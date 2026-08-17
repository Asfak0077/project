"""
Comprehensive Automated Test Suite: Advanced RAG + LLM Response Quality & Routing
Tests all 7 required benchmark queries:
1. "What is its price?" -> PRODUCT_PRICE from MySQL
2. "What processor does it use?" -> PRODUCT_SPECIFICATION from MySQL
3. "How much RAM?" -> PRODUCT_SPECIFICATION from MySQL
4. "What does the PDF say about battery?" -> DOCUMENT_QUERY via RAG VER2
5. "Best laptop under 80000" -> PRODUCT_RECOMMENDATION via Recommendation Engine
6. "Compare ASUS and MSI" -> PRODUCT_COMPARISON via Comparison Matrix
7. "Is this good for gaming?" -> PERFORMANCE_ANALYSIS via Technical Engine
8. Multi-turn Session Memory ("Tell me about ASUS" -> "What is its price?")
9. Category isolation in RAG (Phone query -> mobile collection)
10. Fact validation and hallucination correction
11. RAG Health check endpoint GET /api/rag/health
12. API Debug trace in POST /api/chat
"""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from models.product import Product
from services.nlp_service import NLPService, IntentType
from services.rag_service import RAGService
from services.query_router import QueryRouter
from services.fact_validation_service import FactValidationService
from services.conversation_memory_service import ConversationMemoryService
from services.response_service import ResponseService


class TestAdvancedRAGQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

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

    def test_01_benchmark_price_query(self):
        """1. Query: 'What is its price?' -> PRODUCT_PRICE from MySQL."""
        nlp_data = NLPService.parse_query_heuristics("What is its price?")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_PRICE)
        self.assertEqual(nlp_data["spec_field"], "price")

        res = QueryRouter.route_query(
            db=self.db,
            user_query="What is its price?",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_PRICE)
        self.assertEqual(res["context_used"], "database")
        self.assertEqual(res["confidence"], "Database Verified")
        self.assertIn("78,000", res["answer"])
        self.assertFalse(res.get("show_recommendations"))

    def test_02_benchmark_processor_query(self):
        """2. Query: 'What processor does it use?' -> PRODUCT_SPECIFICATION from MySQL."""
        nlp_data = NLPService.parse_query_heuristics("What processor does it use?")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_SPECIFICATION)
        self.assertEqual(nlp_data["spec_field"], "processor")

        res = QueryRouter.route_query(
            db=self.db,
            user_query="What processor does it use?",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_SPECIFICATION)
        self.assertEqual(res["context_used"], "database")
        self.assertIn("AMD Ryzen 7 3750H", res["answer"])

    def test_03_benchmark_ram_query(self):
        """3. Query: 'How much RAM?' -> PRODUCT_SPECIFICATION from MySQL."""
        nlp_data = NLPService.parse_query_heuristics("How much RAM?")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_SPECIFICATION)
        self.assertEqual(nlp_data["spec_field"], "ram")

        res = QueryRouter.route_query(
            db=self.db,
            user_query="How much RAM?",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_SPECIFICATION)
        self.assertEqual(res["context_used"], "database")
        self.assertIn("16GB", res["answer"])

    def test_04_benchmark_pdf_battery_query(self):
        """4. Query: 'What does the PDF say about battery?' -> DOCUMENT_QUERY from RAG VER2."""
        nlp_data = NLPService.parse_query_heuristics("What does the PDF say about battery?")
        self.assertEqual(nlp_data["intent"], IntentType.DOCUMENT_QUERY)
        self.assertTrue(nlp_data["is_document_query"])

        res = QueryRouter.route_query(
            db=self.db,
            user_query="What does the PDF say about battery?",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["intent"], IntentType.DOCUMENT_QUERY)
        self.assertEqual(res["context_used"], "documents")
        self.assertTrue(len(res.get("sources", [])) > 0)
        self.assertEqual(res.get("rag_version"), "ver2")

    def test_05_benchmark_recommendation_under_budget(self):
        """5. Query: 'Best laptop under 80000' -> PRODUCT_RECOMMENDATION."""
        nlp_data = NLPService.parse_query_heuristics("Best laptop under 80000")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_RECOMMENDATION)
        self.assertEqual(nlp_data["category"], "Laptop")
        self.assertEqual(nlp_data["max_price"], 80000.0)

        res = QueryRouter.route_query(
            db=self.db,
            user_query="Best laptop under 80000",
            nlp_data=nlp_data,
            active_products=[]
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_RECOMMENDATION)
        self.assertTrue(res.get("show_recommendations"))
        recs = res.get("recommendations", [])
        self.assertTrue(len(recs) > 0)
        for r in recs:
            p = r.get("product", {})
            p_cat = p.category if hasattr(p, "category") else p.get("category")
            p_price = p.price if hasattr(p, "price") else p.get("price")
            self.assertEqual(p_cat, "Laptop")
            if p_price:
                self.assertLessEqual(p_price, 80000.0)

    def test_06_benchmark_compare_query(self):
        """6. Query: 'Compare ASUS and MSI' -> PRODUCT_COMPARISON."""
        nlp_data = NLPService.parse_query_heuristics("Compare ASUS and MSI")
        self.assertEqual(nlp_data["intent"], IntentType.PRODUCT_COMPARISON)

        res = QueryRouter.route_query(
            db=self.db,
            user_query="Compare ASUS and MSI",
            nlp_data=nlp_data,
            active_products=[
                self.sample_product,
                {
                    "id": 102,
                    "name": "GL62M 7REX",
                    "brand": "MSI",
                    "category": "Laptop",
                    "price": 55000.0,
                    "processor": "Intel Core i7-7700HQ",
                    "ram_gb": 8.0,
                    "storage": "1TB HDD",
                    "gpu": "NVIDIA GTX 1050 Ti",
                    "rating": 4.2,
                    "score": 80.0,
                }
            ]
        )

        self.assertEqual(res["intent"], IntentType.PRODUCT_COMPARISON)
        self.assertTrue(res.get("show_comparison"))
        self.assertIn("Technical Specification", res["answer"])
        self.assertIn("Verdict & Winner", res["answer"])

    def test_07_benchmark_gaming_performance(self):
        """7. Query: 'Is this good for gaming?' -> PERFORMANCE_ANALYSIS."""
        nlp_data = NLPService.parse_query_heuristics("Is this good for gaming?")
        self.assertEqual(nlp_data["intent"], IntentType.PERFORMANCE_ANALYSIS)

        res = QueryRouter.route_query(
            db=self.db,
            user_query="Is this good for gaming?",
            nlp_data=nlp_data,
            active_products=[self.sample_product]
        )

        self.assertEqual(res["intent"], IntentType.PERFORMANCE_ANALYSIS)
        self.assertIn("Gaming Performance", res["answer"])
        self.assertIn("GTX 1660 Ti", res["answer"])

    def test_08_active_context_multi_turn_resolution(self):
        """8. Multi-turn session memory: Turn 1 sets active product -> Turn 2 'What is its price?' resolves it."""
        session_id = "test_memory_session_99"
        ConversationMemoryService.clear_session(session_id)

        # Turn 1: User asks about ASUS ROG Zephyrus
        req1 = {
            "message": "Tell me about ASUS ROG Zephyrus",
            "session_id": session_id,
        }
        res1 = self.client.post("/api/chat", json=req1)
        self.assertEqual(res1.status_code, 200)

        # Turn 2: User asks "What is its price?"
        req2 = {
            "message": "What is its price?",
            "session_id": session_id,
        }
        res2 = self.client.post("/api/chat", json=req2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()

        self.assertEqual(data2["intent"], IntentType.PRODUCT_PRICE)
        self.assertEqual(data2["database_used"], True)
        self.assertIn("Price", data2["answer"])
        self.assertIn("₹", data2["answer"])

    def test_09_rag_category_isolation(self):
        """9. Phone queries must route to mobile collection in RAG VER2."""
        res_phone = RAGService.query_rag(
            query="Battery life of smartphone",
            category="phone",
            top_k=3
        )
        self.assertEqual(res_phone["rag_version"], "ver2")
        for r in res_phone.get("results", []):
            self.assertIn("mobile", r.get("filename", "").lower())

    def test_10_fact_validation_hallucination_correction(self):
        """10. Fact validation detects and corrects hallucinated RAM or price."""
        ground_truth = {
            "name": "ROG Zephyrus G GA502",
            "ram_gb": 16.0,
            "price": 78000.0,
        }

        hallucinated_text = "The ROG Zephyrus G GA502 features 32GB RAM and costs ₹1,20,000 in India."
        is_valid, corrected_text, report = FactValidationService.validate_llm_response(
            hallucinated_text,
            ground_truth
        )

        self.assertFalse(is_valid)
        self.assertIn("16GB RAM", corrected_text)
        self.assertIn("₹78,000", corrected_text)

    def test_11_rag_health_endpoint(self):
        """11. GET /api/rag/health returns status healthy and ver2."""
        res = self.client.get("/api/rag/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["rag_version"], "ver2")
        self.assertEqual(data["vector_store"], "ready")
        self.assertEqual(data["retriever"], "ready")

    def test_12_api_chat_debug_trace(self):
        """12. POST /api/chat returns debug_trace and structured metadata."""
        req = {
            "message": "What processor does it use?",
            "session_id": "test_debug_session_trace"
        }
        res = self.client.post("/api/chat", json=req)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("debug_trace", data)
        self.assertIsNotNone(data["debug_trace"])
        self.assertEqual(data["database_used"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
