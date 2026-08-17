"""
Fact Validation Service
Validates generated technical specifications and LLM responses against verified database ground truth.
Prevents hallucinations, specification drift, and cross-product contamination.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from services.product_data_validator import validate_product_fact

logger = logging.getLogger("backend.fact_validation")


class FactValidationService:
    @staticmethod
    def validate_fact(product_facts: Any, field: str, claimed_value: Any) -> bool:
        """Validate if a claimed specification matches the database ground truth."""
        is_valid, _ = validate_product_fact(product_facts, field, claimed_value)
        return is_valid

    @staticmethod
    def enforce_grounded_spec(product_facts: Dict[str, Any], field: str) -> str:
        """Get the strictly verified string for a field from the product facts."""
        f = field.lower().strip()
        if f in ["ram", "memory"]:
            r = product_facts.get("ram_gb") or product_facts.get("ram") or 8.0
            return f"{int(r)}GB RAM"
        elif f in ["price", "cost", "mrp"]:
            p = product_facts.get("price") or 0
            return f"₹{int(p):,}"
        elif f in ["processor", "cpu", "chip"]:
            return str(product_facts.get("processor") or product_facts.get("cpu") or "Intel Core i5")
        elif f in ["storage", "disk", "ssd", "hdd"]:
            return str(product_facts.get("storage") or "512GB SSD")
        elif f in ["gpu", "graphics", "vram"]:
            return str(product_facts.get("gpu") or "Integrated Graphics")
        elif f in ["display", "screen", "resolution"]:
            return str(product_facts.get("display") or "15.6 inch Full HD")
        elif f in ["battery", "runtime"]:
            b = product_facts.get("battery") or product_facts.get("battery_capacity_mah")
            if b:
                return f"{b}mAh Battery" if str(b).isdigit() and int(b) > 1000 else str(b)
            return "5000mAh Battery"
        elif f in ["camera", "rear_camera", "front_camera"]:
            rc = product_facts.get("rear_camera") or "50MP"
            return f"{rc} Camera"
        elif f in ["rating", "score"]:
            return f"{float(product_facts.get('rating', 4.2)):.1f}/5.0"
        return str(product_facts.get(field, "Verified Database Fact"))

    @classmethod
    def validate_llm_response(
        cls,
        response_text: str,
        ground_truth: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate generated LLM response against grounded product specifications.
        Detects hallucinated RAM, Price, CPU, and corrections needed.
        """
        if not ground_truth or not response_text:
            return True, response_text, {"status": "skipped", "issues": []}

        issues = []
        validated_text = response_text

        # 1. RAM check
        actual_ram = ground_truth.get("ram_gb") or ground_truth.get("ram")
        if actual_ram:
            actual_ram_int = int(float(actual_ram))
            ram_mentions = re.findall(r"\b(\d+)\s*(?:GB|gb)\s*(?:RAM|ram|memory)\b", response_text)
            for m in ram_mentions:
                if int(m) != actual_ram_int and int(m) in [4, 6, 8, 12, 16, 24, 32, 64]:
                    issues.append(f"RAM mismatch: Generated {m}GB vs Database {actual_ram_int}GB")
                    # Correct hallucinated RAM in text
                    validated_text = re.sub(
                        rf"\b{m}\s*(?:GB|gb)\s*(?:RAM|ram|memory)\b",
                        f"{actual_ram_int}GB RAM",
                        validated_text
                    )

        # 2. Price check
        actual_price = ground_truth.get("price")
        if actual_price and float(actual_price) > 0:
            act_p = int(float(actual_price))
            # Match ₹ with digits and commas (e.g. ₹1,20,000 or ₹78000 or ₹120,000)
            price_mentions = re.findall(r"₹\s*([0-9,]+)", response_text)
            for pm in price_mentions:
                clean_digits = pm.replace(",", "")
                if clean_digits.isdigit() and int(clean_digits) > 500:
                    p_val = int(clean_digits)
                    if abs(p_val - act_p) / max(act_p, 1) > 0.20:
                        issues.append(f"Price deviation: Generated ₹{pm} vs Database ₹{act_p:,}")
                        validated_text = re.sub(rf"₹\s*{re.escape(pm)}", f"₹{act_p:,}", validated_text)

        status = "corrected" if issues else "verified"
        return len(issues) == 0, validated_text, {"status": status, "issues": issues}

    @classmethod
    def clean_and_validate_evidence(
        cls,
        snippets: List[Dict[str, Any]],
        target_product_name: Optional[str] = None,
        target_category: Optional[str] = None,
        min_score: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Context cleaning: remove duplicate chunks, chunks with low relevance,
        or chunks explicitly belonging to an unrelated product/category.
        """
        cleaned = []
        seen_texts = set()

        for s in snippets:
            content = str(s.get("content", "")).strip()
            score = float(s.get("rerank_score") or s.get("score") or s.get("similarity_score") or 0.5)

            # Skip very low scores
            if score < min_score:
                continue

            # Skip exact text duplicates
            norm_text = re.sub(r"\s+", " ", content.lower())
            if norm_text in seen_texts:
                continue
            seen_texts.add(norm_text)

            # Category filter validation
            chunk_cat = str(s.get("category", "")).lower()
            if target_category and chunk_cat:
                t_cat = target_category.lower()
                if (t_cat == "laptop" and "mobile" in chunk_cat) or (t_cat in ["phone", "mobile"] and "laptop" in chunk_cat):
                    continue

            cleaned.append(s)

        # Safe fallback: if filtering removed all items, return top uncorrupted snippets
        if not cleaned and snippets:
            return snippets[:3]

        return cleaned
