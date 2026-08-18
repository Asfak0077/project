"""
Category-Aware Comparison Service
Generates dynamic side-by-side specification comparison tables for Laptops, Phones, and Tablets.
Only renders columns for the strictly selected products.
"""
from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional
from services.product_data_validator import normalize_product_name

logger = logging.getLogger("backend.comparison_service")


class ComparisonService:
    @staticmethod
    def compare_products(products: List[Dict[str, Any]], section_focus: Optional[str] = None) -> Dict[str, Any]:
        """
        Build dynamic side-by-side specification comparison delta matrix.
        Adapts spec rows dynamically based on product categories and strictly renders
        columns ONLY for the provided products list.
        """
        if not products or len(products) < 2:
            return {
                "markdown": "Please select at least two products to generate a side-by-side comparison.",
                "winner": None,
                "winner_reason": None,
            }

        # Deduplicate products by ID
        seen_ids = set()
        unique_products = []
        for p in products:
            if p and p.get("id") is not None and p.get("id") not in seen_ids:
                unique_products.append(p)
                seen_ids.add(p.get("id"))

        if len(unique_products) < 2:
            unique_products = products[:2]

        products = unique_products

        # Detect primary category among compared items
        categories = [str(p.get("category", "Laptop")).capitalize() for p in products]
        is_phone_comp = any("Phone" in c for c in categories)
        is_tablet_comp = any("Tablet" in c for c in categories)

        headers = ["Technical Specification"] + [
            f"**{normalize_product_name(p.get('brand', ''), p.get('name', ''))}**"
            for p in products
        ]

        def _format_ram(p: Dict[str, Any]) -> str:
            raw_ram = p.get("ram_gb") if p.get("ram_gb") is not None else p.get("ram")
            if raw_ram is None or str(raw_ram).strip() in ["", "0", "nan", "NaN"]:
                return "8GB RAM"
            r_str = str(raw_ram).upper().replace("GB", "").replace("RAM", "").strip()
            if r_str.replace(".", "", 1).isdigit():
                return f"{int(float(r_str))}GB RAM"
            return f"{raw_ram} RAM" if not str(raw_ram).upper().endswith("RAM") else str(raw_ram)

        def _format_price(p: Dict[str, Any]) -> str:
            raw_p = str(p.get("price", 0)).replace("₹", "").replace(",", "").strip()
            try:
                return f"₹{int(float(raw_p)):,}"
            except Exception:
                return f"₹{p.get('price', 0)}"

        rows = [
            ["📂 Category", *[str(p.get("category", "Laptop")) for p in products]],
            ["💰 Price", *[_format_price(p) for p in products]],
            ["🧠 RAM", *[_format_ram(p) for p in products]],
            ["⚡ Processor", *[str(p.get('processor') or p.get('cpu', 'N/A')) for p in products]],
            ["💾 Storage", *[str(p.get('storage', 'N/A')) for p in products]],
            ["🖥️ Display", *[str(p.get('display', 'Standard Display')) for p in products]],
            ["🔋 Battery Spec", *[str(p.get('battery', 'Standard Battery')) for p in products]],
        ]

        if is_phone_comp:
            rows.append(["📸 Rear Camera", *[str(p.get('camera') or p.get('rear_camera') or 'Standard Camera') for p in products]])
            rows.append(["📶 5G Ready", *["Yes (5G Ready)" if p.get('5g') else "4G / LTE" for p in products]])
        elif is_tablet_comp:
            rows.append(["✏️ Stylus Support", *["Supported" if p.get('stylus') else "Not specified" for p in products]])
        else:
            rows.append(["🎮 Graphics (GPU)", *[str(p.get('gpu', 'Integrated')) for p in products]])

        rows.extend([
            ["⭐ Customer Rating", *[f"⭐ {float(p.get('rating', 4.0)):.1f}/5.0" for p in products]],
            ["📊 Performance Index", *[f"{int(float(p.get('score', 80)))}/100" for p in products]],
        ])

        table_lines = [
            "### 📊 Side-by-Side Technical Comparison Matrix",
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows:
            table_lines.append("| " + " | ".join(row) + " |")

        # Determine winner
        winner = max(products, key=lambda x: float(x.get("score", 0)))
        clean_winner_name = normalize_product_name(winner.get("brand", ""), winner.get("name", ""))
        winner_cat = winner.get("category", "Product")

        if section_focus:
            sf = section_focus.lower().strip()
            if sf in ["gpu", "graphics"]:
                winner_reason = (
                    f"**Verdict & Winner for Graphics (GPU):** **{clean_winner_name}** leads with "
                    f"**{winner.get('gpu', 'dedicated graphics')}**, delivering superior frame rates."
                )
            elif sf in ["price", "cost", "cheaper"]:
                cheapest = min(products, key=lambda x: float(x.get("price", float('inf'))))
                clean_cheapest = normalize_product_name(cheapest.get("brand", ""), cheapest.get("name", ""))
                winner_reason = (
                    f"**Verdict for Best Value / Price:** **{clean_cheapest}** is more affordable at "
                    f"**₹{int(float(cheapest.get('price', 0))):,}**."
                )
            elif sf in ["processor", "cpu"]:
                winner_reason = (
                    f"**Verdict & Winner for Processor (CPU):** **{clean_winner_name}** delivers higher compute throughput with its **{winner.get('processor', 'CPU')}**."
                )
            elif sf in ["battery"]:
                winner_reason = (
                    f"**Verdict for Battery Endurance:** **{clean_winner_name}** provides longer runtime with its **{winner.get('battery', 'battery')}**."
                )
            elif sf in ["camera"]:
                winner_reason = (
                    f"**Verdict for Camera Quality:** **{clean_winner_name}** leads with its **{winner.get('rear_camera', 'camera')}**."
                )
            else:
                winner_reason = (
                    f"**Verdict & Winner:** **{clean_winner_name}** leads overall with a score of "
                    f"**{int(float(winner.get('score', 85)))}/100**."
                )
        else:
            if winner_cat == "Phone":
                highlight = f"**{winner.get('camera', 'Camera')}**, **{int(float(winner.get('ram_gb') or 4))}GB RAM**, and **{winner.get('battery', 'Battery')}**"
            elif winner_cat == "Tablet":
                highlight = f"**{winner.get('display', 'Display')}**, **{winner.get('battery', 'Battery')}**, and **{int(float(winner.get('ram_gb') or 4))}GB RAM**"
            else:
                highlight = f"**{winner.get('processor', 'CPU')}**, **{int(float(winner.get('ram_gb') or 8))}GB RAM**, and **{winner.get('gpu', 'graphics')}**"

            winner_reason = (
                f"**Verdict & Winner:** **{clean_winner_name}** leads overall with a score of "
                f"**{int(float(winner.get('score', 85)))}/100**, driven by its {highlight}."
            )

        table_lines.append("")
        table_lines.append(f"> 🏆 {winner_reason}")

        return {
            "markdown": "\n".join(table_lines),
            "winner": winner,
            "winner_reason": winner_reason,
            "fields": [
                "price", "processor", "ram", "storage", "gpu", "display", "battery"
            ],
            "compared_products": [p["id"] for p in products if p.get("id")],
        }
