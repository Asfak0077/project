"""
RAG VER2 Migration and Full Project Integration Automated Verification Suite
Verifies all 12 test requirements from section 27 of the specifications.
"""
from __future__ import annotations

import os
import sys
import time
import json
import logging
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Ensure local SQLite fallback works cleanly for tests without AWS RDS network dependency
os.environ["DB_HOST"] = "localhost"
os.environ["DB_USER"] = "test"
os.environ["DB_PASSWORD"] = ""

from utils.config import settings
from services.rag_service import RAGService, ACTIVE_RAG_VERSION
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter
from database import SessionLocal

logging.basicConfig(level=logging.WARNING)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{CYAN}{BOLD}{'=' * 70}")
    print(f" {title}")
    print(f"{'=' * 70}{RESET}")

def print_pass(msg: str):
    print(f" [{GREEN}✔ PASS{RESET}] {msg}")

def print_fail(msg: str, err: Exception = None):
    print(f" [{RED}✖ FAIL{RESET}] {msg}")
    if err:
        print(f"         {RED}Error Details: {err}{RESET}")

def run_all_tests() -> bool:
    print_header("RAG VER2 Migration Verification Suite (12 Tests)")
    passed = 0
    failed = 0

    # ---------------------------------------------------------
    # TEST 1: Active Import Graph Check
    # ---------------------------------------------------------
    print_header("Test 1: Active Import Graph Check")
    try:
        backend_files = list(BACKEND_DIR.glob("**/*.py"))
        found_legacy = []
        for bf in backend_files:
            if "venv" in str(bf) or "__pycache__" in str(bf) or "test_" in bf.name:
                continue
            with open(bf, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "import laptop_comparison_rag" in content or "from laptop_comparison_rag" in content:
                    found_legacy.append(str(bf))
        
        assert len(found_legacy) == 0, f"Found legacy imports in: {found_legacy}"
        print_pass("Zero active imports from 'laptop_comparison_rag' in backend codebase.")
        passed += 1
    except Exception as e:
        print_fail("Legacy import found in backend", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 2: Active RAG Version Guard
    # ---------------------------------------------------------
    print_header("Test 2: RAG Service Version Guard")
    try:
        version = RAGService.get_version()
        assert version == "ver2", f"Expected version 'ver2', got '{version}'"
        print_pass(f"RAGService.get_version() authoritative report: '{version}'.")
        passed += 1
    except Exception as e:
        print_fail("RAG version verification failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 3: Health Check & Collection Counts
    # ---------------------------------------------------------
    print_header("Test 3: RAG Health Check & Collections Verification")
    try:
        health = RAGService.check_health()
        assert health["status"] == "healthy", f"Health status was {health.get('status')}: {health.get('message')}"
        assert health["rag_version"] == "ver2", f"Health rag_version was {health.get('rag_version')}"
        assert "laptops" in health["collections"], "Missing 'laptops' collection"
        assert health["collections"]["laptops"] >= 2000, f"Expected >2000 laptops, found {health['collections']['laptops']}"
        print_pass(f"RAG Health Status: {health['status'].upper()} | Version: {health['rag_version']}")
        print_pass(f"Collections Loaded: {health['collections']}")
        passed += 1
    except Exception as e:
        print_fail("Health check failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 4: Dataset Paths Verification
    # ---------------------------------------------------------
    print_header("Test 4: VER2 Dataset Integrity")
    try:
        dataset_dir = Path(settings.RAG_VER2_ROOT) / "data" / "processed"
        assert dataset_dir.exists(), f"Dataset directory missing at {dataset_dir}"
        laptop_corpus = dataset_dir / "laptop_rag_corpus.json"
        assert laptop_corpus.exists() and laptop_corpus.stat().st_size > 100000, "laptop_rag_corpus.json missing or empty"
        print_pass(f"Datasets verified in {dataset_dir}")
        print_pass(f"Laptop corpus size: {laptop_corpus.stat().st_size / 1024:.1f} KB")
        passed += 1
    except Exception as e:
        print_fail("Dataset path verification failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 5: Vector Index Verification
    # ---------------------------------------------------------
    print_header("Test 5: VER2 Vector Index Verification")
    try:
        vdb_path = Path(settings.RAG_VECTOR_DB_PATH)
        assert vdb_path.exists(), f"Vector DB missing at {vdb_path}"
        sqlite_file = vdb_path / "chroma.sqlite3"
        assert sqlite_file.exists() and sqlite_file.stat().st_size > 1000000, "chroma.sqlite3 missing or small"
        print_pass(f"ChromaDB index verified at {vdb_path}")
        print_pass(f"Vector DB file size: {sqlite_file.stat().st_size / (1024*1024):.1f} MB")
        passed += 1
    except Exception as e:
        print_fail("Vector index verification failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 6: Embedding Model Compatibility
    # ---------------------------------------------------------
    print_header("Test 6: Embedding Model Configuration")
    try:
        model_name = settings.RAG_EMBEDDING_MODEL
        assert model_name == "all-MiniLM-L6-v2", f"Unexpected model name: {model_name}"
        engine = RAGService.get_engine()
        assert engine.embedding_model == model_name, "Engine embedding model mismatch"
        print_pass(f"Embedding model verified: {model_name}")
        passed += 1
    except Exception as e:
        print_fail("Embedding model check failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 7: Simple RAG Query Execution
    # ---------------------------------------------------------
    print_header("Test 7: Simple RAG Query")
    try:
        res = RAGService.query_rag(query="lightweight laptop for travel", category="laptop", top_k=3)
        assert res["rag_version"] == "ver2", f"RAG version mismatch in response: {res.get('rag_version')}"
        assert len(res["results"]) > 0, "No candidate results returned"
        assert res["answer"] is not None and len(res["answer"]) > 10, "Empty grounded answer"
        print_pass(f"Query returned {len(res['results'])} candidates with RAG version '{res['rag_version']}'")
        print_pass(f"Top candidate: {res['results'][0]['product_name']}")
        passed += 1
    except Exception as e:
        print_fail("Simple RAG query failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 8: Product-Specific Context Query
    # ---------------------------------------------------------
    print_header("Test 8: Product-Specific Context Retrieval")
    try:
        res = RAGService.query_rag(query="Asus Intel Core i5", category="laptop", top_k=3)
        assert len(res["results"]) > 0, "No Asus laptops found"
        # Check brand in results
        first_content = res["results"][0]["content"]
        assert "Asus" in first_content or "asus" in first_content.lower(), f"Expected Asus in top result, got: {first_content}"
        print_pass("Product-specific query correctly returned Asus target context.")
        print_pass(f"Result snippet: {res['results'][0]['content'][:120]}...")
        passed += 1
    except Exception as e:
        print_fail("Product-specific query failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 9: Category Routing & Metadata Filtering
    # ---------------------------------------------------------
    print_header("Test 9: Multi-Category Routing (Mobiles & Tablets)")
    try:
        mob_res = RAGService.query_rag(query="Samsung 5G 128GB", category="mobile", top_k=2)
        tab_res = RAGService.query_rag(query="Apple iPad tablet", category="tablet", top_k=2)
        assert len(mob_res["results"]) > 0, "Mobile collection query failed"
        assert len(tab_res["results"]) > 0, "Tablet collection query failed"
        print_pass(f"Mobile category returned {len(mob_res['results'])} items (Sample: {mob_res['results'][0]['product_name']})")
        print_pass(f"Tablet category returned {len(tab_res['results'])} items (Sample: {tab_res['results'][0]['product_name']})")
        passed += 1
    except Exception as e:
        print_fail("Category routing failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 10: Anti-Hallucination on Empty / Missing Retrieval
    # ---------------------------------------------------------
    print_header("Test 10: Anti-Hallucination Grounding")
    try:
        # Empty snippet test
        grounded = RAGService.query_rag(query="", category="laptop")
        assert "Query cannot be empty" in grounded["answer"] or "couldn't find" in grounded["answer"].lower()
        print_pass("Anti-hallucination guard verified for unverified/empty inputs.")
        passed += 1
    except Exception as e:
        print_fail("Anti-hallucination check failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 11: End-to-End NLP & Query Router Integration
    # ---------------------------------------------------------
    print_header("Test 11: End-to-End Query Router RAG VER2 Flow")
    try:
        db = SessionLocal()
        nlp_out = NLPService.parse_query_heuristics("What does the datasheet say about battery performance?")
        assert nlp_out["intent"] == IntentType.RAG_DOCUMENT_QUERY, f"Expected RAG intent, got {nlp_out['intent']}"
        
        router_res = QueryRouter.route_query(
            db=db,
            user_query="What does the datasheet say about battery performance?",
            nlp_data=nlp_out,
            active_products=[],
        )
        db.close()
        assert router_res["intent"] == IntentType.RAG_DOCUMENT_QUERY
        assert router_res["rag_version"] == "ver2"
        assert len(router_res["sources"]) > 0
        print_pass("QueryRouter correctly routed RAG query and produced ver2 response.")
        print_pass(f"Answer Preview: {router_res['answer'][:120]}...")
        passed += 1
    except Exception as e:
        print_fail("Query Router end-to-end flow failed", e)
        failed += 1

    # ---------------------------------------------------------
    # TEST 12: Unified Document Query Bridge
    # ---------------------------------------------------------
    print_header("Test 12: Unified Document Query Bridge")
    try:
        doc_res = RAGService.query_documents(db=None, query="Dell Inspiron specifications", top_k=3)
        assert doc_res["rag_version"] == "ver2"
        assert len(doc_res["results"]) > 0
        print_pass(f"Unified document query bridge returned {len(doc_res['results'])} candidates with rag_version='ver2'.")
        passed += 1
    except Exception as e:
        print_fail("Unified document query bridge failed", e)
        failed += 1

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    print_header("RAG VER2 Verification Results Summary")
    total = passed + failed
    print(f" Total Tests Run: {total}")
    print(f" {GREEN}Passed:          {passed} / {total}{RESET}")
    if failed > 0:
        print(f" {RED}Failed:          {failed} / {total}{RESET}")
        return False
    else:
        print(f"\n {GREEN}{BOLD}🎉 ALL 12 RAG VER2 MIGRATION TESTS COMPLETED WITH 100% PASS RATE! 🎉{RESET}\n")
        return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
