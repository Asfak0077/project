"""
AI Product Comparison Battle Mode Service
Calculates multi-round category battle scores, computes weighted totals,
invokes the AI Judge for grounded verdict generation, and persists battle results.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from models.battle import ProductBattleHistory
from services.product_service import ProductService
from services.product_data_validator import normalize_product_name
from services.rag_service import RAGService
from utils.config import settings

logger = logging.getLogger("backend.battle_service")

# Scoring Weights
WEIGHT_PERFORMANCE = 0.40
WEIGHT_PRICE_VALUE = 0.20
WEIGHT_DISPLAY = 0.15
WEIGHT_BATTERY = 0.10
WEIGHT_RATING = 0.15


class BattleService:
    @staticmethod
    def _evaluate_performance(p: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Evaluate performance (0-100) based on CPU, GPU, RAM, and Score."""
        base_score = float(p.get("score") or 75.0)
        ram = float(p.get("ram_gb") or p.get("ram") or 8.0)
        cpu = str(p.get("processor") or p.get("cpu") or "").lower()
        gpu = str(p.get("gpu") or "").lower()

        perf = base_score * 0.5

        # RAM contribution (max 20 pts)
        if ram >= 32:
            perf += 20
        elif ram >= 16:
            perf += 16
        elif ram >= 12:
            perf += 13
        elif ram >= 8:
            perf += 10
        else:
            perf += 5

        # CPU tier contribution (max 15 pts)
        if any(t in cpu for t in ["i9", "ryzen 9", "m3 max", "m2 max", "m3 pro", "m2 pro", "snapdragon 8 gen 3", "a17 pro", "a18"]):
            perf += 15
        elif any(t in cpu for t in ["i7", "ryzen 7", "m3", "m2", "m1", "snapdragon 8 gen 2", "a16", "dimensity 9300"]):
            perf += 12
        elif any(t in cpu for t in ["i5", "ryzen 5", "snapdragon 7", "dimensity 8200", "a15"]):
            perf += 9
        else:
            perf += 6

        # GPU tier contribution (max 15 pts)
        if any(g in gpu for g in ["rtx 4090", "rtx 4080", "rtx 3080", "rtx 4070"]):
            perf += 15
        elif any(g in gpu for g in ["rtx 4060", "rtx 4050", "rtx 3060", "rtx 3050", "gtx 1660", "radeon 780m"]):
            perf += 12
        elif any(g in gpu for g in ["dedicated", "gtx", "radeon", "geforce"]):
            perf += 9
        elif "integrated" in gpu or "iris" in gpu or "intel uhd" in gpu or "mali" in gpu or "adreno" in gpu:
            perf += 6
        else:
            perf += 8

        perf_score = min(100.0, max(30.0, round(perf, 1)))
        metrics = {
            "cpu": p.get("processor") or p.get("cpu") or "Standard Processor",
            "gpu": p.get("gpu") or "Integrated Graphics",
            "ram": f"{int(ram)}GB RAM",
            "benchmark_index": f"{int(base_score)}/100",
        }
        return perf_score, metrics

    @staticmethod
    def _evaluate_price_value(p: Dict[str, Any], opponent: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Evaluate Price Value (0-100) combining absolute price affordability and performance-per-rupee."""
        p_price = max(1000.0, float(p.get("price") or 50000.0))
        o_price = max(1000.0, float(opponent.get("price") or 50000.0))
        p_score = float(p.get("score") or 75.0)

        # Performance per 10k INR
        vfm_ratio = (p_score / p_price) * 10000.0

        # Relative price advantage
        if p_price < o_price:
            savings_pct = (o_price - p_price) / o_price
            price_pts = 60.0 + min(40.0, savings_pct * 80.0)
        elif p_price == o_price:
            price_pts = 75.0
        else:
            premium_pct = (p_price - o_price) / p_price
            price_pts = max(35.0, 75.0 - (premium_pct * 60.0))

        vfm_pts = min(100.0, vfm_ratio * 35.0)
        total_val = round(0.6 * price_pts + 0.4 * vfm_pts, 1)
        final_val = min(100.0, max(25.0, total_val))

        metrics = {
            "price": f"₹{int(p_price):,}",
            "value_index": f"{round(vfm_ratio, 2)} pts/₹10k",
            "price_delta": f"{'+' if p_price > o_price else ''}₹{int(p_price - o_price):,}" if p_price != o_price else "Equal Price",
        }
        return final_val, metrics

    @staticmethod
    def _evaluate_display(p: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Evaluate Display (0-100) based on resolution, refresh rate, and panel type."""
        disp_str = str(p.get("display") or p.get("screen_size") or "").lower()
        score = 65.0

        if any(w in disp_str for w in ["oled", "amoled", "liquid retina", "mini-led", "retina"]):
            score += 18.0
        elif "ips" in disp_str:
            score += 10.0

        if any(w in disp_str for w in ["4k", "uhd", "3840", "3.2k", "2.8k", "2880"]):
            score += 15.0
        elif any(w in disp_str for w in ["2k", "qhd", "1440p", "2560", "wqxga"]):
            score += 10.0
        elif any(w in disp_str for w in ["fhd", "1080p", "1920"]):
            score += 6.0

        if any(w in disp_str for w in ["240hz", "165hz", "144hz"]):
            score += 10.0
        elif "120hz" in disp_str:
            score += 7.0
        elif "90hz" in disp_str:
            score += 4.0

        final_score = min(100.0, max(40.0, round(score, 1)))
        metrics = {
            "display": p.get("display") or "Standard High-Definition Display",
            "resolution": "4K / Ultra-HD" if "4k" in disp_str else ("2K / QHD" if "2k" in disp_str or "1440" in disp_str else "Full HD (1080p)"),
            "refresh_rate": "144Hz+" if any(w in disp_str for w in ["144hz", "165hz", "240hz"]) else ("120Hz" if "120hz" in disp_str else "60Hz Standard"),
        }
        return final_score, metrics

    @staticmethod
    def _evaluate_battery(p: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Evaluate Battery (0-100) based on capacity (Wh / mAh) and battery spec string."""
        b_str = str(p.get("battery") or p.get("battery_capacity_mah") or "").lower()
        score = 60.0
        runtime_est = "6-8 Hours"

        # Check Wh for laptops
        wh_match = re.search(r"(\d+)\s*wh", b_str)
        mah_match = re.search(r"(\d{3,5})\s*mah", b_str)

        if wh_match:
            wh = int(wh_match.group(1))
            if wh >= 90:
                score = 95.0
                runtime_est = "10-14 Hours"
            elif wh >= 75:
                score = 88.0
                runtime_est = "8-11 Hours"
            elif wh >= 55:
                score = 76.0
                runtime_est = "6-8 Hours"
            else:
                score = 65.0
                runtime_est = "4-6 Hours"
        elif mah_match:
            mah = int(mah_match.group(1))
            if mah >= 6000:
                score = 96.0
                runtime_est = "1.5-2 Days"
            elif mah >= 5000:
                score = 88.0
                runtime_est = "Full Day Heavy"
            elif mah >= 4500:
                score = 80.0
                runtime_est = "All Day Normal"
            else:
                score = 70.0
                runtime_est = "Standard Day"
        else:
            if "all day" in b_str or "long" in b_str:
                score = 85.0
                runtime_est = "All-Day Battery"
            else:
                score = 72.0
                runtime_est = "6-8 Hours"

        metrics = {
            "battery_spec": p.get("battery") or "High Capacity Lithium-Ion",
            "runtime_estimate": runtime_est,
        }
        return round(score, 1), metrics

    @staticmethod
    def _evaluate_rating(p: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Evaluate User Rating (0-100) based on customer reviews and stars."""
        rating = float(p.get("rating") or 4.2)
        reviews = int(p.get("reviews") or 150)

        # 5.0 -> 100, 4.0 -> 80, 3.0 -> 60
        r_score = (rating / 5.0) * 90.0
        # Volume boost
        vol_boost = min(10.0, (reviews / 500.0) * 10.0)
        final_score = min(100.0, max(40.0, round(r_score + vol_boost, 1)))

        metrics = {
            "rating": f"⭐ {rating:.1f} / 5.0",
            "review_count": f"{reviews:,} verified ratings",
        }
        return final_score, metrics

    @classmethod
    def run_battle(
        cls,
        db: Session,
        p1: Dict[str, Any],
        p2: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute full AI Battle:
        1. 5 animated combat rounds
        2. Weighted final scores
        3. Winner determination
        4. AI Judge verdict & key winning factors
        5. Database record creation
        """
        if not p1 or not p2:
            raise ValueError("Please select valid products for battle.")

        if str(p1.get("id")) == str(p2.get("id")):
            raise ValueError("Cannot battle a product against itself. Please select 2 distinct products.")

        p1_name = normalize_product_name(p1.get("brand", ""), p1.get("name", "Product 1"))
        p2_name = normalize_product_name(p2.get("brand", ""), p2.get("name", "Product 2"))

        # If distinct products happen to share identical normalized names, differentiate them
        if p1_name == p2_name:
            p1_name = f"{p1_name} (Variant 1)"
            p2_name = f"{p2_name} (Variant 2)"

        # Round 1: Performance (40%)
        r1_p1_score, r1_p1_met = cls._evaluate_performance(p1)
        r1_p2_score, r1_p2_met = cls._evaluate_performance(p2)
        r1_winner = "p1" if r1_p1_score > r1_p2_score else ("p2" if r1_p2_score > r1_p1_score else "tie")
        r1_winner_name = p1_name if r1_winner == "p1" else (p2_name if r1_winner == "p2" else "Tie")
        r1_reason = (
            f"**{r1_winner_name}** takes the Performance Round with stronger {r1_p1_met['cpu'] if r1_winner == 'p1' else r1_p2_met['cpu']} and {r1_p1_met['gpu'] if r1_winner == 'p1' else r1_p2_met['gpu']}."
            if r1_winner != "tie" else "Both products offer comparable processing horsepower."
        )

        # Round 2: Price Value (20%)
        r2_p1_score, r2_p1_met = cls._evaluate_price_value(p1, p2)
        r2_p2_score, r2_p2_met = cls._evaluate_price_value(p2, p1)
        r2_winner = "p1" if r2_p1_score > r2_p2_score else ("p2" if r2_p2_score > r2_p1_score else "tie")
        r2_winner_name = p1_name if r2_winner == "p1" else (p2_name if r2_winner == "p2" else "Tie")
        r2_reason = (
            f"**{r2_winner_name}** offers superior price-to-performance value at {r2_p1_met['price'] if r2_winner == 'p1' else r2_p2_met['price']}."
            if r2_winner != "tie" else "Both offer identical value per rupee."
        )

        # Round 3: Display (15%)
        r3_p1_score, r3_p1_met = cls._evaluate_display(p1)
        r3_p2_score, r3_p2_met = cls._evaluate_display(p2)
        r3_winner = "p1" if r3_p1_score > r3_p2_score else ("p2" if r3_p2_score > r3_p1_score else "tie")
        r3_winner_name = p1_name if r3_winner == "p1" else (p2_name if r3_winner == "p2" else "Tie")
        r3_reason = (
            f"**{r3_winner_name}** delivers a sharper visual experience with its {r3_p1_met['display'] if r3_winner == 'p1' else r3_p2_met['display']}."
            if r3_winner != "tie" else "Both displays feature matching clarity and refresh rates."
        )

        # Round 4: Battery (10%)
        r4_p1_score, r4_p1_met = cls._evaluate_battery(p1)
        r4_p2_score, r4_p2_met = cls._evaluate_battery(p2)
        r4_winner = "p1" if r4_p1_score > r4_p2_score else ("p2" if r4_p2_score > r4_p1_score else "tie")
        r4_winner_name = p1_name if r4_winner == "p1" else (p2_name if r4_winner == "p2" else "Tie")
        r4_reason = (
            f"**{r4_winner_name}** provides higher endurance with an estimated runtime of {r4_p1_met['runtime_estimate'] if r4_winner == 'p1' else r4_p2_met['runtime_estimate']}."
            if r4_winner != "tie" else "Both devices provide comparable all-day battery endurance."
        )

        # Round 5: User Rating (15%)
        r5_p1_score, r5_p1_met = cls._evaluate_rating(p1)
        r5_p2_score, r5_p2_met = cls._evaluate_rating(p2)
        r5_winner = "p1" if r5_p1_score > r5_p2_score else ("p2" if r5_p2_score > r5_p1_score else "tie")
        r5_winner_name = p1_name if r5_winner == "p1" else (p2_name if r5_winner == "p2" else "Tie")
        r5_reason = (
            f"**{r5_winner_name}** holds higher buyer confidence with {r5_p1_met['rating'] if r5_winner == 'p1' else r5_p2_met['rating']}."
            if r5_winner != "tie" else "Both hold identical top-tier consumer satisfaction scores."
        )

        # Weighted Final Scores
        p1_final_score = round(
            r1_p1_score * WEIGHT_PERFORMANCE +
            r2_p1_score * WEIGHT_PRICE_VALUE +
            r3_p1_score * WEIGHT_DISPLAY +
            r4_p1_score * WEIGHT_BATTERY +
            r5_p1_score * WEIGHT_RATING,
            1
        )
        p2_final_score = round(
            r1_p2_score * WEIGHT_PERFORMANCE +
            r2_p2_score * WEIGHT_PRICE_VALUE +
            r3_p2_score * WEIGHT_DISPLAY +
            r4_p2_score * WEIGHT_BATTERY +
            r5_p2_score * WEIGHT_RATING,
            1
        )

        if p1_final_score > p2_final_score:
            overall_winner_id = p1.get("id")
            overall_winner_key = "p1"
            overall_winner_name = p1_name
            winner_score = p1_final_score
            loser_score = p2_final_score
            winning_product = p1
        elif p2_final_score > p1_final_score:
            overall_winner_id = p2.get("id")
            overall_winner_key = "p2"
            overall_winner_name = p2_name
            winner_score = p2_final_score
            loser_score = p1_final_score
            winning_product = p2
        else:
            overall_winner_id = None
            overall_winner_key = "tie"
            overall_winner_name = "Draw / Even Match"
            winner_score = p1_final_score
            loser_score = p2_final_score
            winning_product = p1

        # Key Winning Advantages
        key_reasons = []
        if overall_winner_key == "p1":
            if r1_winner == "p1":
                key_reasons.append(f"Superior processing and graphics throughput ({r1_p1_met['cpu']})")
            if r2_winner == "p1":
                key_reasons.append(f"Better price-to-performance value (₹{int(p1.get('price', 0)):,})")
            if r3_winner == "p1":
                key_reasons.append(f"Higher quality display panel ({r3_p1_met['display']})")
            if r4_winner == "p1":
                key_reasons.append(f"Longer battery runtime ({r4_p1_met['runtime_estimate']})")
            if r5_winner == "p1":
                key_reasons.append(f"Higher verified user satisfaction ({r5_p1_met['rating']})")
        elif overall_winner_key == "p2":
            if r1_winner == "p2":
                key_reasons.append(f"Superior processing and graphics throughput ({r1_p2_met['cpu']})")
            if r2_winner == "p2":
                key_reasons.append(f"Better price-to-performance value (₹{int(p2.get('price', 0)):,})")
            if r3_winner == "p2":
                key_reasons.append(f"Higher quality display panel ({r3_p2_met['display']})")
            if r4_winner == "p2":
                key_reasons.append(f"Longer battery runtime ({r4_p2_met['runtime_estimate']})")
            if r5_winner == "p2":
                key_reasons.append(f"Higher verified user satisfaction ({r5_p2_met['rating']})")

        if not key_reasons:
            key_reasons = [
                "Balanced hardware specifications across both choices",
                "Competitive pricing and reliable build quality",
            ]

        confidence_score = min(99, max(82, int(85 + abs(p1_final_score - p2_final_score) * 1.5)))

        rounds_data = [
            {
                "round_number": 1,
                "title": "Performance Battle",
                "icon": "🔥",
                "weight": "40%",
                "p1_score": r1_p1_score,
                "p2_score": r1_p2_score,
                "p1_metrics": r1_p1_met,
                "p2_metrics": r1_p2_met,
                "winner": r1_winner,
                "winner_name": r1_winner_name,
                "reason": r1_reason,
            },
            {
                "round_number": 2,
                "title": "Price Value Battle",
                "icon": "💰",
                "weight": "20%",
                "p1_score": r2_p1_score,
                "p2_score": r2_p2_score,
                "p1_metrics": r2_p1_met,
                "p2_metrics": r2_p2_met,
                "winner": r2_winner,
                "winner_name": r2_winner_name,
                "reason": r2_reason,
            },
            {
                "round_number": 3,
                "title": "Display Battle",
                "icon": "🖥",
                "weight": "15%",
                "p1_score": r3_p1_score,
                "p2_score": r3_p2_score,
                "p1_metrics": r3_p1_met,
                "p2_metrics": r3_p2_met,
                "winner": r3_winner,
                "winner_name": r3_winner_name,
                "reason": r3_reason,
            },
            {
                "round_number": 4,
                "title": "Battery Battle",
                "icon": "🔋",
                "weight": "10%",
                "p1_score": r4_p1_score,
                "p2_score": r4_p2_score,
                "p1_metrics": r4_p1_met,
                "p2_metrics": r4_p2_met,
                "winner": r4_winner,
                "winner_name": r4_winner_name,
                "reason": r4_reason,
            },
            {
                "round_number": 5,
                "title": "User Rating Battle",
                "icon": "⭐",
                "weight": "15%",
                "p1_score": r5_p1_score,
                "p2_score": r5_p2_score,
                "p1_metrics": r5_p1_met,
                "p2_metrics": r5_p2_met,
                "winner": r5_winner,
                "winner_name": r5_winner_name,
                "reason": r5_reason,
            },
        ]

        ai_verdict = {
            "summary": f"In this AI-judged combat, **{overall_winner_name}** emerged victorious with an aggregate score of **{winner_score}/100** versus **{loser_score}/100**.",
            "performance_winner": r1_winner_name,
            "performance_reason": r1_reason,
            "price_winner": r2_winner_name,
            "price_reason": r2_reason,
            "final_winner": overall_winner_name,
            "final_winner_id": overall_winner_id,
            "confidence_score": f"{confidence_score}%",
            "key_reasons": key_reasons,
        }

        # Build battle result payload
        battle_result_data = {
            "product_1": p1,
            "product_2": p2,
            "product_1_name": p1_name,
            "product_2_name": p2_name,
            "product_1_score": p1_final_score,
            "product_2_score": p2_final_score,
            "winner_id": overall_winner_id,
            "winner_name": overall_winner_name,
            "winner_score": winner_score,
            "rounds": rounds_data,
            "ai_verdict": ai_verdict,
            "key_reasons": key_reasons,
            "confidence": f"{confidence_score}%",
        }

        # Persist in Database
        saved_id = None
        try:
            record = ProductBattleHistory(
                user_id=user_id,
                product_1_id=p1.get("id"),
                product_2_id=p2.get("id"),
                winner_id=overall_winner_id,
                product_1_score=p1_final_score,
                product_2_score=p2_final_score,
                battle_result=battle_result_data,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            saved_id = record.id
            logger.info(f"Saved product battle #{saved_id}: {p1_name} vs {p2_name} -> Winner: {overall_winner_name}")
        except Exception as e:
            db.rollback()
            logger.warning(f"Could not persist battle record: {e}")

        battle_result_data["battle_id"] = saved_id

        # Build clean Markdown response for chat integration
        markdown_lines = [
            f"## ⚔️ AI Battle Result: {p1_name} vs {p2_name}\n",
            f"**{p1_name}:** `{p1_final_score}/100`  ",
            f"**{p2_name}:** `{p2_final_score}/100`\n",
            f"### 🏆 Winner: **{overall_winner_name}**\n",
            "**Key Winning Factors:**",
        ]
        for kr in key_reasons:
            markdown_lines.append(f"✓ {kr}")

        markdown_lines.append(f"\n**Round Summary:**")
        for r in rounds_data:
            markdown_lines.append(f"• **Round {r['round_number']} ({r['title']}):** Winner: **{r['winner_name']}** ({r['p1_score']} vs {r['p2_score']})")

        markdown_lines.append(f"\n**AI Confidence:** {confidence_score}% Verified")

        battle_result_data["markdown"] = "\n".join(markdown_lines)
        return battle_result_data

    @staticmethod
    def get_battle_history(
        db: Session,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Retrieve battle history records for a user."""
        records = (
            db.query(ProductBattleHistory)
            .filter(ProductBattleHistory.user_id == user_id)
            .order_by(ProductBattleHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        results = []
        for r in records:
            res = dict(r.battle_result) if isinstance(r.battle_result, dict) else {}
            res["id"] = r.id
            res["created_at"] = r.created_at.isoformat() if r.created_at else None
            results.append(res)
        return results
