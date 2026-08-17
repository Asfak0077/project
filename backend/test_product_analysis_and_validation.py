import unittest
import os
import sys

# Ensure backend directory in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models.product import Product
from services.product_service import ProductService
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter
from services.response_service import ResponseService

class TestProductAnalysisAndValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.laptop = cls.db.query(Product).filter(Product.category == "Laptop").first()
        cls.phone = cls.db.query(Product).filter(Product.category == "Phone").first()
        cls.tablet = cls.db.query(Product).filter(Product.category == "Tablet").first()
        
        cls.sample_products = [
            ProductService.get_by_id(cls.db, cls.laptop.id) if cls.laptop else {"id": 1, "name": "ASUS ROG Zephyrus", "brand": "ASUS", "category": "Laptop", "price": 78000, "ram_gb": 16, "processor": "AMD Ryzen 7", "storage": "512GB SSD", "battery": "76Wh"},
            ProductService.get_by_id(cls.db, cls.phone.id) if cls.phone else {"id": 2, "name": "Apple iPhone 15", "brand": "Apple", "category": "Phone", "price": 79900, "ram_gb": 6, "processor": "A16 Bionic", "storage": "128GB", "battery": "3349mAh"},
            ProductService.get_by_id(cls.db, cls.tablet.id) if cls.tablet else {"id": 3, "name": "Apple iPad Pro 2018", "brand": "Apple", "category": "Tablet", "price": 103900, "ram_gb": 6, "processor": "A12X Bionic", "storage": "1000GB", "battery": "9720mAh"},
        ]

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_simple_ram_query(self):
        """1. Ask: RAM -> Returns direct RAM answer."""
        nlp_data = NLPService.parse_query_heuristics("RAM")
        self.assertEqual(nlp_data["spec_field"], "ram")
        res = QueryRouter.route_query(
            db=self.db,
            user_query="RAM",
            nlp_data=nlp_data,
            active_products=[self.sample_products[0]]
        )
        self.assertIn("RAM:", res["answer"])
        self.assertEqual(res["type"], "specification")

    def test_02_explain_product_1(self):
        """2. Ask: Explain product 1 -> Returns Product Analysis with Performance, Memory, Storage, Battery."""
        nlp_data = NLPService.parse_query_heuristics("Explain product 1")
        self.assertEqual(nlp_data["selected_indices"], [1])
        res = QueryRouter.route_query(
            db=self.db,
            user_query="Explain product 1",
            nlp_data=nlp_data,
            active_products=self.sample_products
        )
        self.assertEqual(res["type"], "analysis")
        self.assertIn("## Product Analysis", res["answer"])
        self.assertIn("Performance:", res["answer"])
        self.assertIn("Memory:", res["answer"])
        self.assertIn("Storage:", res["answer"])
        self.assertIn("Battery:", res["answer"])
        self.assertEqual(len(res["products"]), 1)
        self.assertEqual(res["products"][0]["name"], self.sample_products[0]["name"])

    def test_03_explain_product_1_and_2(self):
        """3. Ask: Explain product 1 and 2 -> Returns multi-product analysis of strictly products 1 and 2."""
        nlp_data = NLPService.parse_query_heuristics("Explain product 1 and 2")
        self.assertEqual(nlp_data["selected_indices"], [1, 2])
        res = QueryRouter.route_query(
            db=self.db,
            user_query="Explain product 1 and 2",
            nlp_data=nlp_data,
            active_products=self.sample_products
        )
        self.assertEqual(res["type"], "analysis")
        self.assertIn("## Product Analysis", res["answer"])
        self.assertIn("Product 1:", res["answer"])
        self.assertIn("Product 2:", res["answer"])
        self.assertEqual(len(res["products"]), 2)

    def test_04_2_product_explain_variation(self):
        """4. Ask: 2 product explain -> Correctly maps index 2 and returns product analysis."""
        nlp_data = NLPService.parse_query_heuristics("2 product explain")
        self.assertEqual(nlp_data["selected_indices"], [2])
        res = QueryRouter.route_query(
            db=self.db,
            user_query="2 product explain",
            nlp_data=nlp_data,
            active_products=self.sample_products
        )
        self.assertEqual(res["type"], "analysis")
        self.assertIn("## Product Analysis", res["answer"])
        self.assertEqual(len(res["products"]), 1)
        self.assertEqual(res["products"][0]["name"], self.sample_products[1]["name"])

    def test_05_api_chat_explain_endpoint(self):
        """5. POST /api/chat with 'Explain product 1' returns clean JSON without backend error messages."""
        payload = {
            "message": "Explain product 1",
            "context_products": [
                {"index": 1, "id": str(self.sample_products[0]["id"]), "name": self.sample_products[0]["name"]},
                {"index": 2, "id": str(self.sample_products[1]["id"]), "name": self.sample_products[1]["name"]},
            ]
        }
        res = self.client.post("/api/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("## Product Analysis", data["answer"])
        self.assertNotIn("Validation error", data["answer"])
        self.assertNotIn("Unprocessable", data["answer"])
        self.assertEqual(data["type"], "analysis")

    def test_06_validation_error_returns_friendly_message(self):
        """6. Malformed / invalid input to /api/chat returns friendly AI message, never raw Pydantic errors."""
        # Send empty/bad payload format to test error safety
        res = self.client.post("/api/chat", json={"invalid_field": 123})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("couldn't complete the product analysis", data["answer"])
        self.assertNotIn("field required", data["answer"])
        self.assertNotIn("pydantic", data["answer"])

    def test_07_image_url_presence_in_products(self):
        """7. Product facts return image_url or image without breaking."""
        for p in self.sample_products:
            self.assertTrue("image_url" in p or "image" in p)
            self.assertTrue(len(p.get("name", "")) > 0)

if __name__ == "__main__":
    unittest.main()
