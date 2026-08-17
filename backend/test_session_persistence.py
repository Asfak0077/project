"""
Test Suite: Temporary Comparison Context Persistence after Page Reload
Verifies:
1. POST /api/session/save creates temporary session with 24h expiration.
2. GET /api/session/{conversation_id} retrieves session and validates product existence in MySQL DB.
3. Non-existent / deleted product IDs are filtered out on session restore.
4. Expired sessions (>24h) are rejected with 404.
5. Multi-turn reload continuity: Turn 1 saves comparison -> Page Reload -> Turn 2 'Which has better GPU?' remembers comparison context.
6. DELETE /api/session/{conversation_id} removes session.
"""
from __future__ import annotations

import time
import unittest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from services.conversation_memory_service import ConversationMemoryService, SessionState
from services.nlp_service import IntentType


class TestSessionPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.test_cid = "test_conv_reload_12345"

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        ConversationMemoryService.clear_session(self.test_cid)

    def tearDown(self):
        ConversationMemoryService.clear_session(self.test_cid)

    def test_01_save_and_retrieve_session(self):
        """1. Save session with comparison products and messages, then retrieve."""
        save_payload = {
            "conversation_id": self.test_cid,
            "comparison_products": [101, 102],
            "active_product": 101,
            "messages": [
                {"role": "user", "content": "compare 1 and 2"},
                {"role": "assistant", "content": "Here is the comparison between ASUS and MSI."},
            ],
            "last_intent": "comparison",
        }

        res_save = self.client.post("/api/session/save", json=save_payload)
        self.assertEqual(res_save.status_code, 200)
        data_save = res_save.json()
        self.assertEqual(data_save["status"], "saved")
        self.assertEqual(data_save["conversation_id"], self.test_cid)
        self.assertIn("expires_at", data_save)

        # Retrieve session
        res_get = self.client.get(f"/api/session/{self.test_cid}")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertEqual(data_get["conversation_id"], self.test_cid)
        self.assertEqual(len(data_get["comparison_products"]), 2)
        self.assertEqual(len(data_get["messages"]), 2)
        self.assertEqual(data_get["last_intent"], "comparison")

    def test_02_filter_nonexistent_products_on_restore(self):
        """2. Non-existent product ID (e.g. 9999999) must be filtered out on restore."""
        save_payload = {
            "conversation_id": self.test_cid,
            "comparison_products": [101, 9999999],  # 9999999 does not exist in DB
            "messages": [],
            "last_intent": "comparison",
        }

        self.client.post("/api/session/save", json=save_payload)

        # Retrieve session: only ID 101 should survive
        res_get = self.client.get(f"/api/session/{self.test_cid}")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        comp_ids = [p["id"] for p in data_get["comparison_products"]]
        self.assertIn(101, comp_ids)
        self.assertNotIn(9999999, comp_ids)

    def test_03_expired_session_returns_404(self):
        """3. Expired session (>24h) must return 404."""
        save_payload = {
            "conversation_id": self.test_cid,
            "comparison_products": [101, 102],
        }
        self.client.post("/api/session/save", json=save_payload)

        # Artificially expire the session
        session = ConversationMemoryService.get_or_create(self.test_cid)
        session.expires_at = time.time() - 100  # Expired in past

        res_get = self.client.get(f"/api/session/{self.test_cid}")
        self.assertEqual(res_get.status_code, 404)

    def test_04_multi_turn_reload_context_continuity(self):
        """4. Turn 1 comparison -> Reload session -> Turn 2 'Which has better GPU?' remembers active comparison set."""
        # Turn 1: Save comparison context
        save_payload = {
            "conversation_id": self.test_cid,
            "comparison_products": [101, 102],
            "active_product": 101,
            "messages": [
                {"role": "user", "content": "compare 1 and 2"},
                {"role": "assistant", "content": "Comparison table rendered."},
            ],
            "last_intent": "PRODUCT_COMPARISON",
        }
        self.client.post("/api/session/save", json=save_payload)

        # Simulate Page Reload: Client fetches session from API
        res_reload = self.client.get(f"/api/session/{self.test_cid}")
        self.assertEqual(res_reload.status_code, 200)
        reloaded_state = res_reload.json()
        self.assertEqual(len(reloaded_state["comparison_products"]), 2)

        # Turn 2: User asks follow-up "Which has better GPU?"
        chat_payload = {
            "message": "Which has better GPU?",
            "conversation_id": self.test_cid,
            "session_id": self.test_cid,
            "context_products": [],  # Empty context products after refresh
            "history": reloaded_state["messages"],
        }
        res_chat = self.client.post("/api/chat", json=chat_payload)
        self.assertEqual(res_chat.status_code, 200)
        chat_data = res_chat.json()

        self.assertEqual(chat_data["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(chat_data["compared_products"], [101, 102])
        self.assertIn("GPU", chat_data["answer"])
        self.assertIn("Verdict & Winner for Graphics (GPU)", chat_data["answer"])

    def test_05_delete_session(self):
        """5. DELETE /api/session/{conversation_id} removes session."""
        save_payload = {
            "conversation_id": self.test_cid,
            "comparison_products": [101, 102],
        }
        self.client.post("/api/session/save", json=save_payload)

        # Delete
        res_del = self.client.delete(f"/api/session/{self.test_cid}")
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["status"], "deleted")

        # Verify 404
        res_get = self.client.get(f"/api/session/{self.test_cid}")
        self.assertEqual(res_get.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
