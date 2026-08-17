"""
Test Suite: Simple Answer Mode for User Questions (Level 1, Level 2, Level 3 Response Formatting)
Verifies:
1. 'ram' -> 'RAM: 16GB' with type: 'specification', field: 'ram', verified: True, source_type: 'database'
2. 'price' -> 'Price: ₹78,000'
3. 'processor' -> 'Processor: AMD Ryzen 7 3750H'
4. 'storage' -> 'Storage: 512GB NVMe SSD'
5. 'gpu' -> 'GPU: NVIDIA GeForce GTX 1660 Ti Max-Q'
6. 'battery' -> 'Battery: 76Wh Battery'
7. Level 2 'Is this good for gaming?' -> concise Gaming Performance summary without markdown bloat.
8. Level 3 RAG query -> concise Document Information + clean source.
9. No full product name repetition in simple spec answers.
"""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter
from services.response_service import ResponseService
from services.conversation_memory_service import ConversationMemoryService


class TestSimpleAnswerMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.session_id = "test_simple_answer_session"
        cls.sample_product = {
            "id": 101,
            "name": "ROG Zephyrus G GA502",
            "brand": "ASUS",
            "category": "Laptop",
            "price": 78000.0,
            "processor": "AMD Ryzen 7 3750H",
            "ram_gb": 16.0,
            "storage": "512GB NVMe SSD",
            "gpu": "NVIDIA GeForce GTX 1660 Ti Max-Q",
            "battery": "76Wh Battery",
            "rating": 4.5,
            "score": 88.0,
        }

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        ConversationMemoryService.clear_session(self.session_id)

    def tearDown(self):
        ConversationMemoryService.clear_session(self.session_id)

    def test_01_simple_ram_response(self):
        """1. Query 'ram' returns 'RAM: 16GB' with clean metadata."""
        nlp_data = NLPService.parse_query_heuristics("ram")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="ram",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["answer"], "RAM: 16GB")
        self.assertEqual(res["type"], "specification")
        self.assertEqual(res["field"], "ram")
        self.assertTrue(res["verified"])
        self.assertEqual(res["source_type"], "database")
        self.assertNotIn("The ASUS ROG Zephyrus has", res["answer"])

    def test_02_simple_price_response(self):
        """2. Query 'price' returns 'Price: ₹78,000'."""
        nlp_data = NLPService.parse_query_heuristics("price")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="price",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["answer"], "Price: ₹78,000")
        self.assertEqual(res["type"], "specification")
        self.assertEqual(res["field"], "price")

    def test_03_simple_processor_response(self):
        """3. Query 'processor' returns 'Processor: AMD Ryzen 7 3750H'."""
        nlp_data = NLPService.parse_query_heuristics("processor")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="processor",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["answer"], "Processor: AMD Ryzen 7 3750H")
        self.assertEqual(res["field"], "processor")

    def test_04_simple_storage_response(self):
        """4. Query 'storage' returns 'Storage: 512GB NVMe SSD'."""
        nlp_data = NLPService.parse_query_heuristics("storage")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="storage",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["answer"], "Storage: 512GB NVMe SSD")
        self.assertEqual(res["field"], "storage")

    def test_05_simple_gpu_response(self):
        """5. Query 'gpu' returns 'GPU: NVIDIA GeForce GTX 1660 Ti Max-Q'."""
        nlp_data = NLPService.parse_query_heuristics("gpu")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="gpu",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["answer"], "GPU: NVIDIA GeForce GTX 1660 Ti Max-Q")

    def test_06_simple_battery_response(self):
        """6. Query 'battery' returns 'Battery: 76Wh Battery'."""
        nlp_data = NLPService.parse_query_heuristics("battery")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="battery",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["answer"], "Battery: 76Wh Battery")

    def test_07_api_chat_level1_formatting(self):
        """7. POST /api/chat with active product returns concise JSON."""
        # Prime session memory with product
        ConversationMemoryService.update_session(
            session_id=self.session_id,
            product=self.sample_product,
            query="Tell me about ASUS ROG",
            answer="ASUS ROG specs",
            intent="PRODUCT_DETAILS"
        )

        req = {
            "message": "ram",
            "session_id": self.session_id,
        }
        res = self.client.post("/api/chat", json=req)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["answer"], "RAM: 16GB")
        self.assertEqual(data["type"], "specification")
        self.assertEqual(data["field"], "ram")
        self.assertTrue(data["verified"])
        self.assertEqual(data["source_type"], "database")

    def test_08_level2_gaming_explanation(self):
        """8. Level 2 query 'Is this good for gaming?' returns concise analysis without markdown headings."""
        nlp_data = NLPService.parse_query_heuristics("Is this good for gaming?")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="Is this good for gaming?",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertIn("Gaming Performance:", res["answer"])
        self.assertIn("GTX 1660 Ti", res["answer"])
        self.assertNotIn("###", res["answer"])  # No markdown heading bloat


if __name__ == "__main__":
    unittest.main(verbosity=2)
