import os
from pathlib import Path
from conversation_memory import ConversationMemory

# Define the path to your database
DB_PATH = Path("../data/conversation_memory.db")

def main():
    print("=" * 60)
    print("PROCESS 1: INITIALIZATION & RECOMMENDATION")
    print("=" * 60)
    
    # 1. Start the 'first' Python process
    memory_process_1 = ConversationMemory(db_path=DB_PATH)
    session_id = memory_process_1.create_session()
    print(f"[+] Created Session ID: {session_id}")

    # 2. Add a recommendation containing 3 products
    memory_process_1.record_completed_turn(
        session_id=session_id,
        user_query="Show me some laptops.",
        assistant_response="Here are three laptops:",
        presented_products=[
            {"product_id": "LAP_001", "product_name": "Asus ROG", "brand": "Asus", "price_inr": 70000, "metadata": {}},
            {"product_id": "LAP_002", "product_name": "HP Pavilion", "brand": "HP", "price_inr": 55000, "metadata": {}},
            {"product_id": "LAP_003", "product_name": "Lenovo ThinkPad", "brand": "Lenovo", "price_inr": 60000, "metadata": {}},
        ]
    )
    print("[+] Recorded turn with 3 presented products (Asus, HP, Lenovo).")

    # 3. STOP THE PYTHON PROCESS
    print("\n[!] SIMULATING PROCESS CRASH / RESTART...")
    del memory_process_1
    # At this exact moment, the Python memory is wiped clean. 
    # Only the SQLite .db file holds the truth.

    print("\n" + "=" * 60)
    print("PROCESS 2: REBOOT & RESOLUTION")
    print("=" * 60)

    # 4. Start it again (New Memory Object)
    memory_process_2 = ConversationMemory(db_path=DB_PATH)
    print("[+] Rebooted ConversationMemory system.")

    # 5. Open the same session_id and resolve "second one"
    print(f"[-] Attempting to resolve 'the second one' for Session: {session_id}")
    
    resolved_product = memory_process_2.resolve_ordinal_reference(
        session_id=session_id,
        text="Can you give me more details on the second one?"
    )

    if resolved_product:
        print("\n[SUCCESS] Product Resolved!")
        print(f"  -> Expected: LAP_002 (HP Pavilion)")
        print(f"  -> Actual:   {resolved_product.product_id} ({resolved_product.product_name})")
        
        if resolved_product.product_id == "LAP_002":
            print("\n✅ TEST PASSED: State survived process death and correctly resolved the ordinal reference!")
        else:
            print("\n❌ TEST FAILED: Resolved the wrong product.")
    else:
        print("\n❌ TEST FAILED: Could not resolve the product.")

    # Clean up the test session so it doesn't clutter your database
    memory_process_2.delete_session(session_id)

if __name__ == "__main__":
    main()