import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database import SessionLocal
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter
from services.conversation_memory_service import ConversationMemoryService


def test_intent_detection():
    # 1. Spec Queries
    r1 = NLPService.parse_query_heuristics("what is RAM?")
    assert r1["spec_field"] == "ram"
    assert not r1.get("is_battle")
    assert not r1.get("is_explain")

    r2 = NLPService.parse_query_heuristics("storage?")
    assert r2["spec_field"] == "storage"
    assert not r2.get("is_battle")

    # 2. Product Explanation Queries
    r3 = NLPService.parse_query_heuristics("Explain product 1")
    assert r3["is_explain"] is True
    assert r3["target_product_index"] == 1

    r4 = NLPService.parse_query_heuristics("Tell me about ASUS ROG Zephyrus")
    assert r4["is_explain"] is True or r4["intent"] == IntentType.PRODUCT_EXPLAIN

    # 3. Battle Reasoning Queries (The exact bug reported: "Why did ASUS ROG Zephyrus win the battle?")
    r5 = NLPService.parse_query_heuristics("Why did ASUS ROG Zephyrus win the battle?")
    assert r5["is_battle"] is True
    assert r5["intent"] in [IntentType.BATTLE_EXPLANATION, IntentType.BATTLE_REASON]

    r6 = NLPService.parse_query_heuristics("Why did ASUS win?")
    assert r6["is_battle"] is True
    assert r6["intent"] in [IntentType.BATTLE_EXPLANATION, IntentType.BATTLE_REASON]

    # 4. Comparison Queries
    r7 = NLPService.parse_query_heuristics("Compare ASUS and MSI")
    assert r7["is_compare"] is True
    assert r7["intent"] == IntentType.PRODUCT_COMPARISON


def test_spec_query_routing():
    db = SessionLocal()
    try:
        active_products = [
            {
                "id": 1,
                "name": "ASUS ROG Zephyrus G14",
                "brand": "ASUS",
                "category": "Laptop",
                "price": 84990,
                "ram": "32GB",
                "ram_gb": 32,
                "storage": "512GB SSD",
                "processor": "AMD Ryzen 7 5800HS",
                "gpu": "NVIDIA GeForce GTX 1660 Ti",
                "score": 88,
                "context_index": 1,
            }
        ]

        nlp_data = NLPService.parse_query_heuristics("what is RAM?")
        res = QueryRouter.route_query(
            db=db,
            user_query="what is RAM?",
            nlp_data=nlp_data,
            active_products=active_products,
            session_id="test_session_spec"
        )

        assert res["type"] == "specification"
        assert "RAM:" in res["answer"]
        assert "32GB" in res["answer"]
        assert "Verified Product Database" in res["answer"]
        print("✓ Spec query test passed:\n", res["answer"])
    finally:
        db.close()


def test_product_explanation_routing():
    db = SessionLocal()
    try:
        active_products = [
            {
                "id": 1,
                "name": "ASUS ROG Zephyrus G14",
                "brand": "ASUS",
                "category": "Laptop",
                "price": 84990,
                "ram": "32GB",
                "ram_gb": 32,
                "storage": "512GB SSD",
                "processor": "AMD Ryzen 7 5800HS",
                "gpu": "NVIDIA GeForce GTX 1660 Ti",
                "score": 88,
                "context_index": 1,
            }
        ]

        nlp_data = NLPService.parse_query_heuristics("Explain product 1")
        res = QueryRouter.route_query(
            db=db,
            user_query="Explain product 1",
            nlp_data=nlp_data,
            active_products=active_products,
            session_id="test_session_explain"
        )

        assert "## ASUS ROG Zephyrus G14 Analysis" in res["answer"]
        assert "**Performance:**" in res["answer"]
        assert "**Memory:**" in res["answer"]
        assert "**Storage:**" in res["answer"]
        assert "**Best For:**" in res["answer"]
        print("✓ Product explanation test passed:\n", res["answer"])
    finally:
        db.close()


def test_battle_reason_routing():
    db = SessionLocal()
    try:
        active_products = [
            {
                "id": 1,
                "name": "ASUS ROG Zephyrus G14",
                "brand": "ASUS",
                "category": "Laptop",
                "price": 84990,
                "ram": "32GB",
                "ram_gb": 32,
                "storage": "512GB SSD",
                "processor": "AMD Ryzen 7 5800HS",
                "gpu": "NVIDIA GeForce GTX 1660 Ti",
                "score": 88,
                "context_index": 1,
            },
            {
                "id": 2,
                "name": "MSI GF63 Thin",
                "brand": "MSI",
                "category": "Laptop",
                "price": 54990,
                "ram": "8GB",
                "ram_gb": 8,
                "storage": "256GB SSD",
                "processor": "Intel Core i5-11400H",
                "gpu": "NVIDIA GeForce GTX 1650",
                "score": 75,
                "context_index": 2,
            }
        ]

        query = "Why did ASUS ROG Zephyrus win the battle?"
        nlp_data = NLPService.parse_query_heuristics(query)
        res = QueryRouter.route_query(
            db=db,
            user_query=query,
            nlp_data=nlp_data,
            active_products=active_products,
            session_id="test_session_battle"
        )

        assert res["type"] == "battle"
        assert "🏆 **AI Battle Verdict**" in res["answer"]
        assert "Winner:" in res["answer"]
        assert "Reasons:" in res["answer"]
        assert "🔥 **Performance**" in res["answer"]
        assert "💰 **Value**" in res["answer"]
        assert "⚡ **Overall**" in res["answer"]
        assert "Confidence:" in res["answer"]
        # Crucial check: It must NOT be just "RAM: 32GB"
        assert res["answer"].strip() != "RAM: 32GB"
        print("✓ Battle reasoning test passed:\n", res["answer"])
    finally:
        db.close()


def test_comparison_routing():
    db = SessionLocal()
    try:
        active_products = [
            {
                "id": 1,
                "name": "ASUS ROG Zephyrus G14",
                "brand": "ASUS",
                "category": "Laptop",
                "price": 84990,
                "ram": "32GB",
                "ram_gb": 32,
                "storage": "512GB SSD",
                "processor": "AMD Ryzen 7 5800HS",
                "gpu": "NVIDIA GeForce GTX 1660 Ti",
                "score": 88,
                "context_index": 1,
            },
            {
                "id": 2,
                "name": "MSI GF63 Thin",
                "brand": "MSI",
                "category": "Laptop",
                "price": 54990,
                "ram": "8GB",
                "ram_gb": 8,
                "storage": "256GB SSD",
                "processor": "Intel Core i5-11400H",
                "gpu": "NVIDIA GeForce GTX 1650",
                "score": 75,
                "context_index": 2,
            }
        ]

        query = "Compare ASUS and MSI"
        nlp_data = NLPService.parse_query_heuristics(query)
        res = QueryRouter.route_query(
            db=db,
            user_query=query,
            nlp_data=nlp_data,
            active_products=active_products,
            session_id="test_session_compare"
        )

        assert res["type"] == "comparison"
        assert "Technical Specification" in res["answer"]
        print("✓ Comparison test passed:\n", res["answer"][:200])
    finally:
        db.close()


if __name__ == "__main__":
    test_intent_detection()
    test_spec_query_routing()
    test_product_explanation_routing()
    test_battle_reason_routing()
    test_comparison_routing()
    print("\nALL 5 TESTS PASSED SUCCESSFULLY!")
