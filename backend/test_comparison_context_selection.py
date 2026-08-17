"""
Test Suite: Product Comparison Context Selection in AI Chat + RAG
Verifies all 5 explicit test cases and additional criteria:
Case 1: Active products [A, B, C], User: "compare 1 and 2" -> Compares ONLY A vs B.
Case 2: Active products [A, B, C], User: "compare MSI and ASUS" -> Compares ONLY MSI vs ASUS.
Case 3: Active products [A, B, C], User: "compare all" -> Compares A vs B vs C (all 3).
Case 4: Active products [A, B, C], User: "which is better between first two?" -> Compares ONLY first two products.
Case 5: Active products [A, B, C], User: "compare 2 and 3" -> Compares ONLY Product 2 vs Product 3.
Case 6: Duplicate products in active context -> Deduplicated by unique product ID.
Case 7: Follow-up comparative query ("Which has better GPU?") -> Remembers active comparison set.
Case 8: API POST /api/chat with context_products -> Returns compared_products and ignored_products.
"""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter
from services.comparison_service import ComparisonService
from services.conversation_memory_service import ConversationMemoryService


class TestComparisonContextSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.product_a = {
            "id": 101,
            "name": "ROG Zephyrus G GA502",
            "brand": "ASUS",
            "category": "Laptop",
            "price": 78000.0,
            "processor": "AMD Ryzen 7 3750H",
            "ram_gb": 16.0,
            "storage": "512GB SSD",
            "gpu": "NVIDIA GTX 1660 Ti Max-Q",
            "battery": "76Wh Battery",
            "rating": 4.5,
            "score": 88.0,
        }

        cls.product_b = {
            "id": 102,
            "name": "Titan Pro GT73VR-7RF",
            "brand": "MSI",
            "category": "Laptop",
            "price": 125000.0,
            "processor": "Intel Core i7-7820HK",
            "ram_gb": 32.0,
            "storage": "1TB SSD + 1TB HDD",
            "gpu": "NVIDIA GTX 1080",
            "battery": "75Wh Battery",
            "rating": 4.6,
            "score": 92.0,
        }

        cls.product_c = {
            "id": 103,
            "name": "Inspiron 15 5559",
            "brand": "Dell",
            "category": "Laptop",
            "price": 45000.0,
            "processor": "Intel Core i5-6200U",
            "ram_gb": 8.0,
            "storage": "1TB HDD",
            "gpu": "AMD Radeon R5 M335",
            "battery": "40Wh Battery",
            "rating": 4.0,
            "score": 70.0,
        }

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_case_01_compare_1_and_2(self):
        """Case 1: Active products [A, B, C], User: 'compare 1 and 2' -> ONLY A and B compared."""
        nlp_data = NLPService.parse_query_heuristics("compare 1 and 2")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(nlp_data["selected_indices"], [1, 2])

        active_context = [self.product_a, self.product_b, self.product_c]

        res = QueryRouter.route_query(
            db=self.db,
            user_query="compare 1 and 2",
            nlp_data=nlp_data,
            active_products=active_context,
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(res["compared_products"], [101, 102])
        self.assertEqual(res["ignored_products"], [103])
        self.assertEqual(len(res["products"]), 2)

        # Markdown table must have exactly 2 product columns (not 3)
        self.assertIn("ASUS", res["answer"])
        self.assertIn("MSI", res["answer"])
        self.assertNotIn("Dell", res["answer"])

    def test_case_02_compare_named_products(self):
        """Case 2: Active products [A, B, C], User: 'compare MSI and ASUS' -> ONLY MSI and ASUS compared."""
        nlp_data = NLPService.parse_query_heuristics("compare MSI and ASUS")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_COMPARISON)

        active_context = [self.product_a, self.product_b, self.product_c]

        res = QueryRouter.route_query(
            db=self.db,
            user_query="compare MSI and ASUS",
            nlp_data=nlp_data,
            active_products=active_context,
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(len(res["products"]), 2)
        compared_names = [f"{p['brand']} {p['name']}" for p in res["products"]]
        self.assertTrue(any("MSI" in n for n in compared_names))
        self.assertTrue(any("ASUS" in n for n in compared_names))
        self.assertFalse(any("Dell" in n for n in compared_names))
        self.assertEqual(res["ignored_products"], [103])

    def test_case_03_compare_all(self):
        """Case 3: Active products [A, B, C], User: 'compare all' -> A vs B vs C (all 3 compared)."""
        nlp_data = NLPService.parse_query_heuristics("compare all")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertTrue(nlp_data["is_compare_all"])

        active_context = [self.product_a, self.product_b, self.product_c]

        res = QueryRouter.route_query(
            db=self.db,
            user_query="compare all",
            nlp_data=nlp_data,
            active_products=active_context,
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(res["compared_products"], [101, 102, 103])
        self.assertEqual(res["ignored_products"], [])
        self.assertEqual(len(res["products"]), 3)
        self.assertIn("ASUS", res["answer"])
        self.assertIn("MSI", res["answer"])
        self.assertIn("Dell", res["answer"])

    def test_case_04_better_between_first_two(self):
        """Case 4: User: 'which is better between first two?' -> First two products only (A vs B)."""
        nlp_data = NLPService.parse_query_heuristics("which is better between first two?")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(nlp_data["selected_indices"], [1, 2])

        active_context = [self.product_a, self.product_b, self.product_c]

        res = QueryRouter.route_query(
            db=self.db,
            user_query="which is better between first two?",
            nlp_data=nlp_data,
            active_products=active_context,
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(res["compared_products"], [101, 102])
        self.assertEqual(res["ignored_products"], [103])
        self.assertEqual(len(res["products"]), 2)

    def test_case_05_compare_2_and_3(self):
        """Case 5: Active products [A, B, C], User: 'compare 2 and 3' -> Product 2 vs Product 3 (B vs C)."""
        nlp_data = NLPService.parse_query_heuristics("compare 2 and 3")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(nlp_data["selected_indices"], [2, 3])

        active_context = [self.product_a, self.product_b, self.product_c]

        res = QueryRouter.route_query(
            db=self.db,
            user_query="compare 2 and 3",
            nlp_data=nlp_data,
            active_products=active_context,
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(res["compared_products"], [102, 103])
        self.assertEqual(res["ignored_products"], [101])
        self.assertEqual(len(res["products"]), 2)
        self.assertIn("MSI", res["answer"])
        self.assertIn("Dell", res["answer"])
        self.assertNotIn("ASUS", res["answer"])

    def test_case_06_handle_duplicate_products_in_context(self):
        """Case 6: Duplicate product IDs in context -> Automatically deduplicated by ID."""
        duplicate_context = [
            self.product_a,
            self.product_b,
            self.product_b,  # Duplicate of B
        ]

        nlp_data = NLPService.parse_query_heuristics("compare all")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="compare all",
            nlp_data=nlp_data,
            active_products=duplicate_context,
        )

        # Must have exactly 2 unique products
        self.assertEqual(len(res["products"]), 2)
        self.assertEqual(res["compared_products"], [101, 102])

    def test_case_07_followup_comparative_query_memory(self):
        """Case 7: Turn 1 compares ASUS and MSI -> Turn 2 'Which has better GPU?' remembers comparison set."""
        session_id = "test_comparison_memory_session_1"
        ConversationMemoryService.clear_session(session_id)

        # Turn 1: Compare 1 and 2
        nlp_data_1 = NLPService.parse_query_heuristics("compare 1 and 2")
        active_context = [self.product_a, self.product_b, self.product_c]
        res1 = QueryRouter.route_query(
            db=self.db,
            user_query="compare 1 and 2",
            nlp_data=nlp_data_1,
            active_products=active_context,
            session_id=session_id
        )
        ConversationMemoryService.update_session(
            session_id=session_id,
            comparison_products=res1["products"],
            query="compare 1 and 2",
            answer=res1["answer"],
            intent=IntentType.PRODUCT_COMPARISON
        )

        # Turn 2: Follow-up "Which has better GPU?"
        nlp_data_2 = NLPService.parse_query_heuristics("Which has better GPU?")
        self.assertEqual(nlp_data_2["intent"], IntentType.PRODUCT_COMPARISON)

        res2 = QueryRouter.route_query(
            db=self.db,
            user_query="Which has better GPU?",
            nlp_data=nlp_data_2,
            active_products=[],  # Empty active products in turn 2
            session_id=session_id
        )

        self.assertEqual(res2["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(res2["compared_products"], [101, 102])
        self.assertIn("GPU", res2["answer"])
        self.assertIn("Verdict & Winner for Graphics (GPU)", res2["answer"])

    def test_case_08_api_chat_with_context_products(self):
        """Case 8: API POST /api/chat with context_products returns compared_products and ignored_products."""
        session_id = "test_api_context_products_session"
        payload = {
            "message": "compare 1 and 2",
            "session_id": session_id,
            "context_products": [
                {"index": 1, "id": 101},
                {"index": 2, "id": 102},
                {"index": 3, "id": 103},
            ]
        }

        res = self.client.post("/api/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertEqual(data["compared_products"], [101, 102])
        self.assertEqual(data["ignored_products"], [103])
        self.assertIn("Side-by-Side Technical Comparison Matrix", data["answer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
