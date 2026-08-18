"""
Notifications Router
REST Endpoints, WebSocket, and SSE Streams for Real-Time User Notifications.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from services.notification_service import NotificationService, connection_manager
from services.auth_service import decode_access_token
from utils.security import get_current_user

logger = logging.getLogger("backend.notifications")

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
def get_notifications(
    status: Optional[str] = Query(None, description="Filter by status: 'unread' or 'read'"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch all notifications for the currently logged-in user with pagination and optional status filter.
    Strictly isolated to current_user.id.
    """
    notifs, total, unread_count = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        success=True,
        notifications=[NotificationResponse.model_validate(n) for n in notifs],
        total=total,
        unread_count=unread_count,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the unread notifications count for the badge icon."""
    count = NotificationService.get_unread_count(db=db, user_id=current_user.id)
    return UnreadCountResponse(success=True, count=count)


@router.post("/notifications/read/{notification_id}")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied.",
        )
    return {
        "success": True,
        "message": "Notification marked as read.",
        "notification": NotificationResponse.model_validate(notif),
    }


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications for the user as read."""
    updated_count = NotificationService.mark_all_as_read(db=db, user_id=current_user.id)
    return {
        "success": True,
        "message": f"Marked {updated_count} notifications as read.",
        "updated_count": updated_count,
    }


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a single notification."""
    success = NotificationService.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied.",
        )
    return {"success": True, "message": "Notification deleted successfully."}


@router.delete("/notifications")
def clear_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear all notifications for the logged-in user."""
    deleted_count = NotificationService.clear_all_notifications(db=db, user_id=current_user.id)
    return {
        "success": True,
        "message": f"Cleared {deleted_count} notifications.",
        "deleted_count": deleted_count,
    }


# ===========================================================================
# REAL-TIME WEBSOCKET ENDPOINT
# ===========================================================================

@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Real-Time WebSocket channel for instant notification delivery without page refresh.
    Authenticates user via JWT token query parameter.
    """
    await websocket.accept()
    if not token:
        logger.warning("[NotificationWS] Connection rejected: token query parameter missing.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)
    if not payload:
        logger.warning("[NotificationWS] Connection rejected: invalid JWT token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_raw = payload.get("user_id") or payload.get("sub")
    if not user_id_raw:
        logger.warning("[NotificationWS] Connection rejected: missing user_id in JWT payload.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = int(user_id_raw)
    await connection_manager.add_websocket(user_id, websocket)

    # Send welcome handshake event
    try:
        await websocket.send_text(
            json.dumps({
                "event": "CONNECTED",
                "message": "Real-time notification stream active.",
                "user_id": user_id,
            })
        )
    except Exception:
        pass

    try:
        while True:
            # Keep socket alive and respond to client heartbeats / ping
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_text(json.dumps({"event": "PONG"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        await connection_manager.disconnect_websocket(user_id, websocket)
    except Exception as e:
        logger.warning(f"[NotificationWS] Socket error for user {user_id}: {e}")
        await connection_manager.disconnect_websocket(user_id, websocket)


# ===========================================================================
# SERVER-SENT EVENTS (SSE) FALLBACK ENDPOINT
# ===========================================================================

@router.get("/notifications/stream")
async def sse_notifications(
    token: Optional[str] = Query(None),
):
    """
    Server-Sent Events (SSE) fallback stream for instant notification updates
    in environments where WebSockets are restricted.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token.")

    user_id_raw = payload.get("user_id") or payload.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=401, detail="Missing user_id in token.")

    user_id = int(user_id_raw)
    queue: asyncio.Queue = asyncio.Queue()
    await connection_manager.register_sse(user_id, queue)

    async def event_generator():
        # Handshake
        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'user_id': user_id})}\n\n"
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"event: notification\ndata: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield ": heartbeat\n\n"
        finally:
            await connection_manager.unregister_sse(user_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
