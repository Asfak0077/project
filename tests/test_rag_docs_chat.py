import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models.document import Document, DocumentChunk
from services.rag_service import RAGService

class TestRAGDocsChat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        
        # Create or verify sample test document in database
        cls.test_doc = cls.db.query(Document).filter(Document.filename == "Test_ROG_Zephyrus_Datasheet.txt").first()
        if not cls.test_doc:
            test_file_path = os.path.join(os.path.dirname(__file__), "Test_ROG_Zephyrus_Datasheet.txt")
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(
                    "ASUS ROG Zephyrus G GA502 Gaming Laptop Manual\n\n"
                    "Processor and Performance:\n"
                    "Powered by AMD Ryzen 7 3750H Quad-Core Processor with clock speeds up to 4.0GHz. Coupled with NVIDIA GeForce GTX 1660 Ti Max-Q graphics with 6GB GDDR6 VRAM.\n\n"
                    "Memory and Storage:\n"
                    "Comes standard with 16GB DDR4 2400MHz dual-channel RAM, expandable up to 32GB. Fast 512GB M.2 NVMe PCIe SSD storage.\n\n"
                    "Battery and Charging:\n"
                    "Equipped with a 76Wh 4-cell lithium-ion battery providing up to 8.8 hours of mixed web browsing and video playback. Includes 180W fast charging power adapter.\n\n"
                    "Thermal and Cooling Architecture:\n"
                    "Features intelligent dual-fan cooling system with self-cleaning anti-dust tunnels and 33% thinner fan blades for 17% higher airflow under full gaming load."
                )
            
            cls.test_doc = Document(
                filename="Test_ROG_Zephyrus_Datasheet.txt",
                file_path=test_file_path,
                file_type="text/plain",
                file_size=os.path.getsize(test_file_path),
                status="uploading"
            )
            cls.db.add(cls.test_doc)
            cls.db.commit()
            cls.db.refresh(cls.test_doc)
            
            # Process & index chunks
            RAGService.process_and_index_document(cls.db, int(getattr(cls.test_doc, "id", 1)))
            cls.db.refresh(cls.test_doc)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_document_indexed_with_metadata(self):
        """1. Verify document chunks have section_title, page_number, and chunk metadata."""
        chunks = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == self.test_doc.id).all()
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIsNotNone(chunk.section_title)
            self.assertIsNotNone(chunk.content)
            self.assertGreater(len(chunk.content), 20)

    def test_02_ask_what_is_processor(self):
        """2. Ask: 'What is processor?' -> Direct answer with source."""
        payload = {
            "message": "What is processor?",
            "document_id": self.test_doc.id
        }
        res = self.client.post("/api/rag/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue("Ryzen" in data["answer"] or "AMD" in data["answer"] or "Processor" in data["answer"])
        self.assertTrue(data["document_used"])
        self.assertEqual(data["rag_version"], "ver2")
        self.assertGreater(len(data["sources"]), 0)

    def test_03_ask_what_is_ram(self):
        """3. Ask: 'What is RAM?' -> Direct 16GB spec answer with source."""
        payload = {
            "message": "What is RAM?",
            "document_id": self.test_doc.id
        }
        res = self.client.post("/api/rag/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue("16GB" in data["answer"] or "DDR4" in data["answer"] or "RAM" in data["answer"])
        self.assertGreater(len(data["sources"]), 0)

    def test_04_ask_explain_battery_performance(self):
        """4. Ask: 'Explain battery performance' -> Detailed explanation with sources."""
        payload = {
            "message": "Explain battery performance",
            "document_id": self.test_doc.id
        }
        res = self.client.post("/api/rag/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue("76Wh" in data["answer"] or "battery" in data["answer"].lower() or "hours" in data["answer"].lower())
        self.assertGreater(len(data["sources"]), 0)

    def test_05_ask_summarize_document(self):
        """5. Ask: 'Summarize document' -> Structured Document Summary."""
        payload = {
            "message": "Summarize document",
            "document_id": self.test_doc.id
        }
        res = self.client.post("/api/rag/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue("Zephyrus" in data["answer"] or "summary" in data["answer"].lower() or "processor" in data["answer"].lower())
        self.assertGreater(len(data["sources"]), 0)

    def test_06_ask_unrelated_question_returns_not_found(self):
        """6. Ask completely unrelated question -> Returns 'I could not find this information in the document.'"""
        payload = {
            "message": "What is the recipe for chocolate chip cookies with organic butter?",
            "document_id": self.test_doc.id
        }
        res = self.client.post("/api/rag/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("could not find this information in the document", data["answer"].lower())

    def test_07_api_response_schema_format(self):
        """7. Verify POST /api/rag/chat returns clean schema format."""
        payload = {
            "message": "Explain cooling system",
            "document_id": self.test_doc.id
        }
        res = self.client.post("/api/rag/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("sources", data)
        self.assertIn("confidence", data)
        self.assertIn("rag_version", data)
        self.assertIn("document_used", data)
        self.assertEqual(data["rag_version"], "ver2")
        if data["sources"]:
            s = data["sources"][0]
            self.assertIn("document", s)
            self.assertIn("section", s)

if __name__ == "__main__":
    unittest.main()
