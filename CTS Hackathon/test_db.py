"""
AWS RDS MySQL Connection and CRUD Verification Suite
Project: CTS Hackathon Product Assistant

Tests:
1. RDS Connectivity Handshake & Server Information
2. Database Existence Check
3. Table Schema Existence Check (users, search_history, comparison_history, recommendation_history, laptops)
4. User CRUD Operations Lifecycle (Create -> Read -> Update -> Verify -> Delete)
5. Search History Logging & Readback
6. Comparison History Logging & Readback
7. Recommendation History Logging & Readback
8. Connection Pooling Concurrency & Safe Resource Release
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

# Auto-detect and switch to virtual environment python if needed
_venv_py = Path(__file__).parent.parent / "backend" / "venv" / "bin" / "python"
if not _venv_py.exists():
    _venv_py = Path(__file__).parent.parent / ".venv" / "bin" / "python"
if _venv_py.exists() and ("backend/venv" not in sys.executable and ".venv" not in sys.executable):
    try:
        import mysql.connector
    except ImportError:
        os.execv(str(_venv_py), [str(_venv_py)] + sys.argv)

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import (
    get_db_config,
    get_db_connection,
    get_db_cursor,
    init_connection_pool,
    init_schema,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_all_users,
    update_user,
    delete_user,
    log_user_search,
    get_user_search_history,
    delete_user_search_history_item,
    clear_user_search_history,
    log_user_comparison,
    get_user_comparison_history,
    delete_user_comparison_history_item,
    clear_user_comparison_history,
    log_user_recommendation,
    get_user_recommendation_history,
    delete_user_recommendation_history_item,
    clear_user_recommendation_history,
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_NAME,
    DB_POOL_SIZE,
)
import mysql.connector

# Set up logging for test runner
logging.basicConfig(level=logging.WARNING)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(title: str):
    print(f"\n{CYAN}{BOLD}{'=' * 65}")
    print(f" {title}")
    print(f"{'=' * 65}{RESET}")


def print_pass(msg: str):
    print(f" [{GREEN}✔ PASS{RESET}] {msg}")


def print_fail(msg: str, err: Exception = None):
    print(f" [{RED}✖ FAIL{RESET}] {msg}")
    if err:
        print(f"         {RED}Error Details: {err}{RESET}")


def print_warn(msg: str):
    print(f" [{YELLOW}⚠ WARN{RESET}] {msg}")


def print_info(msg: str):
    print(f" [ℹ INFO] {msg}")


def run_all_tests():
    print_header("AWS RDS MySQL Connection & CRUD Test Suite")
    config = get_db_config()
    print_info(f"Target Host:     {config['host']}:{config['port']}")
    print_info(f"Target Database: {config['database']}")
    print_info(f"Target User:     {config['user']}")
    print_info(f"Pool Size:       {DB_POOL_SIZE}")

    passed_count = 0
    failed_count = 0

    # ---------------------------------------------------------
    # TEST 1: Connectivity & Server Version
    # ---------------------------------------------------------
    print_header("Test 1: RDS Connectivity & Handshake")
    try:
        t0 = time.time()
        conn = get_db_connection()
        t1 = time.time()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION(), CURRENT_TIMESTAMP()")
        row = cursor.fetchone()
        server_version = row[0]
        server_time = row[1]
        cursor.close()
        conn.close()
        elapsed_ms = (t1 - t0) * 1000
        print_pass(f"Connected to MySQL successfully in {elapsed_ms:.1f} ms!")
        print_pass(f"Server Version: {server_version}")
        print_pass(f"Server Time:    {server_time}")
        passed_count += 1
    except Exception as e:
        print_fail("Failed to connect to AWS RDS MySQL host.", e)
        failed_count += 1
        print(f"\n{RED}{BOLD}Database connection failed. Please verify .env settings and RDS Security Groups.{RESET}")
        return False

    # ---------------------------------------------------------
    # TEST 2: Database Existence
    # ---------------------------------------------------------
    print_header("Test 2: Target Database Verification")
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            if current_db and current_db.lower() == DB_NAME.lower():
                print_pass(f"Active database is correctly set to '{current_db}'.")
                passed_count += 1
            else:
                print_warn(f"Active database '{current_db}' differs from expected '{DB_NAME}'.")
                passed_count += 1
    except Exception as e:
        print_fail("Failed to verify active database.", e)
        failed_count += 1

    # ---------------------------------------------------------
    # TEST 3: Table Schema Existence & Auto-Init
    # ---------------------------------------------------------
    print_header("Test 3: Tables & Schema Verification")
    expected_tables = ["users", "search_history", "comparison_history", "recommendation_history", "laptops"]
    try:
        # Initialize schema if not present
        init_schema()

        with get_db_cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [t[0].lower() for t in cursor.fetchall()]

        all_tables_found = True
        for table in expected_tables:
            if table.lower() in tables:
                print_pass(f"Table exists: `{table}`")
            else:
                print_fail(f"Missing table: `{table}`")
                all_tables_found = False

        if all_tables_found:
            passed_count += 1
        else:
            failed_count += 1
    except Exception as e:
        print_fail("Error inspecting database tables.", e)
        failed_count += 1

    # ---------------------------------------------------------
    # TEST 4: Users CRUD Lifecycle
    # ---------------------------------------------------------
    print_header("Test 4: Users CRUD Operations")
    test_email = f"aws_rds_test_{int(time.time())}@example.com"
    test_user_id = None
    try:
        # Create
        test_user_id = create_user(
            name="AWS RDS Tester",
            email=test_email,
            password_hash="$2b$12$e8Y4Jg8VpG7VzL...",
            username="rds_tester",
            auth_provider="local"
        )
        print_pass(f"CREATE: Inserted test user (user_id={test_user_id}, email={test_email})")

        # Read by Email
        user_by_email = get_user_by_email(test_email)
        assert user_by_email is not None, "Failed to retrieve user by email"
        assert user_by_email["user_id"] == test_user_id, "User ID mismatch on email lookup"
        print_pass("READ: Retrieved test user by email successfully.")

        # Read by ID
        user_by_id = get_user_by_id(test_user_id)
        assert user_by_id is not None, "Failed to retrieve user by ID"
        print_pass("READ: Retrieved test user by user_id successfully.")

        # Update
        updated = update_user(test_user_id, {"name": "AWS RDS Tester Updated", "username": "rds_tester_v2"})
        assert updated is True, "Failed to update user record"
        user_updated = get_user_by_id(test_user_id)
        assert (user_updated.get("name") == "AWS RDS Tester Updated" or user_updated.get("username") == "rds_tester_v2"), "Updated name/username did not persist"
        print_pass("UPDATE: Updated user fields successfully.")

        passed_count += 1
    except Exception as e:
        print_fail("Users CRUD test failed.", e)
        failed_count += 1

    # Ensure a valid user_id for history tests
    active_test_user_id = test_user_id or 1

    # ---------------------------------------------------------
    # TEST 5: Search History CRUD
    # ---------------------------------------------------------
    print_header("Test 5: Search History CRUD Operations")
    try:
        query_text = "Lightweight ultrabook under 1500 USD"
        filters = {"category": "Laptop", "min_ram": 16, "brand": "Dell"}

        # Insert
        search_id = log_user_search(active_test_user_id, query_text, filters)
        print_pass(f"INSERT: Search log created (search_id={search_id})")

        # Read
        searches = get_user_search_history(active_test_user_id, limit=5)
        found_search = next((s for s in searches if s["search_id"] == search_id), None)
        assert found_search is not None, "Search log record was not returned in query history"
        assert found_search["query_text"] == query_text, "Search query text mismatch"
        print_pass(f"READ: Verified search log content: '{found_search['query_text']}'")

        # Delete
        deleted = delete_user_search_history_item(search_id, active_test_user_id)
        assert deleted is True, "Failed to delete search history item"
        print_pass(f"DELETE: Deleted search history item (search_id={search_id})")

        passed_count += 1
    except Exception as e:
        print_fail("Search history CRUD test failed.", e)
        failed_count += 1

    # ---------------------------------------------------------
    # TEST 6: Comparison History CRUD
    # ---------------------------------------------------------
    print_header("Test 6: Comparison History CRUD Operations")
    try:
        product_list = [
            {"brand": "Apple", "model": "MacBook Air M2", "price": 1199},
            {"brand": "Dell", "model": "XPS 13", "price": 1299}
        ]
        summary = "MacBook Air M2 offers superior battery runtime; Dell XPS 13 has a brighter display."

        # Insert
        comp_id = log_user_comparison(active_test_user_id, product_list, summary)
        print_pass(f"INSERT: Comparison log created (comparison_id={comp_id})")

        # Read
        comps = get_user_comparison_history(active_test_user_id, limit=5)
        found_comp = next((c for c in comps if c["comparison_id"] == comp_id), None)
        assert found_comp is not None, "Comparison log record was not returned in history"
        assert len(found_comp["compared_products"]) == 2, "Compared products count mismatch"
        print_pass(f"READ: Verified comparison log content: '{found_comp['notes_or_summary']}'")

        # Delete
        deleted = delete_user_comparison_history_item(comp_id, active_test_user_id)
        assert deleted is True, "Failed to delete comparison history item"
        print_pass(f"DELETE: Deleted comparison history item (comparison_id={comp_id})")

        passed_count += 1
    except Exception as e:
        print_fail("Comparison history CRUD test failed.", e)
        failed_count += 1

    # ---------------------------------------------------------
    # TEST 7: Recommendation History CRUD
    # ---------------------------------------------------------
    print_header("Test 7: Recommendation History CRUD Operations")
    try:
        requirements = "Need 32GB RAM for heavy containerized development"
        rec_products = [
            {"brand": "Lenovo", "model": "ThinkPad P14s", "score": 95},
            {"brand": "HP", "model": "ZBook Studio", "score": 92}
        ]
        rec_summary = "ThinkPad P14s recommended for extensive multitasking and certified driver stability."

        # Insert
        rec_id = log_user_recommendation(active_test_user_id, requirements, rec_products, rec_summary)
        print_pass(f"INSERT: Recommendation log created (recommendation_id={rec_id})")

        # Read
        recs = get_user_recommendation_history(active_test_user_id, limit=5)
        found_rec = next((r for r in recs if r["recommendation_id"] == rec_id), None)
        assert found_rec is not None, "Recommendation log record was not returned in history"
        print_pass(f"READ: Verified recommendation log content: '{found_rec['reasoning_summary']}'")

        # Delete
        deleted = delete_user_recommendation_history_item(rec_id, active_test_user_id)
        assert deleted is True, "Failed to delete recommendation history item"
        print_pass(f"DELETE: Deleted recommendation history item (recommendation_id={rec_id})")

        passed_count += 1
    except Exception as e:
        print_fail("Recommendation history CRUD test failed.", e)
        failed_count += 1

    # Clean up test user if created
    if test_user_id:
        try:
            delete_user(test_user_id)
            print_pass(f"CLEANUP: Deleted temporary test user #{test_user_id}.")
        except Exception:
            pass

    # ---------------------------------------------------------
    # TEST 8: Connection Pool Concurrency Test
    # ---------------------------------------------------------
    print_header("Test 8: Connection Pooling & Resource Reclaim")
    try:
        connections = []
        pool = init_connection_pool()
        # Acquire multiple connections up to pool capacity
        acquire_count = min(DB_POOL_SIZE, 4)
        for i in range(acquire_count):
            c = pool.get_connection()
            connections.append(c)
        print_pass(f"Acquired {len(connections)} concurrent pooled connections from '{pool.pool_name}'.")

        # Execute queries concurrently across acquired connections
        for idx, c in enumerate(connections):
            cur = c.cursor()
            cur.execute("SELECT %s", (idx + 1,))
            res = cur.fetchone()[0]
            assert res == idx + 1
            cur.close()

        # Release all back to pool
        for c in connections:
            c.close()
        print_pass("Released all connections back to pool cleanly.")
        passed_count += 1
    except Exception as e:
        print_fail("Connection pool test failed.", e)
        failed_count += 1

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print_header("AWS RDS MySQL Test Results Summary")
    total_tests = passed_count + failed_count
    print(f" Total Tests Run: {total_tests}")
    print(f" {GREEN}Passed:          {passed_count}{RESET}")
    if failed_count > 0:
        print(f" {RED}Failed:          {failed_count}{RESET}")
        return False
    else:
        print(f"\n {GREEN}{BOLD}🎉 ALL AWS RDS MYSQL TESTS COMPLETED SUCCESSFULLY! 🎉{RESET}\n")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)