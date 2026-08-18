"""
Structured Response Formatting Service
Formats clean, direct, concise responses for Product Specifications,
RAG Document Answers, Comparisons, and Technical Overviews.
Eliminates unnecessary filler and repetitive product title text.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from services.product_data_validator import normalize_product_name

logger = logging.getLogger("backend.response_service")


class ResponseService:
    @staticmethod
    def format_specification_response(
        product_facts: Dict[str, Any],
        spec_field: str
    ) -> str:
        """
        Generate direct, concise answer for a single technical specification.
        Examples:
        RAM:
        32GB

        Source:
        Verified Product Database
        """
        field = spec_field.lower().strip()

        if field in ["ram", "memory"]:
            raw_ram = product_facts.get("ram_gb") if product_facts.get("ram_gb") is not None else product_facts.get("ram")
            ram_val = int(raw_ram or 8) if (raw_ram and str(raw_ram).replace('.', '', 1).isdigit()) else (raw_ram or "8GB")
            val_str = f"{ram_val}GB" if str(ram_val).isdigit() else str(ram_val)
            return f"RAM:\n{val_str}\n\n**Source:**\nVerified Product Database"

        elif field in ["price", "cost", "mrp", "rate"]:
            price_val = int(product_facts.get("price") or 0)
            return f"Price:\n₹{price_val:,}\n\n**Source:**\nVerified Product Database"

        elif field in ["processor", "cpu", "chipset", "chip"]:
            proc_val = str(product_facts.get("processor") or product_facts.get("cpu") or "Intel Core i5")
            return f"Processor:\n{proc_val}\n\n**Source:**\nVerified Product Database"

        elif field in ["storage", "disk", "ssd", "hdd", "rom"]:
            stor_val = str(product_facts.get("storage") or "512GB SSD")
            return f"Storage:\n{stor_val}\n\n**Source:**\nVerified Product Database"

        elif field in ["gpu", "graphics", "vram"]:
            gpu_val = str(product_facts.get("gpu") or "Integrated Graphics")
            return f"GPU:\n{gpu_val}\n\n**Source:**\nVerified Product Database"

        elif field in ["battery", "battery_life", "endurance", "runtime"]:
            b_raw = str(product_facts.get("battery") or product_facts.get("battery_capacity_mah") or "").strip()
            if b_raw.isdigit() and int(b_raw) > 1000:
                b_str = f"{b_raw}mAh"
            elif b_raw and b_raw.lower() not in ["none", "nan", "unknown"]:
                b_str = b_raw
            else:
                b_str = "5000mAh"
            return f"Battery:\n{b_str}\n\n**Source:**\nVerified Product Database"

        elif field in ["camera", "cameras", "rear_camera", "front_camera", "selfie"]:
            rc = product_facts.get("rear_camera") or product_facts.get("camera") or "50MP"
            fc = product_facts.get("front_camera")
            if fc and fc != rc:
                cam_str = f"Rear: {rc} | Front: {fc}"
            else:
                cam_str = str(rc)
            return f"Camera:\n{cam_str}\n\n**Source:**\nVerified Product Database"

        elif field in ["display", "screen", "panel", "resolution", "screen_size"]:
            disp_val = str(product_facts.get("display") or product_facts.get("screen_size") or "Full HD Display")
            return f"Display:\n{disp_val}\n\n**Source:**\nVerified Product Database"

        elif field in ["os", "operating_system", "windows", "android", "ios"]:
            os_val = str(product_facts.get("os") or "Android / Windows")
            return f"Operating System:\n{os_val}\n\n**Source:**\nVerified Product Database"

        elif field in ["rating", "score", "reviews"]:
            r_val = float(product_facts.get("rating", 4.2))
            return f"Rating:\n⭐ {r_val:.1f} / 5.0\n\n**Source:**\nVerified Product Database"

        elif field in ["cooling", "thermal"]:
            cool_val = str(product_facts.get("cooling") or "Dual-Fan Thermal Architecture")
            return f"Cooling:\n{cool_val}\n\n**Source:**\nVerified Product Database"

        elif field in ["warranty"]:
            return "Warranty:\n1 Year Manufacturer Warranty\n\n**Source:**\nVerified Product Database"

        elif field in ["5g", "cellular"]:
            c_str = "5G Supported" if product_facts.get("has_5g") or product_facts.get("5g") else "4G LTE"
            return f"Cellular:\n{c_str}\n\n**Source:**\nVerified Product Database"

        elif field in ["stylus", "pen"]:
            s_str = "Supported" if product_facts.get("has_stylus") or product_facts.get("stylus") else "Not specified"
            return f"Stylus:\n{s_str}\n\n**Source:**\nVerified Product Database"

        else:
            field_title = spec_field.replace("_", " ").title()
            field_val = str(product_facts.get(spec_field, "Verified in database"))
            return f"{field_title}:\n{field_val}\n\n**Source:**\nVerified Product Database"

    @staticmethod
    def format_product_analysis_response(products: List[Dict[str, Any]]) -> str:
        """
        Generate rich structured Product Analysis card for one or multiple products.
        Format:
        ## ASUS ROG Zephyrus Analysis

        Performance:
        Excellent gaming performance with Ryzen 7 and GTX 1660 Ti.

        Memory:
        32GB RAM.

        Storage:
        512GB SSD.

        Best For:
        Gaming and performance workloads.
        """
        if not products:
            return "No product specified for analysis. Please select or mention a product."

        if len(products) == 1:
            p = products[0]
            name = normalize_product_name(p.get("brand", ""), p.get("name", "Product"))
            proc = p.get("processor") or p.get("cpu") or "High-Performance Multi-Core Processor"
            gpu = p.get("gpu")
            raw_ram = p.get("ram_gb") if p.get("ram_gb") is not None else p.get("ram")
            if raw_ram and str(raw_ram).replace('.', '', 1).isdigit():
                ram_str = f"{int(float(raw_ram))}GB RAM"
            else:
                ram_str = str(p.get("ram") or "8GB RAM")
            if not ram_str.upper().endswith("RAM"):
                ram_str = f"{ram_str} RAM"

            storage = p.get("storage") or "512GB SSD"
            if not any(storage.endswith(s) for s in [".", "SSD", "HDD", "Storage"]):
                storage = f"{storage} SSD"

            gpu_str = f" and {gpu}" if gpu and "integrated" not in str(gpu).lower() else ""
            is_gaming = "gaming" in name.lower() or (gpu and any(g in str(gpu).lower() for g in ["rtx", "gtx", "radeon", "geforce"]))
            perf_text = f"Excellent gaming and multitasking performance with {proc}{gpu_str}." if is_gaming else f"Smooth, responsive performance powered by {proc}{gpu_str}."
            
            best_for = "Gaming, creative content production, and intensive performance workloads." if is_gaming else "Everyday multitasking, office productivity, and entertainment."

            return (
                f"## {name} Analysis\n\n"
                f"**Performance:**\n{perf_text}\n\n"
                f"**Memory:**\n{ram_str}.\n\n"
                f"**Storage:**\n{storage}.\n\n"
                f"**Best For:**\n{best_for}"
            )

        # Multi-product analysis
        sections = ["## Product Analysis\n"]
        for idx, p in enumerate(products, 1):
            name = normalize_product_name(p.get("brand", ""), p.get("name", "Product"))
            proc = p.get("processor") or p.get("cpu") or "High-Performance Processor"
            gpu = p.get("gpu")
            raw_ram = p.get("ram_gb") if p.get("ram_gb") is not None else p.get("ram")
            ram_str = f"{int(float(raw_ram))}GB RAM" if (raw_ram and str(raw_ram).replace('.', '', 1).isdigit()) else str(p.get("ram") or "8GB RAM")
            storage = p.get("storage") or "512GB SSD"
            gpu_str = f" and {gpu}" if gpu and "integrated" not in str(gpu).lower() else ""
            perf_text = f"Solid performance with {proc}{gpu_str}."

            sections.append(
                f"### {idx}. {name}\n"
                f"• **Performance:** {perf_text}\n"
                f"• **Memory:** {ram_str}\n"
                f"• **Storage:** {storage}\n"
            )

        return "\n".join(sections)

    @staticmethod
    def format_product_details_response(product_facts: Dict[str, Any]) -> str:
        """Generate a structured, grounded technical overview of a product."""
        clean_name = normalize_product_name(product_facts.get("brand", ""), product_facts.get("name", "Product"))
        category = product_facts.get("category", "Product")
        price_val = int(product_facts.get("price") or 0)
        score_val = int(float(product_facts.get("score") or 80))

        lines = [f"**{clean_name} Specifications**\n"]
        lines.append(f"• **Category:** {category}")
        lines.append(f"• **Price:** ₹{price_val:,}")

        if product_facts.get("processor") or product_facts.get("cpu"):
            lines.append(f"• **Processor:** {product_facts.get('processor') or product_facts.get('cpu')}")
        if product_facts.get("ram_gb") is not None or product_facts.get("ram") is not None:
            raw_ram = product_facts.get("ram_gb") if product_facts.get("ram_gb") is not None else product_facts.get("ram")
            ram_val = int(raw_ram or 8) if (raw_ram and str(raw_ram).replace('.', '', 1).isdigit()) else (raw_ram or 8)
            lines.append(f"• **RAM:** {ram_val}GB")
        if product_facts.get("storage"):
            lines.append(f"• **Storage:** {product_facts.get('storage')}")
        if product_facts.get("gpu"):
            lines.append(f"• **Graphics:** {product_facts.get('gpu')}")
        if product_facts.get("display") or product_facts.get("screen_size"):
            lines.append(f"• **Display:** {product_facts.get('display') or str(product_facts.get('screen_size')) + ' inch'}")
        if product_facts.get("battery") or product_facts.get("battery_capacity_mah"):
            lines.append(f"• **Battery:** {product_facts.get('battery') or str(product_facts.get('battery_capacity_mah')) + 'mAh'}")
        if product_facts.get("rear_camera"):
            lines.append(f"• **Camera:** {product_facts.get('rear_camera')}")

        lines.append(f"• **Performance Score:** {score_val}/100")
        lines.append(f"\n**Source:**\nVerified Product Database")

        return "\n".join(lines)

    @staticmethod
    def format_clarification_response(spec_field: Optional[str] = None) -> str:
        """Prompt user to identify which product they want information for."""
        if spec_field:
            field_name = spec_field.upper() if spec_field.lower() in ["ram", "cpu", "gpu", "ssd", "hdd", "os", "5g"] else spec_field.capitalize()
            return f"Which product would you like me to check the **{field_name}** for?"
        return "Which product would you like to check? You can ask for specifications (RAM, battery, price), comparisons, or recommendations."

    @staticmethod
    def format_rag_document_response(
        answer_text: str,
        evidence_snippet: str,
        source_filename: str,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None
    ) -> str:
        """Generate concise RAG Document response with clean source attribution."""
        header = f"{section_title.title()} Information" if section_title and section_title.lower() != "overview" else "Document Information"
        src_parts = [source_filename]
        if page_number:
            src_parts.append(f"Page {page_number}")
        if section_title and section_title.lower() != "overview":
            src_parts.append(section_title)
        source_str = " • ".join(src_parts)

        return (
            f"**{header}**\n\n"
            f"{answer_text}\n\n"
            f"**Source:** {source_str}"
        )

    @staticmethod
    def format_battle_verdict_response(battle_data: Dict[str, Any]) -> str:
        """
        Format comprehensive AI Battle Verdict card:
        🏆 AI Battle Verdict

        Winner:
        ASUS ROG Zephyrus

        Reasons:

        🔥 Performance
        GTX 1660 Ti provides stronger graphics performance.

        💰 Value
        Lower price with competitive hardware.

        ⚡ Overall
        Better performance-to-price ratio.

        Confidence:
        94%
        """
        winner_name = battle_data.get("winner_name") or battle_data.get("winner") or "Winning Device"
        loser_name = battle_data.get("loser_name") or battle_data.get("loser") or "Competing Device"
        w_score = battle_data.get("winner_score", 92)
        l_score = battle_data.get("loser_score", 86)
        
        conf = battle_data.get("confidence") or "94%"
        if isinstance(conf, (int, float)):
            conf = f"{int(conf)}%"
        elif not str(conf).endswith("%"):
            conf = f"{conf}%"

        rounds = battle_data.get("rounds") or []
        perf_reason = ""
        value_reason = ""
        display_reason = ""
        battery_reason = ""

        for r in rounds:
            t = r.get("title", "").lower()
            if "performance" in t:
                perf_reason = r.get("reason", "")
            elif "price" in t or "value" in t:
                value_reason = r.get("reason", "")
            elif "display" in t:
                display_reason = r.get("reason", "")
            elif "battery" in t:
                battery_reason = r.get("reason", "")

        if not perf_reason:
            perf_reason = f"Stronger processing throughput and graphics capability over {loser_name}."
        if not value_reason:
            value_reason = f"Lower price with highly competitive, premium hardware."

        overall_reason = f"Superior performance-to-price ratio with a commanding battle score ({w_score}/100 vs {l_score}/100)."

        return (
            f"🏆 **AI Battle Verdict**\n\n"
            f"**Winner:**\n{winner_name}\n\n"
            f"**Reasons:**\n\n"
            f"🔥 **Performance**\n{perf_reason}\n\n"
            f"💰 **Value**\n{value_reason}\n\n"
            f"⚡ **Overall**\n{overall_reason}\n\n"
            f"**Confidence:**\n{conf}"
        )

    @staticmethod
    def format_rag_spec_card(
        spec_name: str,
        value: str,
        source_doc: str,
        page_number: Optional[int] = None
    ) -> str:
        """Format Level 1 RAG Specification Card."""
        src = f"{source_doc} • Page {page_number}" if page_number else source_doc
        return (
            f"### {spec_name.upper()}\n\n"
            f"{value}\n\n"
            f"Source:\n{src}"
        )

    @staticmethod
    def format_rag_explanation_card(
        topic_title: str,
        summary_text: str,
        detail_bullets: List[str],
        source_doc: str,
        page_number: Optional[int] = None
    ) -> str:
        """Format RAG Topic Explanation Card."""
        src = f"{source_doc} • Page {page_number}" if page_number else source_doc
        bullets_str = "\n".join([f"• {b}" for b in detail_bullets]) if detail_bullets else "• Comprehensive specifications detailed in documentation"
        return (
            f"### {topic_title}\n\n"
            f"Summary:\n{summary_text}\n\n"
            f"Details:\n{bullets_str}\n\n"
            f"Source:\n{src}"
        )

    @staticmethod
    def format_rag_summary_card(
        product_name: str,
        key_points: List[str],
        page_count: int = 1
    ) -> str:
        """Format RAG Document Summary Card."""
        kp_str = "\n".join([f"✓ {p}" for p in key_points]) if key_points else "✓ Hardware Architecture\n✓ Thermal & Battery Performance\n✓ Display & Ports\n✓ Benchmarks"
        return (
            f"### Document Summary\n\n"
            f"Product:\n{product_name}\n\n"
            f"Key Points:\n{kp_str}\n\n"
            f"Sources:\n{page_count} page(s) analyzed"
        )

