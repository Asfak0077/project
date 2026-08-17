"""
Category-Aware Recommendation Engine
Generates explainable, scored product recommendations tailored to Laptops, Phones, and Tablets.
"""
from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from models.product import Product, ProductSpec
from models.recommendation import Recommendation, RecommendationItem
from services.product_data_validator import get_normalized_product_facts, format_product_response
from services.nlp_service import NLPService

logger = logging.getLogger("backend.recommendation")


class RecommendationService:
    @staticmethod
    def normalize_category(category: Optional[str]) -> Optional[str]:
        """Normalize category string to standard database categories."""
        if not category or str(category).lower() in ["all", "none", "any"]:
            return None
        cat_lower = str(category).lower().strip()
        if "phone" in cat_lower or "mobile" in cat_lower or "smartphone" in cat_lower:
            return "Phone"
        elif "tablet" in cat_lower or "tab" in cat_lower or "ipad" in cat_lower or "slate" in cat_lower:
            return "Tablet"
        elif "laptop" in cat_lower or "notebook" in cat_lower or "macbook" in cat_lower:
            return "Laptop"
        return category.capitalize()

    @classmethod
    def filter_products(
        cls,
        db: Session,
        category: Optional[str] = "Laptop",
        brand: Optional[str] = None,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        min_ram: Optional[float] = None,
        search_term: Optional[str] = None,
        limit: int = 30
    ) -> List[Product]:
        """
        SQL query to fetch candidate products matching strict category, budget, and hardware constraints.
        """
        query = db.query(Product).join(ProductSpec, isouter=True).filter(Product.is_active == True)

        norm_cat = cls.normalize_category(category)
        if norm_cat:
            query = query.filter(Product.category.ilike(f"%{norm_cat}%"))

        if brand and brand.lower() != "all":
            query = query.filter(Product.brand.ilike(f"%{brand}%"))

        # Budget enforcement
        if max_price is not None and max_price > 0:
            query = query.filter(Product.price <= max_price)

        if min_price is not None and min_price > 0:
            query = query.filter(Product.price >= min_price)

        if min_ram is not None and min_ram > 0:
            query = query.filter(
                or_(
                    ProductSpec.ram_gb >= min_ram,
                    Product.name.ilike(f"%{int(min_ram)}GB%"),
                    Product.name.ilike(f"%{int(min_ram)} GB%")
                )
            )

        if search_term:
            terms = search_term.strip().split()
            for term in terms:
                if len(term) >= 2:
                    query = query.filter(
                        or_(
                            Product.name.ilike(f"%{term}%"),
                            Product.brand.ilike(f"%{term}%"),
                            Product.model.ilike(f"%{term}%"),
                            ProductSpec.cpu.ilike(f"%{term}%"),
                            ProductSpec.gpu.ilike(f"%{term}%")
                        )
                    )

        results = query.order_by(desc(Product.score), desc(Product.rating)).limit(limit).all()

        # Fallback if zero items strictly under max_price
        if not results and max_price:
            logger.info(f"No products found strictly under ₹{max_price:,.0f} for category '{norm_cat}', fetching closest alternatives...")
            fallback_query = db.query(Product).join(ProductSpec, isouter=True).filter(Product.is_active == True)
            if norm_cat:
                fallback_query = fallback_query.filter(Product.category.ilike(f"%{norm_cat}%"))
            results = fallback_query.order_by(Product.price.asc()).limit(limit).all()

        return results

    @staticmethod
    def calculate_price_score(price: float, max_price: Optional[float]) -> float:
        """Calculate budget efficiency score (0-30 points)."""
        if not max_price or max_price <= 0:
            return 25.0

        if price <= max_price:
            ratio = price / max_price
            return round(20.0 + (1.0 - abs(0.85 - ratio)) * 10.0, 1)
        else:
            over_ratio = (price - max_price) / max_price
            penalty = over_ratio * 30.0
            return max(0.0, round(15.0 - penalty, 1))

    @staticmethod
    def calculate_feature_score(
        facts: Dict[str, Any],
        purpose: str,
        category: str
    ) -> float:
        """Calculate hardware specification suitability score adapted to gadget category (0-30 points)."""
        score = 18.0
        cat_lower = str(category).lower()
        ram_val = facts.get("ram_gb", 4.0)

        # Phone specific feature scoring
        if "phone" in cat_lower or "mobile" in cat_lower:
            cam_str = str(facts.get("camera", facts.get("rear_camera", ""))).lower()
            cam_match = re.search(r"(\d+)\s*(?:mp|megapixel)", cam_str)
            if cam_match:
                mp = int(cam_match.group(1))
                if mp >= 108:
                    score += 6.0
                elif mp >= 50:
                    score += 4.0
                elif mp >= 12:
                    score += 2.0

            if facts.get("5g"):
                score += 3.0

            if ram_val >= 8:
                score += 3.0

            bat_str = str(facts.get("battery", "")).lower()
            bat_match = re.search(r"(\d+)\s*mah", bat_str)
            if bat_match and int(bat_match.group(1)) >= 5000:
                score += 3.0

        # Tablet specific feature scoring
        elif "tablet" in cat_lower or "tab" in cat_lower:
            if facts.get("stylus"):
                score += 5.0
            if ram_val >= 4:
                score += 4.0
            disp_str = str(facts.get("display", ""))
            disp_m = re.search(r"(\d+(?:\.\d+)?)\s*inch", disp_str)
            if disp_m and float(disp_m.group(1)) >= 10.0:
                score += 3.0

        # Laptop specific feature scoring
        else:
            gpu_str = str(facts.get("gpu", "")).lower()
            cpu_str = str(facts.get("processor", "")).lower()

            if purpose == "gaming":
                if any(k in gpu_str for k in ["4090", "4080", "4070", "3080"]):
                    score += 12.0
                elif any(k in gpu_str for k in ["4060", "3070", "3060"]):
                    score += 10.0
                elif any(k in gpu_str for k in ["3050", "2050", "1650", "1050"]):
                    score += 7.0
                elif "geforce" in gpu_str or "radeon" in gpu_str:
                    score += 4.0
                else:
                    score -= 8.0

                if ram_val >= 16:
                    score += 3.0

            elif purpose == "editing":
                if "oled" in facts.get("display", "").lower():
                    score += 8.0
                if ram_val >= 16:
                    score += 4.0
                if any(k in cpu_str for k in ["i7", "ryzen 7", "m3", "i9", "ryzen 9"]):
                    score += 4.0

            elif purpose == "coding":
                if ram_val >= 16:
                    score += 8.0
                elif ram_val >= 8:
                    score += 4.0
                if any(k in cpu_str for k in ["i7", "ryzen 7", "m3", "i5"]):
                    score += 4.0

            elif purpose == "work":
                if ram_val >= 8:
                    score += 6.0
                if "ssd" in facts.get("storage", "").lower():
                    score += 4.0

        return min(max(round(score, 1), 5.0), 30.0)

    @staticmethod
    def calculate_performance_score(facts: Dict[str, Any]) -> float:
        """Calculate benchmark hardware score (0-25 points)."""
        base_score = facts.get("score", 75.0)
        perf_pts = 10.0 + ((base_score - 50.0) / 50.0) * 15.0
        return min(max(round(perf_pts, 1), 5.0), 25.0)

    @staticmethod
    def calculate_rating_score(rating: float) -> float:
        """Calculate customer satisfaction score (0-15 points)."""
        r = min(max(rating, 1.0), 5.0)
        return round((r / 5.0) * 15.0, 1)

    @classmethod
    def score_product(
        cls,
        prod: Product,
        nlp_data: Dict[str, Any],
        max_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculate traceable, explainable matching score with exact formula components."""
        facts = get_normalized_product_facts(prod)
        purpose = nlp_data.get("purpose", "balanced")
        category = facts.get("category", "Laptop")

        price_score = cls.calculate_price_score(facts["price"], max_price)
        feature_score = cls.calculate_feature_score(facts, purpose, category)
        performance_score = cls.calculate_performance_score(facts)
        rating_score = cls.calculate_rating_score(facts["rating"])

        final_score = round(price_score + feature_score + performance_score + rating_score)
        final_score = min(max(final_score, 40), 99)

        reasons: List[str] = []
        if max_price and facts["price"] <= max_price:
            savings = max_price - facts["price"]
            if savings > 0:
                reasons.append(f"Fits your ₹{max_price:,.0f} budget (₹{savings:,.0f} headroom)")
            else:
                reasons.append(f"Matches your ₹{max_price:,.0f} budget limit")
        elif max_price and facts["price"] > max_price:
            reasons.append(f"Above your ₹{max_price:,.0f} budget (+₹{facts['price'] - max_price:,.0f})")

        reasons.append(f"{facts['processor']} with {facts['ram']} RAM")
        if facts.get("category") == "Phone":
            if facts.get("camera"):
                reasons.append(f"Camera: {facts['camera']}")
            if facts.get("5g"):
                reasons.append("5G Network Ready")
        elif facts.get("category") == "Tablet":
            if facts.get("stylus"):
                reasons.append("Stylus & Pen Support")
            reasons.append(f"Battery: {facts['battery']}")
        else:
            if "integrated" not in str(facts.get("gpu", "")).lower():
                reasons.append(f"Dedicated {facts['gpu']}")
            reasons.append(f"{facts['storage']} storage")

        strengths: List[str] = [
            f"Hardware Benchmark: {facts['score']:.0f}/100",
            f"User Rating: ⭐ {facts['rating']} / 5.0",
        ]
        if facts["ram_gb"] >= 16:
            strengths.append(f"High-capacity {facts['ram']} memory for heavy multitasking")
        if "ssd" in facts["storage"].lower():
            strengths.append(f"Fast {facts['storage']}")
        if facts.get("5g"):
            strengths.append("High-speed 5G network connectivity")

        tradeoffs: List[str] = []
        if facts["ram_gb"] <= 2:
            tradeoffs.append("2GB RAM is limited to basic single-task use")
        elif facts["ram_gb"] <= 4 and facts.get("category") == "Laptop":
            tradeoffs.append("4GB RAM may constrain heavy multitasking")

        is_over_budget = bool(max_price and facts["price"] > max_price)
        formatted_schema = format_product_response(prod)

        return {
            "product_raw": prod,
            "product": formatted_schema,
            "match_score": int(final_score),
            "score_breakdown": {
                "price_score": price_score,
                "feature_score": feature_score,
                "performance_score": performance_score,
                "rating_score": rating_score,
                "final_score": final_score,
            },
            "reason": " • ".join(reasons[:2]),
            "strengths": strengths,
            "weaknesses": tradeoffs,
            "is_over_budget": is_over_budget,
            "budget_tag": "Above your budget" if is_over_budget else "Within budget",
        }

    @classmethod
    def get_recommendations(
        cls,
        db: Session,
        query: str,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        extracted_requirements: Optional[Dict[str, Any]] = None,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """Category-aware recommendation pipeline with strict constraint filtering."""
        nlp_data = extracted_requirements if extracted_requirements else NLPService.extract_requirements(query)
        detected_category = nlp_data.get("category")
        active_category = detected_category if detected_category else (category or "Laptop")

        max_price = nlp_data.get("max_price")
        min_price = nlp_data.get("min_price")
        brand = nlp_data.get("brand")
        min_ram = nlp_data.get("min_ram")

        candidates = cls.filter_products(
            db=db,
            category=active_category,
            brand=brand,
            max_price=max_price,
            min_price=min_price,
            min_ram=min_ram,
            search_term=None,
            limit=30,
        )

        scored_items = [cls.score_product(p, nlp_data, max_price=max_price) for p in candidates]
        scored_items.sort(key=lambda x: (not x["is_over_budget"], x["match_score"], -x["product"].price), reverse=True)

        recommendations = []
        for rank_idx, item in enumerate(scored_items[:top_k], start=1):
            recommendations.append({
                "product": item["product"],
                "match_score": item["match_score"],
                "rank": rank_idx,
                "reason": item["reason"],
                "strengths": item["strengths"],
                "weaknesses": item["weaknesses"]
            })

        cat_label = active_category if active_category else "product"
        summary_text = (
            f"Found {len(candidates)} matching {cat_label}s in AWS RDS MySQL inventory. "
            f"Top match '{recommendations[0]['product'].name}' scores {recommendations[0]['match_score']}/100."
            if recommendations else f"No {cat_label}s matching '{query}' found in inventory."
        )

        return {
            "query": query,
            "category": active_category,
            "nlp_extracted": nlp_data,
            "recommendations": recommendations,
            "summary": summary_text
        }
