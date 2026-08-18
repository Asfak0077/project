"""
Notification Service & Real-Time Connection Manager
Provides multi-user isolated notifications stored in MySQL/AWS RDS,
real-time WebSocket & SSE push broadcasts, and dormant Email service hooks.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
from typing import Dict, Set, List, Optional, Tuple, Any
from fastapi import WebSocket
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.notification import Notification

logger = logging.getLogger("backend.notifications")


class NotificationConnectionManager:
    """
    Thread-safe connection manager for active WebSocket and SSE client connections.
    Indexed strictly by user_id to ensure zero cross-user message leakage.
    """

    def __init__(self):
        self._active_websockets: Dict[int, Set[WebSocket]] = {}
        self._active_sse_queues: Dict[int, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def connect_websocket(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        await self.add_websocket(user_id, websocket)

    async def add_websocket(self, user_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            if user_id not in self._active_websockets:
                self._active_websockets[user_id] = set()
            self._active_websockets[user_id].add(websocket)
        logger.info(f"[NotificationWS] User {user_id} registered socket. Total active sockets for user: {len(self._active_websockets[user_id])}")

    async def disconnect_websocket(self, user_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            if user_id in self._active_websockets and websocket in self._active_websockets[user_id]:
                self._active_websockets[user_id].remove(websocket)
                if not self._active_websockets[user_id]:
                    del self._active_websockets[user_id]
        logger.info(f"[NotificationWS] User {user_id} disconnected.")

    async def register_sse(self, user_id: int, queue: asyncio.Queue) -> None:
        async with self._lock:
            if user_id not in self._active_sse_queues:
                self._active_sse_queues[user_id] = set()
            self._active_sse_queues[user_id].add(queue)
        logger.info(f"[NotificationSSE] User {user_id} registered SSE stream.")

    async def unregister_sse(self, user_id: int, queue: asyncio.Queue) -> None:
        async with self._lock:
            if user_id in self._active_sse_queues and queue in self._active_sse_queues[user_id]:
                self._active_sse_queues[user_id].remove(queue)
                if not self._active_sse_queues[user_id]:
                    del self._active_sse_queues[user_id]
        logger.info(f"[NotificationSSE] User {user_id} unregistered SSE stream.")

    async def broadcast_to_user(self, user_id: int, payload: Dict[str, Any]) -> None:
        """
        Dispatches real-time notification payload to all connected sockets and SSE queues for user_id.
        """
        message_str = json.dumps(payload, default=str)

        # 1. Send to WebSockets
        sockets_to_remove = set()
        user_sockets = list(self._active_websockets.get(user_id, []))
        for ws in user_sockets:
            try:
                await ws.send_text(message_str)
            except Exception as e:
                logger.warning(f"[NotificationWS] Failed to send to socket for user {user_id}: {e}")
                sockets_to_remove.add(ws)

        if sockets_to_remove:
            async with self._lock:
                for bad_ws in sockets_to_remove:
                    if user_id in self._active_websockets and bad_ws in self._active_websockets[user_id]:
                        self._active_websockets[user_id].remove(bad_ws)

        # 2. Send to SSE Queues
        user_queues = list(self._active_sse_queues.get(user_id, []))
        for q in user_queues:
            try:
                await q.put(payload)
            except Exception as e:
                logger.warning(f"[NotificationSSE] Failed to push to SSE queue for user {user_id}: {e}")


# Singleton Connection Manager
connection_manager = NotificationConnectionManager()


class NotificationService:
    """
    Core Notification Management Service.
    Handles MySQL database persistence and asynchronous real-time event dispatch.
    """

    @staticmethod
    def create_notification(
        db: Session,
        user_id: Any,
        title: str,
        message: str,
        type: str = "SYSTEM",
        reference_id: Optional[str] = None,
        status: str = "unread"
    ) -> Optional[Notification]:
        """
        Creates and persists a notification to MySQL, then triggers real-time delivery.
        Non-blocking error handling guarantees the caller function is never broken.
        """
        if not user_id:
            logger.debug("create_notification skipped: user_id is empty or anonymous.")
            return None

        try:
            notif = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=type.upper(),
                status=status,
                reference_id=str(reference_id) if reference_id else None,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(notif)
            db.commit()
            db.refresh(notif)

            # Build serializable payload for real-time broadcast
            payload = {
                "event": "NEW_NOTIFICATION",
                "notification": {
                    "id": notif.id,
                    "user_id": notif.user_id,
                    "title": notif.title,
                    "message": notif.message,
                    "type": notif.type,
                    "status": notif.status,
                    "reference_id": notif.reference_id,
                    "created_at": notif.created_at.isoformat() if notif.created_at else None,
                    "read_at": notif.read_at.isoformat() if notif.read_at else None,
                }
            }

            # Asynchronously dispatch without blocking current synchronous request thread
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(connection_manager.broadcast_to_user(user_id, payload))
            except RuntimeError:
                # If outside async loop (e.g. background task thread), schedule on new event loop or background worker
                asyncio.run(connection_manager.broadcast_to_user(user_id, payload))

            logger.info(f"Notification #{notif.id} created for user {user_id}: [{type}] '{title}'")
            return notif
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create notification for user {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: Any,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Notification], int, int]:
        """
        Retrieves paginated notifications for the specified user.
        Strict multi-user security: query is always constrained by user_id.
        """
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if status_filter:
            query = query.filter(Notification.status == status_filter)

        total = query.count()
        unread_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status == "unread"
        ).count()

        notifications = (
            query.order_by(desc(Notification.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return notifications, total, unread_count

    @staticmethod
    def get_unread_count(db: Session, user_id: Any) -> int:
        """Returns total unread notifications count for a user."""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status == "unread"
        ).count()

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: Any) -> Optional[Notification]:
        """Marks a single notification as read, validating user ownership."""
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if notif:
            notif.status = "read"
            notif.read_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            db.refresh(notif)
            logger.info(f"Notification #{notification_id} marked as read by user {user_id}.")
        return notif

    @staticmethod
    def mark_all_as_read(db: Session, user_id: Any) -> int:
        """Marks all unread notifications for a user as read."""
        now = datetime.datetime.now(datetime.timezone.utc)
        updated = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status == "unread"
        ).update(
            {"status": "read", "read_at": now},
            synchronize_session=False
        )
        db.commit()
        logger.info(f"Marked {updated} notifications as read for user {user_id}.")
        return updated

    @staticmethod
    def delete_notification(db: Session, notification_id: int, user_id: Any) -> bool:
        """Deletes a specific notification with ownership check."""
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if notif:
            db.delete(notif)
            db.commit()
            logger.info(f"Notification #{notification_id} deleted by user {user_id}.")
            return True
        return False

    @staticmethod
    def clear_all_notifications(db: Session, user_id: Any) -> int:
        """Deletes all notifications for a user."""
        deleted = db.query(Notification).filter(
            Notification.user_id == user_id
        ).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Cleared {deleted} notifications for user {user_id}.")
        return deleted


class EmailNotificationService:
    """
    Dormant Email Notification Service structure.
    Prepared for future SMTP / AWS SES / SendGrid integration.
    """

    @staticmethod
    async def send_login_alert(user_email: str, user_name: str, device_info: str = "Web Browser") -> bool:
        logger.info(f"[EmailService - Dormant] Login notification prepared for {user_email} (User: {user_name}, Device: {device_info})")
        return True

    @staticmethod
    async def send_password_reset_confirmation(user_email: str) -> bool:
        logger.info(f"[EmailService - Dormant] Password reset email prepared for {user_email}")
        return True

    @staticmethod
    async def send_ai_completion_summary(user_email: str, query: str, summary: str) -> bool:
        logger.info(f"[EmailService - Dormant] AI Completion digest prepared for {user_email} (Query: {query[:30]}...)")
        return True
