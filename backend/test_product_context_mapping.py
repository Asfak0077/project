"""
Test Suite: Product Context Mapping & Strict Reference Resolution
"""
import unittest
from unittest.mock import MagicMock
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter
from services.conversation_memory_service import ConversationMemoryService


def create_sample_context():
    return [
        {
            "id": 101,
            "context_index": 1,
            "brand": "MSI",
            "name": "Titan Pro GT73VR-7RF",
            "price": 105790,
            "processor": "Intel Core i7-7820HK",
            "cpu": "Intel Core i7-7820HK",
            "ram": "32GB",
            "ram_gb": 32,
            "storage": "512GB NVMe SSD + 1TB HDD",
            "gpu": "NVIDIA GeForce GTX 1080",
            "category": "Laptop",
            "score": 92,
        },
        {
            "id": 102,
            "context_index": 2,
            "brand": "MSI",
            "name": "Titan Pro GT73VR-7RF",
            "price": 105790,
            "processor": "Intel Core i7-7820HK",
            "cpu": "Intel Core i7-7820HK",
            "ram": "32GB",
            "ram_gb": 32,
            "storage": "512GB NVMe SSD + 1TB HDD",
            "gpu": "NVIDIA GeForce GTX 1080",
            "category": "Laptop",
            "score": 92,
        },
        {
            "id": 103,
            "context_index": 3,
            "brand": "ASUS",
            "name": "ROG Zephyrus G GA502",
            "price": 79990,
            "processor": "AMD Ryzen 7 3750H",
            "cpu": "AMD Ryzen 7 3750H",
            "ram": "16GB",
            "ram_gb": 16,
            "storage": "512GB NVMe SSD",
            "gpu": "NVIDIA GeForce GTX 1660 Ti Max-Q",
            "category": "Laptop",
            "score": 88,
        },
    ]


class TestProductContextMapping(unittest.TestCase):
    def test_nlp_target_index_extraction(self):
        """Test NLP extraction of single and multiple product indices."""
        # 1. Price of product 3
        q1 = "What is its price of product 3?"
        nlp1 = NLPService.parse_query_heuristics(q1)
        self.assertEqual(nlp1["target_product_index"], 3)
        self.assertEqual(nlp1["spec_field"], "price")

        # 2. RAM of product 1
        q2 = "RAM of product 1"
        nlp2 = NLPService.parse_query_heuristics(q2)
        self.assertEqual(nlp2["target_product_index"], 1)
        self.assertEqual(nlp2["spec_field"], "ram")

        # 3. Compare product 1 and 3
        q3 = "compare product 1 and 3"
        nlp3 = NLPService.parse_query_heuristics(q3)
        self.assertEqual(nlp3["selected_indices"], [1, 3])
        self.assertTrue(nlp3["is_comparison"])

        # 4. Explain product 2
        q4 = "explain product 2"
        nlp4 = NLPService.parse_query_heuristics(q4)
        self.assertEqual(nlp4["target_product_index"], 2)
        self.assertEqual(nlp4["selected_indices"], [2])

    def test_query_router_price_of_product_3(self):
        """Verify 'What is its price of product 3?' returns ASUS price (₹79,990), NOT MSI (₹105,790)."""
        db_mock = MagicMock()
        context = create_sample_context()
        query = "What is its price of product 3?"
        nlp_data = NLPService.parse_query_heuristics(query)

        res = QueryRouter.route_query(
            db=db_mock,
            user_query=query,
            nlp_data=nlp_data,
            active_products=context,
            session_id="test-session-1"
        )

        self.assertEqual(res["type"], "specification")
        self.assertEqual(res["field"], "price")
        self.assertIn("79,990", res["answer"])
        self.assertNotIn("105,790", res["answer"])
        self.assertEqual(res["product"]["id"], 103)
        self.assertIn("ASUS", res["product"]["brand"])

    def test_query_router_ram_of_product_1(self):
        """Verify 'RAM of product 1' returns Product 1 RAM (32GB)."""
        db_mock = MagicMock()
        context = create_sample_context()
        query = "RAM of product 1"
        nlp_data = NLPService.parse_query_heuristics(query)

        res = QueryRouter.route_query(
            db=db_mock,
            user_query=query,
            nlp_data=nlp_data,
            active_products=context,
            session_id="test-session-2"
        )

        self.assertEqual(res["type"], "specification")
        self.assertEqual(res["field"], "ram")
        self.assertIn("32GB", res["answer"])
        self.assertEqual(res["product"]["id"], 101)

    def test_query_router_compare_product_1_and_3(self):
        """Verify 'compare product 1 and 3' compares ONLY Product 1 and Product 3, completely ignoring Product 2."""
        db_mock = MagicMock()
        context = create_sample_context()
        query = "compare product 1 and 3"
        nlp_data = NLPService.parse_query_heuristics(query)

        res = QueryRouter.route_query(
            db=db_mock,
            user_query=query,
            nlp_data=nlp_data,
            active_products=context,
            session_id="test-session-3"
        )

        self.assertEqual(res["type"], "comparison")
        compared_ids = [p["id"] for p in res["compared_products"]]
        self.assertEqual(compared_ids, [101, 103])
        self.assertIn(102, res["ignored_products"])
        self.assertNotIn(102, compared_ids)

    def test_query_router_explain_product_2(self):
        """Verify 'explain product 2' targets only Product 2."""
        db_mock = MagicMock()
        context = create_sample_context()
        query = "explain product 2"
        nlp_data = NLPService.parse_query_heuristics(query)

        res = QueryRouter.route_query(
            db=db_mock,
            user_query=query,
            nlp_data=nlp_data,
            active_products=context,
            session_id="test-session-4"
        )

        self.assertEqual(res["product"]["id"], 102)
        self.assertEqual(len(res["products"]), 1)

    def test_query_router_out_of_bounds(self):
        """Verify 'product 5' when 3 products exist returns clear friendly context bounds error."""
        db_mock = MagicMock()
        context = create_sample_context()
        query = "What is the price of product 5?"
        nlp_data = NLPService.parse_query_heuristics(query)

        res = QueryRouter.route_query(
            db=db_mock,
            user_query=query,
            nlp_data=nlp_data,
            active_products=context,
            session_id="test-session-5"
        )

        self.assertEqual(res["type"], "error")
        self.assertIn("I have only 3 products in the current context. Please select product 1, 2, or 3.", res["answer"])

    def test_query_router_followup_memory(self):
        """Verify follow-up 'what about RAM?' after querying Product 3 retains Product 3."""
        db_mock = MagicMock()
        session_id = "test-session-followup"
        context = create_sample_context()

        # Turn 1: "What is its price of product 3?"
        q1 = "What is its price of product 3?"
        nlp1 = NLPService.parse_query_heuristics(q1)
        res1 = QueryRouter.route_query(
            db=db_mock,
            user_query=q1,
            nlp_data=nlp1,
            active_products=context,
            session_id=session_id
        )
        self.assertEqual(res1["product"]["id"], 103)

        # Turn 2: "what about RAM?"
        q2 = "what about RAM?"
        nlp2 = NLPService.parse_query_heuristics(q2)
        res2 = QueryRouter.route_query(
            db=db_mock,
            user_query=q2,
            nlp_data=nlp2,
            active_products=context,
            session_id=session_id
        )
        self.assertEqual(res2["type"], "specification")
        self.assertEqual(res2["field"], "ram")
        self.assertIn("16GB", res2["answer"])
        self.assertEqual(res2["product"]["id"], 103)


if __name__ == "__main__":
    unittest.main()
