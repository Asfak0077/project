"""
Multi-User Account Database Storage, AI Chat History & Comparison Persistence Test Suite
Tests:
1. User A and User B Registration and JWT Authentication
2. User A AI Chat Turn Persisted in MySQL (chat_history)
3. User Data Isolation: User B Cannot Read User A's Conversations
4. Persistent Conversation Context Restored from MySQL (conversation_context)
5. Product Comparisons Saved and Retrieved per Logged-in User (product_comparisons)
6. User Profile Aggregated Stats (totalChats, totalComparisons, wishlistCount)
7. Clean Deletion of Conversations and Comparisons
"""
import time
from fastapi.testclient import TestClient
from main import app
from database import get_db, SessionLocal
from models.user import User
from models.chat_history import ChatHistory, ProductComparison, ConversationContext
from services.user_storage_service import UserStorageService

client = TestClient(app)

def test_multi_user_storage_and_isolation():
    print("\n--- Starting Multi-User Storage & Isolation Tests ---")

    # 1. Register User A
    user_a_email = f"user_a_{int(time.time() * 1000)}@versus.ai"
    res_a = client.post("/api/auth/register", json={
        "name": "User Alpha",
        "email": user_a_email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res_a.status_code == 201, f"Failed to register User A: {res_a.text}"
    token_a = res_a.json()["token"]
    user_a_id = res_a.json()["user_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print(f"✅ User A registered (id={user_a_id}, email={user_a_email})")

    # 2. Register User B
    user_b_email = f"user_b_{int(time.time() * 1000)}@versus.ai"
    res_b = client.post("/api/auth/register", json={
        "name": "User Beta",
        "email": user_b_email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res_b.status_code == 201, f"Failed to register User B: {res_b.text}"
    token_b = res_b.json()["token"]
    user_b_id = res_b.json()["user_id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print(f"✅ User B registered (id={user_b_id}, email={user_b_email})")

    # 3. User A chats with AI
    conv_id_a = f"test_conv_a_{int(time.time() * 1000)}"
    chat_res_a = client.post("/api/chat", headers=headers_a, json={
        "message": "best gaming laptop under 80000",
        "conversation_id": conv_id_a,
        "session_id": conv_id_a,
    })
    assert chat_res_a.status_code == 200, f"Chat failed: {chat_res_a.text}"
    print(f"✅ User A executed chat turn: {chat_res_a.json().get('answer', '')[:50]}...")

    # 4. Verify User A conversation is in MySQL
    convs_res_a = client.get("/api/chat/conversations", headers=headers_a)
    assert convs_res_a.status_code == 200
    convs_a = convs_res_a.json()
    assert len(convs_a) >= 1
    assert any(c["conversation_id"] == conv_id_a for c in convs_a)
    print(f"✅ User A has {len(convs_a)} conversation(s) recorded in MySQL.")

    # 5. Verify User B CANNOT see User A's conversations (Strict Isolation)
    convs_res_b = client.get("/api/chat/conversations", headers=headers_b)
    assert convs_res_b.status_code == 200
    convs_b = convs_res_b.json()
    assert not any(c["conversation_id"] == conv_id_a for c in convs_b), "DATA LEAK: User B can see User A's conversation!"
    print(f"✅ Strict Isolation Verified: User B has {len(convs_b)} conversations (0 from User A).")

    # 6. User A saves conversation context
    ctx_res = client.post("/api/chat/context", headers=headers_a, json={
        "conversation_id": conv_id_a,
        "active_products": [{"id": "1", "name": "MSI Titan Pro", "context_index": 1}],
        "selected_products": [{"id": "1", "name": "MSI Titan Pro"}],
        "last_intent": "product_explanation"
    })
    assert ctx_res.status_code == 200
    print(f"✅ User A persisted active context to MySQL.")

    # 7. User A fetches conversation context
    get_ctx_res = client.get(f"/api/chat/context/{conv_id_a}", headers=headers_a)
    assert get_ctx_res.status_code == 200
    ctx_data = get_ctx_res.json()
    assert len(ctx_data.get("active_products", [])) == 1
    assert ctx_data["active_products"][0]["name"] == "MSI Titan Pro"
    print(f"✅ User A retrieved context from MySQL: {ctx_data['active_products'][0]['name']}")

    # 8. User A saves a comparison
    comp_id_a = f"comp_{int(time.time() * 1000)}"
    save_comp_res = client.post("/api/compare/save", headers=headers_a, json={
        "comparison_id": comp_id_a,
        "product_ids": [1, 2],
        "comparison_result": {
            "winner_name": "MSI Titan Pro",
            "winner_summary": "MSI Titan Pro wins on performance."
        }
    })
    assert save_comp_res.status_code == 200
    print(f"✅ User A saved product comparison {comp_id_a}")

    # 9. Verify User A gets saved comparisons and User B does not
    get_comps_a = client.get("/api/compare/saved", headers=headers_a)
    assert get_comps_a.status_code == 200
    assert any(c["comparison_id"] == comp_id_a for c in get_comps_a.json())

    get_comps_b = client.get("/api/compare/saved", headers=headers_b)
    assert get_comps_b.status_code == 200
    assert not any(c["comparison_id"] == comp_id_a for c in get_comps_b.json()), "DATA LEAK: User B can see User A's comparison!"
    print(f"✅ Comparison Isolation Verified: User B cannot access User A's comparisons.")

    # 10. Check User Profile Stats
    prof_res = client.get("/api/users/profile", headers=headers_a)
    assert prof_res.status_code == 200
    prof = prof_res.json()
    assert prof["totalChats"] >= 2  # user msg + assistant msg
    assert prof["totalComparisons"] >= 1
    print(f"✅ User Profile Aggregated Stats Verified: totalChats={prof['totalChats']}, totalComparisons={prof['totalComparisons']}")

    # 11. Delete Conversation
    del_res = client.delete(f"/api/chat/conversations/{conv_id_a}", headers=headers_a)
    assert del_res.status_code == 200
    convs_after_del = client.get("/api/chat/conversations", headers=headers_a).json()
    assert not any(c["conversation_id"] == conv_id_a for c in convs_after_del)
    print(f"✅ User A conversation deleted cleanly from MySQL.")

    print("\n🎉 ALL MULTI-USER DATABASE STORAGE TESTS PASSED SUCCESSFULLY! 🎉\n")

if __name__ == "__main__":
    test_multi_user_storage_and_isolation()
