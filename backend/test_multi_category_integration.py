"""
VersusAI Multi-Category Dataset Integration Test Suite
Verifies:
1. Multi-Category Inventory (Laptops, Phones, Tablets) in AWS RDS MySQL.
2. Category-Aware NLP Extraction (Category detection, entity extraction, budget bounds).
3. Recommendation Engine Category Isolation & Tailored Scoring.
4. Multi-Category Comparison Matrix & Dynamic Winner Determination.
5. RAG VER2 Multi-Collection Retrieval (laptops, mobiles, tablets).
6. REST API Endpoints (/api/products, /api/dashboard/stats, /api/dashboard/category-distribution, /api/compare, /api/chat).
"""
import os
import sys
import unittest
import json
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(str(BACKEND_DIR))

from database import SessionLocal, init_db
from models.product import Product, ProductSpec, Brand, Category
from services.nlp_service import NLPService, IntentType
from services.recommendation_service import RecommendationService
from services.comparison_service import ComparisonService
from services.query_router import QueryRouter
from services.rag_service import RAGService
from services.product_data_validator import get_normalized_product_facts, format_product_response
from fastapi.testclient import TestClient
from main import app


class TestMultiCategoryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # =========================================================================
    # 1. DATABASE INVENTORY & SCHEMA VERIFICATION
    # =========================================================================
    def test_01_database_has_multiple_categories(self):
        """Verify that Laptops, Phones, and Tablets exist in MySQL."""
        laptop_count = self.db.query(Product).filter(Product.category == "Laptop").count()
        phone_count = self.db.query(Product).filter(Product.category == "Phone").count()
        tablet_count = self.db.query(Product).filter(Product.category == "Tablet").count()

        print(f"\n[Test 01] Database Inventory: Laptops={laptop_count}, Phones={phone_count}, Tablets={tablet_count}")
        self.assertGreater(laptop_count, 0, "Laptop inventory should not be zero")
        self.assertGreater(phone_count, 0, "Phone inventory should not be zero")
        self.assertGreater(tablet_count, 0, "Tablet inventory should not be zero")

    def test_02_phone_specs_and_raw_features(self):
        """Verify that Phone products contain camera, 5G, and battery specs in MySQL."""
        phone = self.db.query(Product).join(ProductSpec).filter(Product.category == "Phone").first()
        self.assertIsNotNone(phone, "Should find at least one phone product")
        self.assertIsNotNone(phone.specs, "Phone should have ProductSpec record")
        self.assertIsNotNone(phone.specs.raw_specs_json, "Phone should have raw_specs_json")
        self.assertIn("rear_camera", phone.specs.raw_specs_json)
        self.assertIn("battery_mah", phone.specs.raw_specs_json)

    def test_03_tablet_specs_and_raw_features(self):
        """Verify that Tablet products contain screen size, battery, and stylus flags in MySQL."""
        tablet = self.db.query(Product).join(ProductSpec).filter(Product.category == "Tablet").first()
        self.assertIsNotNone(tablet, "Should find at least one tablet product")
        self.assertIsNotNone(tablet.specs, "Tablet should have ProductSpec record")
        self.assertIsNotNone(tablet.specs.display_size_inch, "Tablet should have display size")
        self.assertIn("stylus_supported", tablet.specs.raw_specs_json)

    # =========================================================================
    # 2. NLP CATEGORY DETECTION & ENTITY EXTRACTION
    # =========================================================================
    def test_04_nlp_detects_phone_category(self):
        """Verify NLP classifies smartphone queries as 'Phone'."""
        parsed = NLPService.parse_query_heuristics("Best 5G smartphone under 30000 with 50MP camera")
        self.assertEqual(parsed["category"], "Phone")
        self.assertEqual(parsed["intent"], IntentType.PRODUCT_RECOMMENDATION)
        self.assertEqual(parsed["max_price"], 30000.0)

    def test_05_nlp_detects_tablet_category(self):
        """Verify NLP classifies tablet and iPad queries as 'Tablet'."""
        parsed = NLPService.parse_query_heuristics("Recommend an iPad or tablet for drawing and note taking under 40k")
        self.assertEqual(parsed["category"], "Tablet")
        self.assertEqual(parsed["intent"], IntentType.PRODUCT_RECOMMENDATION)
        self.assertEqual(parsed["max_price"], 40000.0)

    def test_06_nlp_detects_laptop_category(self):
        """Verify NLP classifies laptop and MacBook queries as 'Laptop'."""
        parsed = NLPService.parse_query_heuristics("Best gaming laptop with RTX 4060 under 90000")
        self.assertEqual(parsed["category"], "Laptop")
        self.assertEqual(parsed["intent"], IntentType.PRODUCT_RECOMMENDATION)
        self.assertEqual(parsed["max_price"], 90000.0)

    def test_07_nlp_extracts_gadget_models(self):
        """Verify NLP extracts model names for phones, tablets, and laptops."""
        names_phone = NLPService.extract_product_names("Tell me about iPhone 15 and Samsung Galaxy S24")
        self.assertTrue(any("iPhone 15" in n for n in names_phone))
        self.assertTrue(any("Galaxy S24" in n for n in names_phone))

        names_tab = NLPService.extract_product_names("Compare iPad Air and Galaxy Tab S9")
        self.assertTrue(any("iPad Air" in n for n in names_tab))
        self.assertTrue(any("Tab S9" in n for n in names_tab))

    # =========================================================================
    # 3. RECOMMENDATION ENGINE STRICT CATEGORY ISOLATION
    # =========================================================================
    def test_08_phone_recommendation_returns_only_phones(self):
        """CRITICAL: Phone query must NEVER return laptops or tablets."""
        res = RecommendationService.get_recommendations(
            db=self.db,
            query="Best phone under 25000 with 6GB RAM",
            category="Phone",
            top_k=4
        )
        recs = res.get("recommendations", [])
        self.assertGreater(len(recs), 0, "Should return phone recommendations")
        for item in recs:
            p = item["product"]
            self.assertEqual(p.category, "Phone", f"Expected Phone but got {p.category} for '{p.name}'")

    def test_09_tablet_recommendation_returns_only_tablets(self):
        """CRITICAL: Tablet query must NEVER return laptops or phones."""
        res = RecommendationService.get_recommendations(
            db=self.db,
            query="Best tablet under 35000 for media reading",
            category="Tablet",
            top_k=4
        )
        recs = res.get("recommendations", [])
        self.assertGreater(len(recs), 0, "Should return tablet recommendations")
        for item in recs:
            p = item["product"]
            self.assertEqual(p.category, "Tablet", f"Expected Tablet but got {p.category} for '{p.name}'")

    def test_10_laptop_recommendation_returns_only_laptops(self):
        """CRITICAL: Laptop query must NEVER return phones or tablets."""
        res = RecommendationService.get_recommendations(
            db=self.db,
            query="Best laptop under 70000 with 16GB RAM for programming",
            category="Laptop",
            top_k=4
        )
        recs = res.get("recommendations", [])
        self.assertGreater(len(recs), 0, "Should return laptop recommendations")
        for item in recs:
            p = item["product"]
            self.assertEqual(p.category, "Laptop", f"Expected Laptop but got {p.category} for '{p.name}'")

    # =========================================================================
    # 4. MULTI-CATEGORY COMPARISON
    # =========================================================================
    def test_11_compare_smartphones(self):
        """Verify side-by-side comparison matrix between smartphones."""
        phones = self.db.query(Product).filter(Product.category == "Phone").limit(2).all()
        if len(phones) >= 2:
            dicts = [get_normalized_product_facts(p) for p in phones]
            comp = ComparisonService.compare_products(dicts)
            self.assertIn("markdown", comp)
            self.assertIn("Rear Camera", comp["markdown"])
            self.assertIsNotNone(comp["winner"])

    def test_12_compare_tablets(self):
        """Verify side-by-side comparison matrix between tablets."""
        tablets = self.db.query(Product).filter(Product.category == "Tablet").limit(2).all()
        if len(tablets) >= 2:
            dicts = [get_normalized_product_facts(t) for t in tablets]
            comp = ComparisonService.compare_products(dicts)
            self.assertIn("markdown", comp)
            self.assertIn("Stylus", comp["markdown"])
            self.assertIsNotNone(comp["winner"])

    # =========================================================================
    # 5. RAG VER2 MULTI-COLLECTION RETRIEVAL
    # =========================================================================
    def test_13_rag_ver2_queries_mobiles_collection(self):
        """Verify RAG VER2 retrieves from the 'mobiles' ChromaDB collection."""
        res = RAGService.query_rag(query="camera resolution and fast charging", category="mobiles", top_k=3)
        self.assertEqual(res.get("rag_version"), "ver2")
        self.assertIn("answer", res)
        self.assertGreater(len(res.get("results", [])), 0)

    def test_14_rag_ver2_queries_tablets_collection(self):
        """Verify RAG VER2 retrieves from the 'tablets' ChromaDB collection."""
        res = RAGService.query_rag(query="battery capacity and display screen", category="tablets", top_k=3)
        self.assertEqual(res.get("rag_version"), "ver2")
        self.assertIn("answer", res)
        self.assertGreater(len(res.get("results", [])), 0)

    def test_15_rag_ver2_queries_laptops_collection(self):
        """Verify RAG VER2 retrieves from the 'laptops' ChromaDB collection."""
        res = RAGService.query_rag(query="graphics card and processor memory", category="laptops", top_k=3)
        self.assertEqual(res.get("rag_version"), "ver2")
        self.assertIn("answer", res)
        self.assertGreater(len(res.get("results", [])), 0)

    # =========================================================================
    # 6. REST API ENDPOINTS
    # =========================================================================
    def test_16_api_get_products_by_category(self):
        """Test GET /api/products?category=Phone & Tablet & Laptop."""
        for cat in ["Phone", "Tablet", "Laptop"]:
            response = self.client.get(f"/api/products?category={cat}&limit=5")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            for item in data["items"]:
                self.assertEqual(item["category"], cat)

    def test_17_api_dashboard_stats_has_category_counts(self):
        """Test GET /api/dashboard/stats returns phone_count and tablet_count."""
        response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_products", data)
        self.assertIn("laptop_count", data)
        self.assertIn("phone_count", data)
        self.assertIn("tablet_count", data)

    def test_18_api_dashboard_category_distribution(self):
        """Test GET /api/dashboard/category-distribution."""
        response = self.client.get("/api/dashboard/category-distribution")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)
        categories = [item["category"] for item in data]
        self.assertTrue(any("Laptop" in c for c in categories))
        self.assertTrue(any("Phone" in c for c in categories))

    def test_19_api_compare_endpoint(self):
        """Test POST /api/compare with real product codes."""
        prods = self.db.query(Product).limit(2).all()
        if len(prods) >= 2:
            pids = [p.product_code for p in prods]
            response = self.client.post("/api/compare", json={"product_ids": pids})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("spec_rows", data)
            self.assertIn("overall_winner_id", data)

    def test_20_api_chat_multi_category_routing(self):
        """Test POST /api/chat with phone and tablet recommendation requests."""
        resp_phone = self.client.post("/api/chat", json={"message": "Suggest top phones under 30000"})
        self.assertEqual(resp_phone.status_code, 200)
        data_phone = resp_phone.json()
        self.assertEqual(data_phone.get("intent"), IntentType.PRODUCT_RECOMMENDATION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
