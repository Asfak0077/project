"""
Comprehensive Verification Suite for Complete AI Chat Pipeline:
1. Product Index Resolution: "price of product 3" -> Product 3 price (not product 1)
2. Direct MySQL Spec Fast-Path: "ram" -> Resolves active product RAM directly from MySQL
3. Multi-Product Comparison: "compare product 1 and 2" -> Compares only selected items
4. RAG Document Intelligence: "explain this document" -> RAG VER2 with source attribution
5. Session Context & Reload Restoration: Chat context persisted & restored from MySQL
6. Multi-User Database Isolation: User A cannot see or mutate User B data
7. Clean Friendly Error Handling: No raw Pydantic / 500 tracebacks exposed
"""
import unittest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models.user import User
from models.chat_history import ChatHistory
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter
from services.auth_service import create_access_token

client = TestClient(app)

SAMPLE_CONTEXT_PRODUCTS = [
    {
        "index": 1,
        "id": 1,
        "product_id": 1,
        "brand": "MSI",
        "name": "Titan Pro GT73VR-7RF",
        "price": 105790,
        "ram": 32,
        "ram_gb": 32,
        "processor": "Intel Core i7 7820HK",
        "storage": "512GB SSD",
        "category": "Laptop",
    },
    {
        "index": 2,
        "id": 2,
        "product_id": 2,
        "brand": "MSI",
        "name": "Titan Pro GT73VR-7RF",
        "price": 105790,
        "ram": 32,
        "ram_gb": 32,
        "processor": "Intel Core i7 7820HK",
        "storage": "512GB SSD",
        "category": "Laptop",
    },
    {
        "index": 3,
        "id": 3,
        "product_id": 3,
        "brand": "ASUS",
        "name": "ROG Zephyrus G GA502",
        "price": 79990,
        "ram": 16,
        "ram_gb": 16,
        "processor": "AMD Ryzen 7 3750H",
        "storage": "512GB SSD",
        "category": "Laptop",
    },
]


def test_scenario_1_product_3_index_resolution():
    """Verify 'price of product 3' returns ₹79,990 (ASUS ROG) and NOT ₹105,790 (MSI Titan)."""
    db = SessionLocal()
    try:
        nlp_res = NLPService.parse_query_heuristics(
            query="What is its price of product 3?",
            conversation_context={"active_products": SAMPLE_CONTEXT_PRODUCTS},
        )
        assert nlp_res["target_product_index"] == 3
        assert nlp_res["spec_field"] == "price"
        assert nlp_res["intent"] == IntentType.PRODUCT_PRICE

        route_res = QueryRouter.route_query(
            user_query="What is its price of product 3?",
            nlp_data=nlp_res,
            active_products=SAMPLE_CONTEXT_PRODUCTS,
            db=db,
        )

        assert route_res["verified"] is True
        assert "79,990" in route_res["answer"]
        assert "105,790" not in route_res["answer"]
        assert route_res["product"]["name"] == "ROG Zephyrus G GA502"
        assert route_res["product"]["id"] == 3
        assert route_res["debug_trace"]["route_selected"] == "MYSQL_DATABASE_SPEC"
        print("✓ Scenario 1 PASS: 'price of product 3' correctly resolved Product 3 (₹79,990)")
    finally:
        db.close()


def test_scenario_2_direct_mysql_spec_fastpath():
    """Verify single attribute queries (ram, battery, storage) use MySQL directly."""
    db = SessionLocal()
    try:
        nlp_res = NLPService.parse_query_heuristics(
            query="ram",
            conversation_context={"active_products": [SAMPLE_CONTEXT_PRODUCTS[2]]},
        )
        assert nlp_res["spec_field"] == "ram"
        assert nlp_res["intent"] == IntentType.PRODUCT_RAM

        route_res = QueryRouter.route_query(
            user_query="ram",
            nlp_data=nlp_res,
            active_products=[SAMPLE_CONTEXT_PRODUCTS[2]],
            db=db,
        )

        assert route_res["verified"] is True
        assert "RAM: 16GB" in route_res["answer"]
        assert route_res["debug_trace"]["route_selected"] == "MYSQL_DATABASE_SPEC"
        print("✓ Scenario 2 PASS: 'ram' fast-path answered directly from MySQL (RAM: 16GB)")
    finally:
        db.close()


def test_scenario_3_two_product_comparison():
    """Verify 'compare product 1 and 2' isolates only products 1 & 2 without mixing product 3."""
    db = SessionLocal()
    try:
        nlp_res = NLPService.parse_query_heuristics(
            query="compare product 1 and 2",
            conversation_context={"active_products": SAMPLE_CONTEXT_PRODUCTS},
        )
        assert nlp_res["is_comparison"] is True
        assert nlp_res["selected_indices"] == [1, 2]

        route_res = QueryRouter.route_query(
            user_query="compare product 1 and 2",
            nlp_data=nlp_res,
            active_products=SAMPLE_CONTEXT_PRODUCTS,
            db=db,
        )

        assert len(route_res.get("compared_products", [])) == 2
        compared_ids = [p["id"] for p in route_res["compared_products"]]
        assert 1 in compared_ids
        assert 2 in compared_ids
        assert 3 not in compared_ids
        print("✓ Scenario 3 PASS: 'compare product 1 and 2' compared only products 1 and 2")
    finally:
        db.close()


def test_scenario_4_rag_document_query():
    """Verify explicit PDF/manual queries route to RAG VER2 with source badges."""
    db = SessionLocal()
    try:
        nlp_res = NLPService.parse_query_heuristics(
            query="What does the datasheet say about cooling architecture?",
            conversation_context={"active_products": [SAMPLE_CONTEXT_PRODUCTS[2]]},
        )
        assert nlp_res["is_document_query"] is True

        route_res = QueryRouter.route_query(
            user_query="What does the datasheet say about cooling architecture?",
            nlp_data=nlp_res,
            active_products=[SAMPLE_CONTEXT_PRODUCTS[2]],
            db=db,
        )

        assert route_res["intent"] == IntentType.DOCUMENT_QUERY
        assert route_res["source_type"] == "documents"
        assert route_res["show_sources"] is True
        assert route_res["debug_trace"]["route_selected"] == "RAG_VER2_DOCUMENTS"
        print("✓ Scenario 4 PASS: Datasheet cooling query routed to RAG VER2 with sources")
    finally:
        db.close()


def test_scenario_5_session_reload_restoration():
    """Verify context and conversation history are persisted and restorable for authenticated sessions."""
    db = SessionLocal()
    try:
        test_user = db.query(User).first()
        if not test_user:
            test_user = User(name="Test Suite User", email="test_pipeline@example.com")
            db.add(test_user)
            db.commit()
            db.refresh(test_user)

        cid = "test_conv_reload_restore_999"

        # Simulate sending a chat message via HTTP API
        token = create_access_token(user_id=test_user.id, email=test_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/chat",
            json={
                "message": "What is the price of product 3?",
                "context_products": SAMPLE_CONTEXT_PRODUCTS,
                "session_id": cid,
                "conversation_id": cid,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["product"]["id"] == 3
        expected_price_str = f"Price: ₹{int(data['product']['price']):,}"
        assert data["answer"] == expected_price_str

        # Verify context is stored in MySQL
        ctx_resp = client.get(f"/api/chat/context/{cid}", headers=headers)
        assert ctx_resp.status_code == 200
        ctx_data = ctx_resp.json()
        assert len(ctx_data.get("active_products", [])) == 3

        # Verify messages history is stored in MySQL
        hist_resp = client.get(f"/api/chat/conversations/{cid}/messages", headers=headers)
        assert hist_resp.status_code == 200
        msgs = hist_resp.json()
        assert len(msgs) >= 2  # user message + assistant response
        print("✓ Scenario 5 PASS: Session reload restored conversation and active context from MySQL")
    finally:
        db.close()


def test_scenario_6_multi_user_isolation():
    """Verify User A cannot access User B's conversation or history."""
    db = SessionLocal()
    try:
        user_a = db.query(User).filter(User.email == "user_a_isolation@example.com").first()
        if not user_a:
            user_a = User(name="User A", email="user_a_isolation@example.com")
            db.add(user_a)
            db.commit()
            db.refresh(user_a)

        user_b = db.query(User).filter(User.email == "user_b_isolation@example.com").first()
        if not user_b:
            user_b = User(name="User B", email="user_b_isolation@example.com")
            db.add(user_b)
            db.commit()
            db.refresh(user_b)

        token_a = create_access_token(user_id=user_a.id, email=user_a.email)
        token_b = create_access_token(user_id=user_b.id, email=user_b.email)

        cid_a = "conv_user_a_private_123"

        # User A sends a private query
        client.post(
            "/api/chat",
            json={
                "message": "User A secret message",
                "session_id": cid_a,
                "conversation_id": cid_a,
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # User B queries User A's conversation
        b_get = client.get(
            f"/api/chat/conversations/{cid_a}/messages",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert b_get.status_code == 200
        assert b_get.json() == []  # Completely isolated, returns 0 messages for unauthorized user

        print("✓ Scenario 6 PASS: Strict multi-user database isolation enforced")
    finally:
        db.close()


def test_scenario_7_clean_friendly_error_handling():
    """Verify out-of-bounds index query returns friendly guidance without 422/500 traceback."""
    db = SessionLocal()
    try:
        nlp_res = NLPService.parse_query_heuristics(
            query="What is the price of product 99?",
            conversation_context={"active_products": SAMPLE_CONTEXT_PRODUCTS},
        )
        route_res = QueryRouter.route_query(
            user_query="What is the price of product 99?",
            nlp_data=nlp_res,
            active_products=SAMPLE_CONTEXT_PRODUCTS,
            db=db,
        )

        assert route_res["type"] == "error"
        assert "I have only 3 products in the current context" in route_res["answer"]
        print("✓ Scenario 7 PASS: Out-of-bounds product index returned clean user-friendly guidance")
    finally:
        db.close()


if __name__ == "__main__":
    test_scenario_1_product_3_index_resolution()
    test_scenario_2_direct_mysql_spec_fastpath()
    test_scenario_3_two_product_comparison()
    test_scenario_4_rag_document_query()
    test_scenario_5_session_reload_restoration()
    test_scenario_6_multi_user_isolation()
    test_scenario_7_clean_friendly_error_handling()
    print("\n=======================================================")
    print("ALL 7 VERIFICATION SCENARIOS PASSED WITH 100% SUCCESS!")
    print("=======================================================")
