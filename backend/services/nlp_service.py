"""
Category-Aware Natural Language Processing (NLP) Service
Extracts Intents, Entities, Category Filters, Specs, and Priority Weights
Across Laptops, Phones / Smartphones, and Tablets.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("backend.nlp")


class IntentType:
    SPEC_QUERY = "SPEC_QUERY"
    PRODUCT_PRICE = "PRODUCT_PRICE"
    PRODUCT_RAM = "PRODUCT_RAM"
    PRODUCT_STORAGE = "PRODUCT_STORAGE"
    PRODUCT_PROCESSOR = "PRODUCT_PROCESSOR"
    PRODUCT_BATTERY = "PRODUCT_BATTERY"
    PRODUCT_SPECIFICATION = "PRODUCT_SPECIFICATION"
    PRODUCT_DETAILS = "PRODUCT_DETAILS"
    PRODUCT_EXPLAIN = "PRODUCT_EXPLAIN"
    PRODUCT_EXPLANATION = "PRODUCT_EXPLAIN"
    PRODUCT_RECOMMENDATION = "PRODUCT_RECOMMENDATION"
    PRODUCT_RECOMMEND = "PRODUCT_RECOMMENDATION"
    PRODUCT_COMPARISON = "PRODUCT_COMPARISON"
    PRODUCT_COMPARE = "PRODUCT_COMPARISON"
    COMPARISON_QUERY = "PRODUCT_COMPARISON"
    PRODUCT_BATTLE = "PRODUCT_BATTLE"
    BATTLE_VERDICT = "BATTLE_VERDICT"
    BATTLE_EXPLANATION = "BATTLE_EXPLANATION"
    BATTLE_REASON = "BATTLE_EXPLANATION"
    PERFORMANCE_ANALYSIS = "PERFORMANCE_ANALYSIS"
    PRICE_ANALYSIS = "PRICE_ANALYSIS"
    BATTERY_ANALYSIS = "BATTERY_ANALYSIS"
    CAMERA_ANALYSIS = "CAMERA_ANALYSIS"
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    RAG_DOCUMENT_QUERY = "DOCUMENT_QUERY"
    TECHNICAL_ANALYSIS = "TECHNICAL_ANALYSIS"
    FOLLOW_UP_QUERY = "FOLLOW_UP_QUERY"
    FOLLOW_UP = "FOLLOW_UP_QUERY"
    GENERAL_PRODUCT_QUERY = "GENERAL_PRODUCT_QUERY"
    UNKNOWN = "UNKNOWN"


# Mapping query phrases to specific specification fields
SPEC_FIELD_MAP = {
    "ram": "ram",
    "memory": "ram",
    "price": "price",
    "cost": "price",
    "mrp": "price",
    "rate": "price",
    "processor": "processor",
    "cpu": "processor",
    "chipset": "processor",
    "chip": "processor",
    "gpu": "gpu",
    "graphics": "gpu",
    "graphics card": "gpu",
    "vram": "gpu",
    "storage": "storage",
    "ssd": "storage",
    "hdd": "storage",
    "hard disk": "storage",
    "rom": "storage",
    "internal memory": "storage",
    "battery": "battery",
    "battery life": "battery",
    "charging": "battery",
    "fast charging": "battery",
    "runtime": "battery",
    "display": "display",
    "screen": "display",
    "screen size": "display",
    "panel": "display",
    "resolution": "display",
    "refresh rate": "display",
    "camera": "camera",
    "cameras": "camera",
    "rear camera": "camera",
    "front camera": "camera",
    "selfie camera": "camera",
    "megapixels": "camera",
    "mp": "camera",
    "stylus": "stylus",
    "pen": "stylus",
    "apple pencil": "stylus",
    "s-pen": "stylus",
    "5g": "5g",
    "cellular": "5g",
    "network": "5g",
    "sim": "5g",
    "os": "os",
    "operating system": "os",
    "android": "os",
    "windows": "os",
    "ios": "os",
    "ipados": "os",
    "rating": "rating",
    "score": "rating",
    "reviews": "rating",
    "weight": "weight",
}

# Follow-up indicators
_FOLLOWUP_PATTERNS = [
    r"^what about\b", r"^how about\b", r"^and the\b", r"^also\b",
    r"^tell me more\b", r"^more (info|details|about)\b",
    r"\b(its|it'?s|this one|that one|the same|both of them|which one|which)\b",
    r"^can you\b", r"^what (is|are) (its|the|their)\b",
    r"^how (is|are) (it|its|the)\b",
    r"^is it (good|better|worth|suitable)\b",
]

KNOWN_BRANDS = [
    "asus", "hp", "lenovo", "dell", "apple", "acer", "msi", "samsung", "micromax", "lg", "razer",
    "xiaomi", "redmi", "vivo", "oppo", "oneplus", "realme", "intex", "lava", "karbonn", "iball",
    "swipe", "motorola", "nokia", "sony", "google", "honor", "huawei", "poco", "iqoo"
]


class NLPService:
    @staticmethod
    def detect_followup(query: str, history: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Detect if the query is a follow-up referring to previous context."""
        q = query.lower().strip()
        words = q.split()

        if len(words) <= 6 and any(w in ["it", "its", "this", "that", "them", "they", "which", "both"] for w in words):
            return True

        for pattern in _FOLLOWUP_PATTERNS:
            if re.search(pattern, q):
                return True

        return False

    @staticmethod
    def extract_product_names(query: str) -> List[str]:
        """Extract explicit product model identifiers across Laptops, Phones, and Tablets."""
        q = query.strip()
        found: List[str] = []

        # 1. Phone & Tablet models (e.g., iPhone 15, Galaxy S24, Redmi Note 5, iPad Air, Galaxy Tab S9)
        gadget_patterns = [
            r"\b(iphone\s+(?:1[1-6]|se|[xX][rRsS]?|\d+)(?:\s+(?:pro\s+max|pro|plus|mini))?)\b",
            r"\b(ipad(?:\s+(?:air|pro|mini|\d+(?:th)?\s*gen))?)\b",
            r"\b(galaxy\s+(?:tab\s+[as]\d+|s2[0-5]|s1[0-9]|z\s+fold|z\s+flip|a\d+|m\d+|note\s*\d+)(?:\s+(?:ultra|plus|fe|\+))?)\b",
            r"\b(redmi(?:\s+note)?\s+\w+(?:\s+pro)?)\b",
            r"\b(oneplus\s+\w+(?:\s+pro|\s+r|\s+nord)?)\b",
            r"\b(pixel\s+[6-9](?:\s+pro|\s+a)?)\b",
            r"\b(tab\s+[2-7]\s*(?:a\d+|lte)?)\b",
        ]
        for gp in gadget_patterns:
            for m in re.finditer(gp, q, re.IGNORECASE):
                name = m.group(1).strip()
                if len(name) >= 3 and name.lower() not in [f.lower() for f in found]:
                    found.append(name)

        # 2. Laptop brand + model patterns
        laptop_brand_pattern = (
            r"\b((?:MSI|ASUS|Acer|HP|Dell|Lenovo|Apple|Samsung|Micromax|Razer)\s+"
            r"(?:[A-Za-z0-9\-\_]+(?:\s+[A-Za-z0-9\-\_]+){0,3}))\b"
        )
        for m in re.finditer(laptop_brand_pattern, q, re.IGNORECASE):
            name = m.group(1).strip()
            if len(name) >= 4 and not any(name.lower() == b.lower() for b in KNOWN_BRANDS):
                if name.lower() not in [f.lower() for f in found]:
                    found.append(name)

        # 3. Standalone laptop series / model tokens (e.g. GL62M, Inspiron 5559, MacBook Air M2)
        standalone_models = re.findall(
            r"\b([A-Z]{2,}\d{2,}[A-Za-z0-9\-]*|\b(?:Inspiron|Pavilion|IdeaPad|ThinkPad|Vivobook|Zenbook|Predator|Legion|TUF|ROG|MacBook|MacBook\s+Air|MacBook\s+Pro)\s+\w+)\b",
            q,
            re.IGNORECASE
        )
        for sm in standalone_models:
            if sm and sm.lower() not in [f.lower() for f in found]:
                found.append(sm.strip())

        return found

    @staticmethod
    def extract_comparison_selection(query: str) -> Dict[str, Any]:
        """
        Extract explicit product selection references from user queries:
        - "price of product 3", "What is its price of product 3?" -> selected_indices=[3], target_product_index=3
        - "RAM of product 1" -> selected_indices=[1], target_product_index=1
        - "explain product 2" -> selected_indices=[2], target_product_index=2
        - "compare 1 and 2", "1 vs 2", "between 1 and 2" -> selected_indices=[1, 2]
        - "compare 1 and 3", "explain product 1 and 3" -> selected_indices=[1, 3]
        - "which is better between first two?", "first two" -> selected_indices=[1, 2]
        - "first and third", "1st and 3rd" -> selected_indices=[1, 3]
        - "compare all", "all of them", "compare all 3" -> is_compare_all=True
        """
        q = query.lower().strip()
        selected_indices: List[int] = []
        is_compare_all = False

        # 1. "compare all" / "all of them" / "compare all 3"
        if any(p in q for p in ["compare all", "compare them all", "all of them", "all 3", "all three", "compare every", "compare all products"]):
            is_compare_all = True

        # 2. Ordinal multi-item text phrases
        elif any(p in q for p in ["first two", "first 2", "first and second", "1st and 2nd", "1st & 2nd"]):
            selected_indices = [1, 2]
        elif any(p in q for p in ["second and third", "2nd and 3rd", "2nd & 3rd"]):
            selected_indices = [2, 3]
        elif any(p in q for p in ["first and third", "1st and 3rd", "1st & 3rd"]):
            selected_indices = [1, 3]
        elif any(p in q for p in ["last two", "last 2"]):
            selected_indices = [-2, -1]

        # 3. Explicit numeric index patterns
        if not selected_indices and not is_compare_all:
            # Multi items (3 items): "1, 2 and 3", "product 1, 2 and 3"
            m3 = re.search(r"\b(?:product|option|item|#)?\s*(\d+)\s*(?:,|and|&|\+)\s*(?:product|option|item|#)?\s*(\d+)\s*(?:and|&|,|\+)\s*(?:product|option|item|#)?\s*(\d+)\b", q)
            if m3:
                idx1 = int(m3.group(1))
                idx2 = int(m3.group(2))
                idx3 = int(m3.group(3))
                if 1 <= idx1 <= 1000 and 1 <= idx2 <= 1000 and 1 <= idx3 <= 1000:
                    selected_indices = [idx1, idx2, idx3]
            else:
                # Multi items (2 items): "1 and 2", "1 vs 2", "product 1 and 3", "1 and 3", "product 1 and product 3"
                m2 = re.search(r"\b(?:product|option|item|#)?\s*(\d+)\s*(?:and|&|vs\.?|versus|,|\+)\s*(?:product|option|item|#)?\s*(\d+)\b", q)
                if m2:
                    idx1 = int(m2.group(1))
                    idx2 = int(m2.group(2))
                    if 1 <= idx1 <= 1000 and 1 <= idx2 <= 1000:
                        selected_indices = [idx1, idx2]
                else:
                    # Single items:
                    # e.g., "price of product 3", "What is its price of product 3?", "RAM of product 1", "product 3 price", "3 product", "product 3", "explain 2", "#3"
                    single_patterns = [
                        r"\b(?:price|ram|storage|processor|cpu|gpu|battery|camera|display|details|specs?|analysis|overview)\s+(?:of|for|in)\s+(?:the\s+)?(?:product|item|option|#)?\s*(\d+)\b",
                        r"\b(?:what is (?:its|the)|how much is (?:the|its))\s*(?:price|ram|storage|processor|cpu|gpu|battery|camera|display)?\s*(?:of|for|in)?\s*(?:the\s+)?(?:product|item|option|#)?\s*(\d+)\b",
                        r"\b(?:product|item|option|choice|#)\s*(\d+)\b",
                        r"\b(\d+)(?:st|nd|rd|th)?\s*(?:product|item|option|choice)\b",
                        r"\b(?:explain|analyze|tell me about|details of|about)\s+(?:product\s+|item\s+|option\s+|#)?(\d+)\b",
                        r"\b(?:of|for)\s+(?:product\s+|item\s+|#)?(\d+)\b",
                    ]
                    for sp in single_patterns:
                        m1 = re.search(sp, q)
                        if m1:
                            num_str = m1.group(1)
                            if num_str and 1 <= int(num_str) <= 1000:
                                selected_indices = [int(num_str)]
                                break

                    # Ordinal single items ("first product", "second product", "third product")
                    if not selected_indices:
                        if re.search(r"\b(?:first|1st)\s*(?:product|item|option|choice)?\b", q) and any(w in q for w in ["product", "item", "option", "choice", "explain", "price", "ram", "cpu", "processor"]):
                            selected_indices = [1]
                        elif re.search(r"\b(?:second|2nd)\s*(?:product|item|option|choice)?\b", q) and any(w in q for w in ["product", "item", "option", "choice", "explain", "price", "ram", "cpu", "processor"]):
                            selected_indices = [2]
                        elif re.search(r"\b(?:third|3rd)\s*(?:product|item|option|choice)?\b", q) and any(w in q for w in ["product", "item", "option", "choice", "explain", "price", "ram", "cpu", "processor"]):
                            selected_indices = [3]
                        elif re.search(r"\b(?:fourth|4th)\s*(?:product|item|option|choice)?\b", q) and any(w in q for w in ["product", "item", "option", "choice", "explain", "price", "ram", "cpu", "processor"]):
                            selected_indices = [4]
                        elif re.search(r"\b(?:fifth|5th)\s*(?:product|item|option|choice)?\b", q) and any(w in q for w in ["product", "item", "option", "choice", "explain", "price", "ram", "cpu", "processor"]):
                            selected_indices = [5]

        target_product_index = selected_indices[0] if len(selected_indices) == 1 else None
        selected_products = [{"context_index": idx} for idx in selected_indices if idx > 0]

        has_explicit_comp_word = any(
            w in q for w in [
                "compare", " vs ", "versus", "difference between", "difference",
                "which is better", "which one is better", "head to head",
                "which has better", "which has higher", "which has more", "which has faster",
                "which is faster", "which is cheaper", "which is more affordable",
                "which has the best", "which one has better", "better between"
            ]
        )

        is_explain = any(w in q for w in ["explain", "analyze", "analysis", "breakdown", "overview", "details", "tell me about", "describe"])

        # It is comparison only if explicit comparison word or (2+ items and NOT pure explain without compare)
        is_comparison = is_compare_all or has_explicit_comp_word or (len(selected_indices) >= 2 and not is_explain)

        return {
            "is_comparison": is_comparison,
            "is_compare_all": is_compare_all,
            "is_explain": is_explain,
            "target_product_index": target_product_index,
            "selected_indices": selected_indices,
            "selected_products": selected_products,
        }

    @classmethod
    def parse_query_heuristics(
        cls,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deterministic, category-aware NLP extraction of intent, entities, category, and budget.
        """
        q = query.lower().strip()
        clean_q = re.sub(r"[^\w\s\-\₹\$\.]", " ", q).strip()
        words = clean_q.split()

        # Comparison selection extraction
        comp_sel = cls.extract_comparison_selection(query)

        # 1. Spec Field Detection
        detected_spec_field = None
        # Check multi-word spec phrases first
        for phrase in ["battery life", "battery backup", "fast charging", "screen size", "refresh rate", "graphics card", "internal memory", "operating system", "rear camera", "front camera", "selfie camera"]:
            if phrase in clean_q:
                detected_spec_field = SPEC_FIELD_MAP.get(phrase)
                break

        if not detected_spec_field:
            for w in words:
                if w in SPEC_FIELD_MAP:
                    detected_spec_field = SPEC_FIELD_MAP[w]
                    break

        # 2. Category Detection
        # Strict category detection for Laptop vs Phone vs Tablet
        category: Optional[str] = None

        is_tablet = any(w in q for w in [
            "tablet", "tablets", "ipad", "ipads", "galaxy tab", "tab s", "surface pro", "slate", "ipad air", "ipad pro", "ipad mini"
        ])
        is_phone = any(w in q for w in [
            "phone", "phones", "smartphone", "smartphones", "mobile", "mobiles", "iphone", "iphones", "android phone",
            "galaxy s2", "galaxy s1", "galaxy z", "redmi", "oneplus", "pixel 7", "pixel 8", "vivo", "oppo", "realme"
        ])
        is_laptop = any(w in q for w in [
            "laptop", "laptops", "notebook", "notebooks", "macbook", "ultrabook", "thinkpad", "ideapad",
            "zenbook", "vivobook", "predator", "legion", "rog", "tuf", "gaming laptop"
        ])

        # Cross-category catch-all (e.g. "all products under 50k", "gadgets under 30000")
        is_cross_category = any(w in q for w in ["gadget", "gadgets", "device", "devices", "electronics", "all products"])

        if is_cross_category:
            category = None
        elif is_tablet and not is_phone and not is_laptop:
            category = "Tablet"
        elif is_phone and not is_laptop and not is_tablet:
            category = "Phone"
        elif is_laptop and not is_phone and not is_tablet:
            category = "Laptop"
        elif conversation_context and conversation_context.get("category"):
            category = conversation_context.get("category")
        else:
            # Contextual fallback: check product names in query
            extracted_names = cls.extract_product_names(query)
            if any("ipad" in n.lower() or "tab" in n.lower() for n in extracted_names):
                category = "Tablet"
            elif any("iphone" in n.lower() or "galaxy s" in n.lower() or "redmi" in n.lower() for n in extracted_names):
                category = "Phone"
            elif any("macbook" in n.lower() or "gl62" in n.lower() or "inspiron" in n.lower() for n in extracted_names):
                category = "Laptop"
            else:
                # Default to Laptop for generic queries, or None if ambiguous
                category = "Laptop"

        # 3. Intent Classification
        intent = IntentType.UNKNOWN

        # A0. AI Battle Reason & Explanation Queries (e.g. "Why did ASUS win?", "Why did ASUS ROG Zephyrus win the battle?", "Why is this better?")
        is_battle_reason_query = (
            any(p in q for p in [
                "why did", "why wins", "why won", "why does", "explain battle", "reason for winning",
                "why is it better", "why is this better", "why winner", "reason why", "how did",
                "why beat", "why defeated", "why victory", "why win", "why is", "what made"
            ]) and any(w in q for w in ["win", "won", "winner", "better", "battle", "versus", "vs", "beat", "defeat", "score", "champion"])
        ) or any(p in q for p in [
            "why did asus win", "why did product 1 win", "why is product 1 better", "why is asus better",
            "why did the winner win", "why won the battle", "why win the battle", "why did"
        ]) or ("why" in words and any(w in words for w in ["win", "won", "winner", "better", "battle", "beat"]))

        is_verdict_query = any(p in q for p in [
            "who wins", "who won", "which is the winner", "who is the winner", "which one wins",
            "who is better overall", "battle verdict", "winner of the battle", "who is victorious"
        ])
        is_battle_query = any(w in q for w in ["battle", "fight", "clash", "ai battle", "versus battle", "product battle"])

        if is_battle_reason_query:
            intent = IntentType.BATTLE_EXPLANATION

        elif is_verdict_query:
            intent = IntentType.BATTLE_VERDICT

        elif is_battle_query and not is_battle_reason_query:
            intent = IntentType.PRODUCT_BATTLE

        # A. RAG Document queries (explicitly asking about datasheet, manual, PDF, cooling/thermal)
        elif any(w in q for w in ["pdf", "datasheet", "document", "manual", "page", "file say", "according to the doc", "uploaded", "cooling", "thermal"]):
            intent = IntentType.RAG_DOCUMENT_QUERY

        # B. Product Comparison queries
        elif comp_sel["is_comparison"] and not is_battle_reason_query:
            intent = IntentType.PRODUCT_COMPARISON

        # D. Product Details / Explanation queries (e.g. "explain product 1", "Tell me about ASUS", "Explain ASUS", "describe product 2")
        elif any(w in q for w in ["explain", "analyze", "analysis", "breakdown", "tell me about", "overview of", "describe", "product explain", "details of", "about this"]) and not is_battle_reason_query:
            intent = IntentType.PRODUCT_EXPLAIN

        # C. Single Spec / Attribute Queries (Strict direct database lookup)
        elif detected_spec_field == "price" and not any(w in q for w in ["best", "recommend", "suggest", "compare", "vs", "better", "between", "why", "explain"]):
            intent = IntentType.PRODUCT_PRICE

        elif detected_spec_field == "ram" and not any(w in q for w in ["best", "recommend", "suggest", "compare", "vs", "better", "between", "why", "explain"]):
            intent = IntentType.PRODUCT_RAM

        elif detected_spec_field == "storage" and not any(w in q for w in ["best", "recommend", "suggest", "compare", "vs", "better", "between", "why", "explain"]):
            intent = IntentType.PRODUCT_STORAGE

        elif detected_spec_field == "processor" and not any(w in q for w in ["best", "recommend", "suggest", "compare", "vs", "better", "between", "why", "explain"]):
            intent = IntentType.PRODUCT_PROCESSOR

        elif detected_spec_field == "battery" and not any(w in q for w in ["best", "recommend", "suggest", "compare", "vs", "better", "between", "why", "explain"]):
            intent = IntentType.PRODUCT_BATTERY

        elif detected_spec_field is not None and not any(w in q for w in ["best", "recommend", "suggest", "compare", "vs", "better", "between", "why", "explain"]):
            intent = IntentType.PRODUCT_SPECIFICATION

        # E. Recommendation queries (e.g. "best gaming laptop", "recommend 5G phone")
        elif any(w in q for w in ["best", "recommend", "recommendation", "suggest", "which should i buy", "which one should i buy", "top 5", "top 10", "suggest me"]):
            intent = IntentType.PRODUCT_RECOMMENDATION

        # F. Performance / Gaming Benchmarks
        elif any(w in q for w in ["gaming", "game", "fps", "frame rate", "cyberpunk", "gta", "benchmark", "heavy load"]):
            intent = IntentType.PERFORMANCE_ANALYSIS

        # G. Camera Analysis (Phones & Tablets)
        elif any(w in q for w in ["camera quality", "best camera", "selfie camera", "night mode camera", "camera performance"]):
            intent = IntentType.CAMERA_ANALYSIS

        # H. Battery Analysis under load
        elif any(w in q for w in ["battery under load", "battery drain", "endurance test", "screen on time under heavy load"]):
            intent = IntentType.BATTERY_ANALYSIS

        # I. Price Analysis
        elif any(w in q for w in ["price-to-performance", "value for money", "best value", "vfm", "is it worth"]):
            intent = IntentType.PRICE_ANALYSIS

        # J. General Recommendation fallback for budget phrases
        elif any(w in q for w in ["under", "below", "budget"]):
            intent = IntentType.PRODUCT_RECOMMENDATION

        # J. General Greeting
        elif len(words) <= 2 and any(w in q for w in ["hi", "hello", "hey", "thanks", "thank you", "help", "who are you"]):
            intent = IntentType.GENERAL_PRODUCT_QUERY

        # K. Follow-up
        elif cls.detect_followup(q):
            intent = IntentType.FOLLOW_UP

        # 4. Budget / Price Detection
        max_price = None
        min_price = None
        NON_PRICE_NUMBERS = {
            "2077", "1080", "1070", "1060", "1050", "2060", "2070", "2080", "3050", "3060", "3070", "3080",
            "4050", "4060", "4070", "4080", "4090", "2023", "2024", "2025", "2026", "5", "6", "7", "8", "9",
            "10", "11", "12", "13", "14", "15", "16", "24"
        }

        range_match = re.search(r"between\s+(?:₹|rs\.?|inr|\$)?\s*(\d+(?:,\d+)?|\d+k)\s*(?:and|to|-)\s*(?:₹|rs\.?|inr|\$)?\s*(\d+(?:,\d+)?|\d+k)", q)
        if range_match:
            min_str, max_str = range_match.groups()
            min_price = float(min_str.replace("k", "000").replace(",", ""))
            max_price = float(max_str.replace("k", "000").replace(",", ""))
        else:
            price_match = re.search(r"(?:under|below|less than|within|budget of|budget|max(?:imum)? of|around|upto|up to)\s*(?:₹|rs\.?|inr|\$)?\s*(\d{1,3}(?:,\d{3})+|\d+k|\d{4,7})", q)
            if not price_match:
                price_match = re.search(r"(?:₹|rs\.?|inr|\$)\s*(\d{1,3}(?:,\d{3})+|\d+k|\d{4,7})", q)
            if not price_match:
                price_match = re.search(r"\b(\d{2,3})k\b", q)

            if price_match:
                raw_str = price_match.group(1) if price_match.lastindex else price_match.group(0)
                raw_num = raw_str.replace(",", "").replace("k", "000")
                if raw_str not in NON_PRICE_NUMBERS and raw_num not in NON_PRICE_NUMBERS:
                    try:
                        parsed_val = float(raw_num)
                        if parsed_val >= 3000:
                            max_price = parsed_val
                    except ValueError:
                        pass

        # 5. RAM Detection
        min_ram = None
        ram_match = re.search(r"(\d+)\s*(?:gb|g)\s*(?:ram|memory)?", q)
        if ram_match:
            try:
                r_val = float(ram_match.group(1))
                if r_val in [2, 3, 4, 6, 8, 12, 16, 24, 32, 64]:
                    min_ram = r_val
            except ValueError:
                pass

        # 6. Purpose & Category-Specific Priorities
        purpose = "balanced"
        features = []
        priorities = {"performance": 0.35, "price": 0.35, "battery": 0.15, "display": 0.15}

        if category == "Phone":
            priorities = {"camera": 0.25, "performance": 0.25, "battery": 0.20, "price": 0.15, "display": 0.15}
            if any(w in q for w in ["camera", "photo", "selfie", "video recording"]):
                purpose = "camera"
                priorities = {"camera": 0.45, "performance": 0.20, "display": 0.15, "battery": 0.10, "price": 0.10}
            elif any(w in q for w in ["battery", "all day", "charging"]):
                purpose = "battery"
                priorities = {"battery": 0.45, "price": 0.25, "performance": 0.15, "camera": 0.15}
        elif category == "Tablet":
            priorities = {"display": 0.25, "battery": 0.20, "performance": 0.20, "stylus": 0.15, "price": 0.10, "ram": 0.10}
            if any(w in q for w in ["drawing", "student", "note taking", "stylus", "pen"]):
                purpose = "creativity"
                priorities = {"stylus": 0.35, "display": 0.30, "battery": 0.15, "performance": 0.10, "price": 0.10}
            elif any(w in q for w in ["movies", "media", "reading", "entertainment"]):
                purpose = "entertainment"
                priorities = {"display": 0.40, "battery": 0.30, "price": 0.15, "performance": 0.15}
        else:
            if any(w in q for w in ["gaming", "game", "esports", "fps", "cyberpunk", "gta", "rtx", "gtx"]):
                purpose = "gaming"
                features.append("gaming")
                priorities = {"performance": 0.55, "price": 0.25, "display": 0.10, "battery": 0.10}
            elif any(w in q for w in ["editing", "video", "render", "creator", "photoshop", "premiere"]):
                purpose = "editing"
                features.append("display")
                priorities = {"performance": 0.40, "display": 0.35, "price": 0.15, "battery": 0.10}
            elif any(w in q for w in ["coding", "programming", "developer", "software", "development"]):
                purpose = "coding"
                features.append("multitasking")
                priorities = {"performance": 0.45, "price": 0.25, "battery": 0.20, "display": 0.10}

        # 7. Brand Detection
        brand = None
        for b in KNOWN_BRANDS:
            if re.search(rf"\b{b}\b", q):
                brand = b.capitalize() if b not in ["msi", "hp", "asus"] else b.upper()
                break

        product_names = cls.extract_product_names(query)

        # 8. Document / Technical Query Specificity
        is_document_query = any(w in q for w in [
            "pdf", "datasheet", "document", "manual", "page", "file say", "according to the doc",
            "uploaded", "cooling", "thermal", "heat pipe", "fan noise", "warranty terms", "service policy"
        ])

        # 9. Query Keywords Extraction (for hybrid search & reranker)
        stop_words = {"the", "a", "an", "is", "of", "and", "or", "in", "for", "with", "on", "what", "how", "tell", "me", "about", "this", "that", "it", "its", "does", "say"}
        keywords = [w for w in words if w not in stop_words and len(w) >= 2]

        # 10. Query Reformulation
        # If product name exists, generate an expanded search query for RAG / retrieval
        p_name_str = product_names[0] if product_names else (conversation_context.get("active_product_name") if conversation_context else "")
        if detected_spec_field:
            if detected_spec_field in ["battery", "runtime"]:
                query_reformulated = f"Battery life capacity runtime power endurance of {p_name_str}".strip()
            elif detected_spec_field in ["cooling", "thermal"]:
                query_reformulated = f"Cooling architecture thermal management heat pipes fan design of {p_name_str}".strip()
            elif detected_spec_field in ["ram", "memory"]:
                query_reformulated = f"RAM memory capacity type upgradability of {p_name_str}".strip()
            elif detected_spec_field in ["storage", "ssd"]:
                query_reformulated = f"Storage SSD HDD disk drive capacity of {p_name_str}".strip()
            elif detected_spec_field in ["camera"]:
                query_reformulated = f"Camera megapixels sensor aperture selfie rear camera of {p_name_str}".strip()
            else:
                query_reformulated = f"{detected_spec_field} specifications and details of {p_name_str}".strip()
        else:
            query_reformulated = f"{query} {p_name_str}".strip()

        constraints = {
            "max_price": max_price,
            "min_price": min_price,
            "min_ram": min_ram,
            "brand": brand,
            "category": category,
            "has_5g": "5g" in q or "cellular" in q,
            "has_stylus": "stylus" in q or "pen" in q,
        }

        return {
            "intent": intent,
            "spec_field": detected_spec_field,
            "required_information": detected_spec_field or ("document_content" if is_document_query else "overview"),
            "category": category,
            "max_price": max_price,
            "min_price": min_price,
            "min_ram": min_ram,
            "brand": brand,
            "purpose": purpose,
            "features": features,
            "priorities": priorities,
            "product_names": product_names,
            "is_followup": cls.detect_followup(query),
            "is_document_query": is_document_query,
            "is_explain": comp_sel.get("is_explain", False) or intent in [IntentType.PRODUCT_EXPLAIN, IntentType.PRODUCT_EXPLANATION, IntentType.PRODUCT_DETAILS],
            "is_battle": is_battle_reason_query or is_verdict_query or is_battle_query or intent in [IntentType.BATTLE_EXPLANATION, IntentType.BATTLE_VERDICT, IntentType.PRODUCT_BATTLE, IntentType.BATTLE_REASON],
            "is_compare": comp_sel.get("is_comparison", False) or intent in [IntentType.PRODUCT_COMPARISON, IntentType.COMPARISON_QUERY],
            "is_comparison": comp_sel["is_comparison"],
            "is_compare_all": comp_sel["is_compare_all"],
            "target_product_index": comp_sel.get("target_product_index"),
            "selected_indices": comp_sel["selected_indices"],
            "selected_products": comp_sel["selected_products"],
            "keywords": keywords,
            "constraints": constraints,
            "query_reformulated": query_reformulated,
            "raw_query": query,
        }

    @classmethod
    def extract_requirements(cls, query: str) -> Dict[str, Any]:
        """Alias for parse_query_heuristics for backward compatibility."""
        return cls.parse_query_heuristics(query)
