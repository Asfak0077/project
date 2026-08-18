"""
Multi-Category Intelligent Query Router
Routes queries deterministically across Laptops, Phones, and Tablets to the exact required service:
- MySQL Ground Truth (for Price, RAM, Storage, Processor, GPU, Battery, Camera, Display)
- RAG VER2 Vector & Document Engine (for PDF, Manuals, Datasheets, Thermal/Cooling, Warranty)
- Category Recommendation Engine (for Best, Recommend, Suggest, Budget constraints)
- Category Comparison Engine (for Side-by-side Matrix with strict explicit context selection)
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from services.nlp_service import IntentType
from services.product_service import ProductService
from services.fact_validation_service import FactValidationService
from services.comparison_service import ComparisonService
from services.recommendation_service import RecommendationService
from services.rag_service import RAGService
from services.technical_analysis_service import TechnicalAnalysisService
from services.response_service import ResponseService
from services.conversation_memory_service import ConversationMemoryService
from services.product_data_validator import normalize_product_name
from services.response_cache import spec_cache
from services.battle_service import BattleService

logger = logging.getLogger("backend.query_router")


class QueryRouter:
    @classmethod
    def detect_comparison_products(
        cls,
        nlp_data: Dict[str, Any],
        active_products: List[Dict[str, Any]],
        db: Session,
        session_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[Any]]:
        """
        Deterministically resolve products for comparison adhering to strict selection priority:
        1. User selected indices/numbers (e.g. "compare 1 and 2", "compare 2 and 3", "compare 1 and 3", "first two")
        2. User mentioned product names (e.g. "compare MSI and ASUS")
        3. Previous comparison context in memory session (e.g. "Which has better GPU?")
        4. Active context window (if is_compare_all, or default to first 2)

        Returns:
            (comparison_products, ignored_product_ids)
        """
        selected_indices = nlp_data.get("selected_indices", [])
        is_compare_all = nlp_data.get("is_compare_all", False)
        product_names = nlp_data.get("product_names", [])

        comparison_products: List[Dict[str, Any]] = []

        # Priority 1: User explicitly selected product indices (e.g. "compare 1 and 3", "compare 2 and 3", "first two")
        if selected_indices and active_products:
            for idx in selected_indices:
                actual_idx = idx - 1 if idx > 0 else len(active_products) + idx
                if 0 <= actual_idx < len(active_products):
                    p = active_products[actual_idx]
                    if p and p.get("id") not in [cp.get("id") for cp in comparison_products]:
                        comparison_products.append(p)

        # Priority 2: User mentioned explicit product names (e.g. "compare MSI and ASUS")
        if len(comparison_products) < 2 and product_names:
            for p_name in product_names:
                matched_in_context = False
                for p in active_products:
                    if not p:
                        continue
                    full_name = f"{p.get('brand', '')} {p.get('name', '')}".lower()
                    if p_name.lower() in full_name:
                        if p.get("id") not in [cp.get("id") for cp in comparison_products]:
                            comparison_products.append(p)
                            matched_in_context = True
                            break
                if not matched_in_context:
                    # Query MySQL database
                    found = ProductService.search_by_name(db, p_name, limit=1)
                    if found and found[0]["id"] not in [cp.get("id") for cp in comparison_products]:
                        comparison_products.append(found[0])

        # Priority 2.5: User mentioned a brand (e.g. "Why did ASUS win?")
        brand = nlp_data.get("brand")
        if len(comparison_products) < 2 and brand:
            for p in active_products:
                if not p:
                    continue
                if brand.lower() in p.get("brand", "").lower() or brand.lower() in p.get("name", "").lower():
                    if p.get("id") not in [cp.get("id") for cp in comparison_products]:
                        comparison_products.append(p)
                        break
            if not comparison_products and db:
                found = ProductService.search_by_name(db, brand, limit=1)
                if found and found[0]["id"] not in [cp.get("id") for cp in comparison_products]:
                    comparison_products.append(found[0])

        # Priority 3: Previous comparison context in session memory (for follow-ups like "Which has better GPU?")
        if len(comparison_products) < 2 and session_id:
            mem_session = ConversationMemoryService.get_or_create(session_id)
            if mem_session.current_comparison_set and len(mem_session.current_comparison_set) >= 2:
                comparison_products = list(mem_session.current_comparison_set)

        # Priority 4: Active context window
        if len(comparison_products) < 2 and active_products:
            if is_compare_all:
                comparison_products = list(active_products)
            elif len(active_products) == 2:
                comparison_products = list(active_products)
            elif len(active_products) > 2:
                # If no specific indices/names and not compare all, pick first 2
                comparison_products = list(active_products[:2])

        # Calculate ignored products from active_products
        comp_ids = {cp["id"] for cp in comparison_products if cp and cp.get("id") is not None}
        ignored_product_ids = [p["id"] for p in active_products if p and p.get("id") is not None and p.get("id") not in comp_ids]

        return comparison_products, ignored_product_ids

    @classmethod
    def route_query(
        cls,
        db: Session,
        user_query: str,
        nlp_data: Dict[str, Any],
        active_products: List[Dict[str, Any]],
        history: Optional[List[Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Central Intelligent Query Router. Dispatches query strictly to the exact required service.
        Resolves explicit target product indices deterministically without guessing or picking the wrong product.
        """
        intent = nlp_data.get("intent", IntentType.UNKNOWN)
        spec_field = nlp_data.get("spec_field")
        category = nlp_data.get("category") or "Laptop"
        is_document_query = nlp_data.get("is_document_query", False)
        
        target_product_index = nlp_data.get("target_product_index")
        selected_indices = nlp_data.get("selected_indices", [])

        # =========================================================================
        # 0. STRICT PRODUCT INDEX RESOLUTION & BOUNDS CHECKING
        # =========================================================================
        primary_product: Optional[Dict[str, Any]] = None

        if target_product_index is not None and active_products:
            # Check if target index is out of bounds (e.g. user asks "product 5" when there are 3 products)
            if target_product_index > len(active_products) or target_product_index <= 0:
                if len(active_products) == 1:
                    err_msg = "I have only 1 product in the current context. Please select product 1."
                else:
                    valid_opts = ", ".join([str(i) for i in range(1, len(active_products))])
                    err_msg = f"I have only {len(active_products)} products in the current context. Please select product {valid_opts}, or {len(active_products)}."

                return {
                    "intent": "ERROR",
                    "type": "error",
                    "response_mode": "FAST",
                    "field": spec_field,
                    "verified": False,
                    "source_type": "error",
                    "answer": err_msg,
                    "message": err_msg,
                    "product": None,
                    "products": [],
                    "recommendations": [],
                    "sources": [],
                    "confidence": "Low",
                    "context_used": "general",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": False,
                    "suggested_followups": [f"Explain product {i}" for i in range(1, min(4, len(active_products) + 1))],
                    "debug_trace": {
                        "raw_query": user_query,
                        "error": "product_index_out_of_bounds",
                        "requested_index": target_product_index,
                        "available_products_count": len(active_products),
                    },
                    "rag_version": "ver2",
                }

            # Map to the exact requested product index
            for p in active_products:
                if p and p.get("context_index") == target_product_index:
                    primary_product = p
                    break
            if not primary_product:
                primary_product = active_products[target_product_index - 1]

        # Priority 2: If query is a follow-up ("what about RAM?") check session memory
        elif not primary_product and session_id:
            mem_session = ConversationMemoryService.get_or_create(session_id)
            if mem_session.active_product:
                primary_product = mem_session.active_product

        # Priority 3: Default to active_products[0] if no target index was specified
        if not primary_product and active_products:
            primary_product = active_products[0]

        # Sync active product in session memory
        if primary_product and session_id:
            mem_session = ConversationMemoryService.get_or_create(session_id)
            mem_session.update_product(primary_product)

        p_name = normalize_product_name(primary_product.get("brand", ""), primary_product.get("name", "")) if primary_product else None

        # Build base debug trace
        debug_trace = {
            "raw_query": user_query,
            "detected_intent": intent,
            "category": category,
            "spec_field": spec_field,
            "target_product_index": target_product_index,
            "resolved_product": p_name,
            "resolved_product_id": primary_product.get("id") if primary_product else None,
            "is_document_query": is_document_query,
            "keywords": nlp_data.get("keywords", []),
        }

        # =========================================================================
        # 1. RAG DOCUMENT QUERIES (PDF, Manual, Datasheet, Cooling, Thermal, Warranty)
        # =========================================================================
        if intent in [IntentType.DOCUMENT_QUERY, IntentType.RAG_DOCUMENT_QUERY] or (is_document_query and not (spec_field and primary_product and spec_field in ["ram", "price", "cpu", "processor", "storage", "gpu"])):
            rag_res = RAGService.query_documents(
                db=db,
                query=nlp_data.get("query_reformulated", user_query),
                category=category,
                product_name=p_name,
                section_focus=spec_field or "overview",
                top_k=4,
            )

            debug_trace["route_selected"] = "RAG_VER2_DOCUMENTS"
            debug_trace["retrieved_sources_count"] = len(rag_res.get("sources", []))

            top_sources = rag_res.get("sources", [])
            conf = "RAG Verified" if top_sources else "Low Confidence"

            return {
                "intent": IntentType.DOCUMENT_QUERY,
                "type": "document",
                "response_mode": "RAG",
                "field": spec_field or "document",
                "verified": bool(top_sources),
                "source_type": "documents",
                "answer": rag_res.get("answer"),
                "message": rag_res.get("answer"),
                "product": primary_product,
                "products": [primary_product] if primary_product else [],
                "recommendations": [],
                "sources": top_sources,
                "confidence": conf,
                "context_used": "documents",
                "show_recommendations": False,
                "show_comparison": False,
                "show_sources": True,
                "suggested_followups": [
                    "What are the full specifications?",
                    "How does the battery perform?",
                    "What is the price?",
                ],
                "debug_trace": debug_trace,
                "rag_version": "ver2",
            }

        # =========================================================================
        # 2. PRODUCT_PRICE, PRODUCT_RAM, PRODUCT_STORAGE, PRODUCT_PROCESSOR, PRODUCT_BATTERY, & SPECS
        # -> STRICT DIRECT MYSQL GROUND TRUTH ON RESOLVED PRODUCT
        # =========================================================================
        spec_intents = [
            IntentType.PRODUCT_PRICE,
            IntentType.PRODUCT_RAM,
            IntentType.PRODUCT_STORAGE,
            IntentType.PRODUCT_PROCESSOR,
            IntentType.PRODUCT_BATTERY,
            IntentType.PRODUCT_SPECIFICATION,
        ]

        if intent != IntentType.PRODUCT_COMPARISON and (
            intent in spec_intents
            or (spec_field and not any(w in user_query.lower() for w in ["best", "recommend", "suggest", "compare", "vs", "between", "better", "which has", "which is", "difference"]))
        ):
            # Derive spec_field from intent if not already populated
            if not spec_field:
                if intent == IntentType.PRODUCT_PRICE:
                    spec_field = "price"
                elif intent == IntentType.PRODUCT_RAM:
                    spec_field = "ram"
                elif intent == IntentType.PRODUCT_STORAGE:
                    spec_field = "storage"
                elif intent == IntentType.PRODUCT_PROCESSOR:
                    spec_field = "processor"
                elif intent == IntentType.PRODUCT_BATTERY:
                    spec_field = "battery"

            # Derive exact resolved intent
            if spec_field == "price":
                resolved_intent = IntentType.PRODUCT_PRICE
            elif spec_field == "ram":
                resolved_intent = IntentType.PRODUCT_RAM
            elif spec_field == "storage":
                resolved_intent = IntentType.PRODUCT_STORAGE
            elif spec_field == "processor":
                resolved_intent = IntentType.PRODUCT_PROCESSOR
            elif spec_field == "battery":
                resolved_intent = IntentType.PRODUCT_BATTERY
            else:
                resolved_intent = IntentType.PRODUCT_SPECIFICATION

            if primary_product and spec_field:
                p_id = primary_product.get("id")
                # --- RESPONSE CACHE CHECK ---
                cached_resp = spec_cache.get(product_id=p_id, spec_field=spec_field) if p_id else None
                if cached_resp:
                    debug_trace["route_selected"] = "CACHE_HIT"
                    debug_trace["cache_stats"] = spec_cache.stats
                    cached_resp["debug_trace"] = debug_trace
                    return cached_resp

                answer = ResponseService.format_specification_response(primary_product, spec_field)
                p_cat = primary_product.get("category", "Product")
                debug_trace["route_selected"] = "MYSQL_DATABASE_SPEC"
                debug_trace["retrieved_sources_count"] = 1
                debug_trace["database_result"] = answer
                debug_trace["final_answer"] = answer
                debug_trace["intent"] = resolved_intent
                debug_trace["field"] = spec_field

                result = {
                    "intent": resolved_intent,
                    "type": "specification",
                    "response_mode": "FAST",
                    "field": spec_field,
                    "verified": True,
                    "source_type": "database",
                    "answer": answer,
                    "message": answer,
                    "product": primary_product,
                    "products": [primary_product],
                    "recommendations": [],
                    "sources": [
                        {
                            "filename": "MySQL Verified Product Catalog",
                            "page_number": None,
                            "section_title": f"{spec_field.upper()} Spec",
                            "snippet": f"Verified {spec_field} specification for {p_name}",
                            "score": 1.0,
                        }
                    ],
                    "confidence": "Database Verified",
                    "context_used": "database",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": True,
                    "suggested_followups": [
                        "What is its price?",
                        "What processor does it use?",
                        f"Is this {p_cat.lower()} good for my use?",
                        "How much storage does it have?",
                    ],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }

                # --- STORE IN CACHE ---
                if p_id:
                    spec_cache.put(product_id=p_id, spec_field=spec_field, response=result)

                return result
            elif primary_product and not spec_field:
                answer = ResponseService.format_product_details_response(primary_product)
                debug_trace["route_selected"] = "MYSQL_DATABASE_PRODUCT_DETAILS"
                debug_trace["database_result"] = answer
                debug_trace["final_answer"] = answer
                debug_trace["intent"] = IntentType.PRODUCT_EXPLAIN

                return {
                    "intent": IntentType.PRODUCT_EXPLAIN,
                    "response_mode": "FAST",
                    "answer": answer,
                    "message": answer,
                    "product": primary_product,
                    "products": [primary_product],
                    "recommendations": [],
                    "sources": [
                        {
                            "filename": "MySQL Verified Product Catalog",
                            "page_number": None,
                            "section_title": "Full Specifications",
                            "snippet": f"Full verified hardware specifications for {p_name}",
                            "score": 1.0,
                        }
                    ],
                    "confidence": "Database Verified",
                    "context_used": "database",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": True,
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }
            else:
                clarification = ResponseService.format_clarification_response(spec_field)
                debug_trace["route_selected"] = "CLARIFICATION"
                debug_trace["final_answer"] = clarification

                return {
                    "intent": resolved_intent,
                    "response_mode": "FAST",
                    "answer": clarification,
                    "message": clarification,
                    "products": [],
                    "recommendations": [],
                    "sources": [],
                    "confidence": "Low Confidence",
                    "context_used": "general",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": False,
                    "suggested_followups": [
                        "Tell me about iPhone 15",
                        "Tell me about ASUS ROG Zephyrus",
                        "Tell me about iPad Air",
                    ],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }

        # =========================================================================
        # 3. PRODUCT_EXPLAIN & ANALYSIS (e.g. "Explain product 1", "Explain product 2", "Explain product 1 and 3")
        # =========================================================================
        if intent in [IntentType.PRODUCT_EXPLAIN, IntentType.PRODUCT_DETAILS] or nlp_data.get("is_explain"):
            target_products: List[Dict[str, Any]] = []

            if selected_indices and active_products:
                for idx in selected_indices:
                    actual_idx = idx - 1 if idx > 0 else len(active_products) + idx
                    if 0 <= actual_idx < len(active_products):
                        p = active_products[actual_idx]
                        if p and p.get("id") not in [tp.get("id") for tp in target_products]:
                            target_products.append(p)
            
            if not target_products:
                if primary_product:
                    target_products = [primary_product]
                elif active_products:
                    target_products = [active_products[0]]

            if target_products:
                is_explain = nlp_data.get("is_explain") or any(w in user_query.lower() for w in ["explain", "analyze", "analysis", "breakdown", "describe"])
                if is_explain or len(target_products) > 1:
                    answer = ResponseService.format_product_analysis_response(target_products)
                    resp_type = "analysis"
                else:
                    answer = ResponseService.format_product_details_response(target_products[0])
                    resp_type = "details"

                debug_trace["route_selected"] = "MYSQL_DATABASE_PRODUCT_ANALYSIS"
                debug_trace["database_result"] = answer
                debug_trace["final_answer"] = answer
                debug_trace["intent"] = IntentType.PRODUCT_EXPLAIN

                p_names = ", ".join([p.get("name", "Product") for p in target_products])
                return {
                    "intent": IntentType.PRODUCT_EXPLAIN,
                    "type": resp_type,
                    "response_mode": "FAST",
                    "field": "analysis",
                    "verified": True,
                    "source_type": "database",
                    "answer": answer,
                    "message": answer,
                    "product": target_products[0],
                    "products": target_products,
                    "recommendations": [],
                    "sources": [
                        {
                            "filename": "MySQL Verified Product Catalog",
                            "page_number": None,
                            "section_title": "Product Analysis",
                            "snippet": f"Verified product specifications for {p_names}",
                            "score": 1.0,
                        }
                    ],
                    "confidence": "Database Verified",
                    "context_used": "database",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": True,
                    "suggested_followups": [
                        "What is its battery backup?",
                        "What is its price?",
                        "Compare with other options",
                    ],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }
            else:
                clarification = "Which product would you like me to analyze? Please select or mention a product."
                return {
                    "intent": IntentType.PRODUCT_DETAILS,
                    "type": "error",
                    "field": "analysis",
                    "verified": False,
                    "source_type": "database",
                    "answer": clarification,
                    "message": clarification,
                    "product": None,
                    "products": [],
                    "recommendations": [],
                    "sources": [],
                    "confidence": "Low Confidence",
                    "context_used": "general",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": False,
                    "suggested_followups": [
                        "Tell me about ASUS ROG",
                        "Tell me about iPad Pro",
                        "Compare ASUS and MSI",
                    ],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }

        # =========================================================================
        # 3.5 PRODUCT_BATTLE & BATTLE VERDICT / REASON (e.g. "Why did ASUS win?", "Why is this better?", "Who won?")
        # =========================================================================
        if intent in [IntentType.PRODUCT_BATTLE, IntentType.BATTLE_VERDICT, IntentType.BATTLE_EXPLANATION, IntentType.BATTLE_REASON]:
            last_battle = None
            if session_id:
                mem_session = ConversationMemoryService.get_or_create(session_id)
                last_battle = mem_session.last_battle_result

            # If user asks why winner won and we have a cached/previous battle result in session
            if (intent in [IntentType.BATTLE_EXPLANATION, IntentType.BATTLE_REASON, IntentType.BATTLE_VERDICT]) and last_battle:
                answer_text = ResponseService.format_battle_verdict_response(last_battle)
                debug_trace["route_selected"] = "AI_BATTLE_MEMORY_VERDICT"
                debug_trace["battle_winner"] = last_battle.get("winner_name") or last_battle.get("winner")

                return {
                    "intent": IntentType.BATTLE_EXPLANATION,
                    "type": "battle",
                    "response_mode": "AI",
                    "field": "battle",
                    "verified": True,
                    "source_type": "battle_engine",
                    "answer": answer_text,
                    "message": answer_text,
                    "products": active_products[:2] if len(active_products) >= 2 else active_products,
                    "compared_products": active_products[:2] if len(active_products) >= 2 else active_products,
                    "ignored_products": [],
                    "battle": last_battle,
                    "recommendations": [],
                    "sources": [
                        {
                            "filename": "AI Battle Arena & Spec Engine",
                            "page_number": None,
                            "section_title": "Multi-Factor Scoring Verdict",
                            "snippet": f"Performance (40%), Price Value (20%), Display (15%), Battery (10%), Rating (15%)",
                            "score": 1.0,
                        }
                    ],
                    "confidence": f"{last_battle.get('confidence', 94)}% Verified",
                    "context_used": "battle_engine",
                    "show_recommendations": False,
                    "show_comparison": True,
                    "show_sources": True,
                    "suggested_followups": [
                        "Explain the winner's performance",
                        "What is the RAM of the winner?",
                        "Compare full specifications",
                    ],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }

            battle_products, ignored_product_ids = cls.detect_comparison_products(
                nlp_data=nlp_data,
                active_products=active_products,
                db=db,
                session_id=session_id
            )

            # If only 1 product resolved (e.g. user only named the winner 'ASUS ROG'), find opponent
            if len(battle_products) == 1:
                p_single = battle_products[0]
                opponent = next((p for p in active_products if p and str(p.get("id")) != str(p_single.get("id"))), None)
                if not opponent and db:
                    # Find a top rival product in same category from MySQL
                    p_cat = p_single.get("category") or category
                    rivals = ProductService.search_by_category(db, p_cat, limit=6)
                    opponent = next((r for r in rivals if str(r.get("id")) != str(p_single.get("id"))), None)
                    if not opponent:
                        all_prods = ProductService.search_by_category(db, "Laptop", limit=5)
                        opponent = next((r for r in all_prods if str(r.get("id")) != str(p_single.get("id"))), None)
                if opponent:
                    battle_products.append(opponent)

            if len(battle_products) >= 2:
                p1, p2 = battle_products[0], battle_products[1]
                battle_res = BattleService.run_battle(
                    db=db,
                    p1=p1,
                    p2=p2,
                    user_id=None
                )

                if session_id:
                    mem_session = ConversationMemoryService.get_or_create(session_id)
                    mem_session.update_comparison_set([p1, p2])
                    mem_session.update_battle_result(battle_res)

                if intent in [IntentType.BATTLE_EXPLANATION, IntentType.BATTLE_REASON]:
                    answer_text = ResponseService.format_battle_verdict_response(battle_res)
                elif intent == IntentType.BATTLE_VERDICT:
                    winner_name = battle_res.get("winner_name")
                    w_score = battle_res.get("winner_score")
                    answer_text = f"🏆 **Final Winner:** **{winner_name}** ({w_score}/100)\n\n" + "\n".join([f"✓ {kr}" for kr in battle_res.get("key_reasons", [])])
                else:
                    answer_text = battle_res.get("markdown", f"AI Battle between {battle_res.get('product_1_name')} and {battle_res.get('product_2_name')}")

                debug_trace["route_selected"] = "AI_BATTLE_ENGINE"
                debug_trace["battle_winner"] = battle_res.get("winner_name")
                debug_trace["battle_scores"] = {
                    "p1": battle_res.get("product_1_score"),
                    "p2": battle_res.get("product_2_score"),
                }

                return {
                    "intent": intent,
                    "type": "battle",
                    "response_mode": "AI",
                    "field": "battle",
                    "verified": True,
                    "source_type": "battle_engine",
                    "answer": answer_text,
                    "message": answer_text,
                    "products": [p1, p2],
                    "compared_products": [p1, p2],
                    "ignored_products": ignored_product_ids,
                    "battle": battle_res,
                    "recommendations": [],
                    "sources": [
                        {
                            "filename": "AI Battle Arena & Spec Engine",
                            "page_number": None,
                            "section_title": "5-Round Multi-Dimensional Scoring",
                            "snippet": f"Performance (40%), Price Value (20%), Display (15%), Battery (10%), Rating (15%)",
                            "score": 1.0,
                        }
                    ],
                    "confidence": f"{battle_res.get('confidence', '94%')} Verified",
                    "context_used": "battle_engine",
                    "show_recommendations": False,
                    "show_comparison": True,
                    "show_sources": True,
                    "suggested_followups": [
                        "Who won the Performance round?",
                        "Why did the winner win?",
                        "What is the battery runtime of each?",
                    ],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }
            else:
                return {
                    "intent": intent,
                    "type": "error",
                    "field": "battle",
                    "verified": False,
                    "source_type": "general",
                    "answer": "Please select or mention 2 products to launch an AI Comparison Battle.",
                    "message": "Please select or mention 2 products to launch an AI Comparison Battle.",
                    "products": battle_products,
                    "recommendations": [],
                    "sources": [],
                    "confidence": "Low Confidence",
                    "context_used": "general",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": False,
                    "suggested_followups": ["Battle ASUS ROG and MSI Titan", "Battle iPhone 15 and Galaxy S24"],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }

        # =========================================================================
        # 4. PRODUCT_COMPARISON (e.g. "compare 1 and 2", "compare 1 and 3", "Compare ASUS and MSI")
        # =========================================================================
        if intent == IntentType.PRODUCT_COMPARISON:
            comparison_products, ignored_product_ids = cls.detect_comparison_products(
                nlp_data=nlp_data,
                active_products=active_products,
                db=db,
                session_id=session_id
            )

            # Validation rule: If user explicitly requested N index items (e.g. 2 items), ensure we compared exactly that
            requested_indices = nlp_data.get("selected_indices", [])
            if requested_indices and len(comparison_products) != len(requested_indices):
                if len(comparison_products) > len(requested_indices):
                    comparison_products = comparison_products[:len(requested_indices)]

            if len(comparison_products) >= 2:
                comparison_result = ComparisonService.compare_products(
                    products=comparison_products,
                    section_focus=spec_field
                )
                answer = comparison_result.get("markdown", "Here is the side-by-side comparison matrix.")

                # Save comparison set to session memory for subsequent follow-up queries
                if session_id:
                    mem_session = ConversationMemoryService.get_or_create(session_id)
                    mem_session.update_comparison_set(comparison_products)

                debug_trace["route_selected"] = "COMPARISON_MATRIX"
                debug_trace["compared_products_count"] = len(comparison_products)
                debug_trace["compared_product_ids"] = [p["id"] for p in comparison_products]
                debug_trace["ignored_product_ids"] = ignored_product_ids

                return {
                    "intent": IntentType.PRODUCT_COMPARISON,
                    "type": "comparison",
                    "response_mode": "FAST",
                    "field": spec_field or "comparison",
                    "verified": True,
                    "source_type": "database",
                    "answer": answer,
                    "message": answer,
                    "products": comparison_products,
                    "compared_products": comparison_products,
                    "ignored_products": ignored_product_ids,
                    "comparison": comparison_result,
                    "recommendations": [],
                    "sources": [
                        {
                            "filename": "MySQL Verified Product Catalog",
                            "page_number": None,
                            "section_title": "Direct Spec Matrix",
                            "snippet": f"Side-by-side comparison for {len(comparison_products)} devices",
                            "score": 1.0,
                        }
                    ],
                    "confidence": "Database Verified",
                    "context_used": "database",
                    "show_recommendations": False,
                    "show_comparison": True,
                    "show_sources": True,
                    "suggested_followups": [
                        "Which one has better battery life?",
                        "Which one is better for gaming?",
                        "Which one has better price-to-performance?",
                    ],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }
            else:
                return {
                    "intent": IntentType.PRODUCT_COMPARISON,
                    "type": "error",
                    "field": "comparison",
                    "verified": False,
                    "source_type": "general",
                    "answer": "Please select or mention at least 2 products to generate a comparison.",
                    "message": "Please select or mention at least 2 products to generate a comparison.",
                    "products": comparison_products,
                    "recommendations": [],
                    "sources": [],
                    "confidence": "Low Confidence",
                    "context_used": "general",
                    "show_recommendations": False,
                    "show_comparison": False,
                    "show_sources": False,
                    "suggested_followups": ["Compare ASUS ROG and MSI Titan", "Compare iPad Pro and Galaxy Tab S9"],
                    "debug_trace": debug_trace,
                    "rag_version": "ver2",
                }

        # =========================================================================
        # 5. PRODUCT_RECOMMENDATION (e.g. "Best gaming laptop under 80000", "Top 5 phones")
        # =========================================================================
        if intent == IntentType.PRODUCT_RECOMMENDATION:
            recommendation_result = RecommendationService.get_recommendations(
                db=db,
                query=user_query,
                category=category,
                extracted_requirements=nlp_data,
                top_k=5,
            )

            rec_items = recommendation_result.get("recommendations", [])
            recommended_products = [item["product"] for item in rec_items if "product" in item]
            answer = recommendation_result.get("summary") or f"Found {len(rec_items)} recommended {category.lower()}s."
            debug_trace["route_selected"] = "RECOMMENDATION_ENGINE"
            debug_trace["recommendations_count"] = len(rec_items)

            return {
                "intent": IntentType.PRODUCT_RECOMMENDATION,
                "type": "recommendation",
                "response_mode": "FAST",
                "field": "recommendation",
                "verified": True,
                "source_type": "database",
                "answer": answer,
                "message": answer,
                "products": recommended_products,
                "recommendations": rec_items,
                "sources": [
                    {
                        "filename": "MySQL Verified Product Catalog",
                        "page_number": None,
                        "section_title": f"{category} Recommendation Model",
                        "snippet": f"Ranked candidates matched against {nlp_data.get('purpose', 'user')} criteria",
                        "score": 0.98,
                    }
                ],
                "confidence": "Database Verified",
                "context_used": "database",
                "show_recommendations": True,
                "show_comparison": False,
                "show_sources": True,
                "suggested_followups": [
                    f"Compare top 2 {category.lower()}s",
                    f"Show me cheaper {category.lower()} options",
                    "Tell me about the #1 ranked device",
                ],
                "debug_trace": debug_trace,
                "rag_version": "ver2",
            }

        # =========================================================================
        # 6. TECHNICAL & BENCHMARK ANALYSIS (Gaming FPS, Battery drain, Camera, Thermals)
        # =========================================================================
        if intent in [
            IntentType.PERFORMANCE_ANALYSIS,
            IntentType.BATTERY_ANALYSIS,
            IntentType.CAMERA_ANALYSIS,
            IntentType.PRICE_ANALYSIS,
        ]:
            analysis_focus = {
                IntentType.PERFORMANCE_ANALYSIS: "performance",
                IntentType.BATTERY_ANALYSIS: "battery",
                IntentType.CAMERA_ANALYSIS: "camera",
                IntentType.PRICE_ANALYSIS: "price",
            }.get(intent, "general")

            analysis_result = TechnicalAnalysisService.analyze_query(
                query=user_query,
                intent=intent,
                product=primary_product or {}
            )

            debug_trace["route_selected"] = "TECHNICAL_ANALYSIS_ENGINE"

            return {
                "intent": intent,
                "type": "analysis",
                "response_mode": "AI",
                "field": analysis_focus,
                "verified": True,
                "source_type": "database",
                "answer": analysis_result.get("answer"),
                "message": analysis_result.get("answer"),
                "product": primary_product,
                "products": [primary_product] if primary_product else [],
                "recommendations": [],
                "sources": [
                    {
                        "filename": "Technical Benchmark Engine",
                        "page_number": None,
                        "section_title": f"{analysis_focus.title()} Benchmark",
                        "snippet": f"Calculated hardware efficiency for {p_name}",
                        "score": 0.95,
                    }
                ],
                "confidence": "Database Verified",
                "context_used": "database",
                "show_recommendations": False,
                "show_comparison": False,
                "show_sources": True,
                "suggested_followups": [
                    "What about gaming performance?",
                    "What about battery life?",
                    "What is its price?",
                ],
                "debug_trace": debug_trace,
                "rag_version": "ver2",
            }

        # =========================================================================
        # 7. GENERAL / UNKNOWN FALLBACK
        # =========================================================================
        greeting_text = (
            f"Hello! I am your AI Product Assistant for **Laptops**, **Smartphones**, and **Tablets**.\n\n"
            f"You can ask me to:\n"
            f"• Get verified specifications (`RAM of product 3`, `What is its price?`)\n"
            f"• Compare specific models (`compare product 1 and 3`)\n"
            f"• Find top recommendations (`best gaming laptop under 80000`)\n"
            f"• Analyze product manuals and datasheets in RAG Docs."
        )

        return {
            "intent": IntentType.GENERAL_PRODUCT_QUERY,
            "type": "general",
            "response_mode": "FAST",
            "field": "general",
            "verified": False,
            "source_type": "general",
            "answer": greeting_text,
            "message": greeting_text,
            "products": [primary_product] if primary_product else [],
            "recommendations": [],
            "sources": [],
            "confidence": "Medium Confidence",
            "context_used": "general",
            "show_recommendations": False,
            "show_comparison": False,
            "show_sources": False,
            "suggested_followups": [
                "Find best gaming laptop under ₹80,000",
                "Compare product 1 and 2",
                "What is the price of product 3?",
            ],
            "debug_trace": debug_trace,
            "rag_version": "ver2",
        }
