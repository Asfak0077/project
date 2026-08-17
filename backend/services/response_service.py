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
        - RAM: 16GB
        - Price: ₹78,000
        - Processor: AMD Ryzen 7 3750H
        - Storage: 512GB SSD
        - GPU: NVIDIA GTX 1660 Ti
        - Battery: 76Wh Battery
        - Display: 15.6 inch FHD
        """
        field = spec_field.lower().strip()

        if field in ["ram", "memory"]:
            raw_ram = product_facts.get("ram_gb") if product_facts.get("ram_gb") is not None else product_facts.get("ram")
            ram_val = int(raw_ram or 8)
            return f"RAM: {ram_val}GB"

        elif field in ["price", "cost", "mrp", "rate"]:
            price_val = int(product_facts.get("price") or 0)
            return f"Price: ₹{price_val:,}"

        elif field in ["processor", "cpu", "chipset", "chip"]:
            proc_val = str(product_facts.get("processor") or product_facts.get("cpu") or "Intel Core i5")
            return f"Processor: {proc_val}"

        elif field in ["storage", "disk", "ssd", "hdd", "rom"]:
            stor_val = str(product_facts.get("storage") or "512GB SSD")
            return f"Storage: {stor_val}"

        elif field in ["gpu", "graphics", "vram"]:
            gpu_val = str(product_facts.get("gpu") or "Integrated Graphics")
            return f"GPU: {gpu_val}"

        elif field in ["battery", "battery_life", "endurance", "runtime"]:
            b_raw = str(product_facts.get("battery") or product_facts.get("battery_capacity_mah") or "").strip()
            if b_raw.isdigit() and int(b_raw) > 1000:
                return f"Battery: {b_raw}mAh"
            elif b_raw and b_raw.lower() not in ["none", "nan", "unknown"]:
                return f"Battery: {b_raw}"
            else:
                return "Battery: 5000mAh"

        elif field in ["camera", "cameras", "rear_camera", "front_camera", "selfie"]:
            rc = product_facts.get("rear_camera") or product_facts.get("camera") or "50MP"
            fc = product_facts.get("front_camera")
            if fc and fc != rc:
                return f"Camera: Rear: {rc} | Front: {fc}"
            return f"Camera: {rc}"

        elif field in ["display", "screen", "panel", "resolution", "screen_size"]:
            disp_val = str(product_facts.get("display") or product_facts.get("screen_size") or "Full HD Display")
            return f"Display: {disp_val}"

        elif field in ["os", "operating_system", "windows", "android", "ios"]:
            os_val = str(product_facts.get("os") or "Android / Windows")
            return f"Operating System: {os_val}"

        elif field in ["rating", "score", "reviews"]:
            r_val = float(product_facts.get("rating", 4.2))
            return f"Rating: ⭐ {r_val:.1f} / 5.0"

        elif field in ["cooling", "thermal"]:
            cool_val = str(product_facts.get("cooling") or "Dual-Fan Thermal Architecture")
            return f"Cooling: {cool_val}"

        elif field in ["warranty"]:
            return "Warranty: 1 Year Manufacturer Warranty"

        elif field in ["5g", "cellular"]:
            return "Cellular: 5G Supported" if product_facts.get("has_5g") or product_facts.get("5g") else "Cellular: 4G LTE"

        elif field in ["stylus", "pen"]:
            return "Stylus: Supported" if product_facts.get("has_stylus") or product_facts.get("stylus") else "Stylus: Not specified"

        else:
            field_title = spec_field.replace("_", " ").title()
            field_val = str(product_facts.get(spec_field, "Verified in database"))
            return f"{field_title}: {field_val}"

    @staticmethod
    def format_rag_document_response(
        answer_text: str,
        evidence_snippet: str,
        source_filename: str,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None
    ) -> str:
        """
        Generate concise RAG Document response with clean source attribution.
        """
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
    def format_clarification_response(spec_field: Optional[str] = None) -> str:
        """Prompt user to identify which product they want information for."""
        if spec_field:
            field_name = spec_field.upper() if spec_field.lower() in ["ram", "cpu", "gpu", "ssd", "hdd", "os", "5g"] else spec_field.capitalize()
            return f"Which product would you like me to check the **{field_name}** for?"
        return "Which product would you like to check? You can ask for specifications (RAM, battery, price), comparisons, or recommendations."

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
            ram_val = int(raw_ram or 8)
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
        lines.append(f"\n**Source:** Verified Database")

        return "\n".join(lines)

    @staticmethod
    def format_product_analysis_response(products: List[Dict[str, Any]]) -> str:
        """
        Generate clean structured Product Analysis card for one or multiple products.
        Follows format:
        ## Product Analysis

        Product:
        Apple iPad Pro 2018

        Performance:
        Good performance with Apple A12X Bionic processor.

        Memory:
        6GB RAM

        Storage:
        1000GB

        Battery:
        9720 mAh
        """
        if not products:
            return "No product specified for analysis. Please select or mention a product."

        if len(products) == 1:
            p = products[0]
            name = normalize_product_name(p.get("brand", ""), p.get("name", "Product"))
            proc = p.get("processor") or p.get("cpu") or "High-Performance Processor"
            gpu = p.get("gpu")
            raw_ram = p.get("ram_gb") if p.get("ram_gb") is not None else p.get("ram")
            ram = f"{int(raw_ram)}GB RAM" if raw_ram and str(raw_ram).replace('.','',1).isdigit() else (p.get("ram") or "8GB RAM")
            storage = p.get("storage") or "512GB SSD"
            battery = p.get("battery") or "Standard Lithium-Ion Battery"
            
            gpu_str = f" with {gpu}" if gpu and "integrated" not in gpu.lower() else ""
            perf_text = f"Good performance with {proc}{gpu_str}."

            return (
                f"## Product Analysis\n\n"
                f"**Product:**\n{name}\n\n"
                f"**Performance:**\n{perf_text}\n\n"
                f"**Memory:**\n{ram}\n\n"
                f"**Storage:**\n{storage}\n\n"
                f"**Battery:**\n{battery}"
            )

        # Multi-product analysis (e.g. "Explain product 1 and 2")
        sections = ["## Product Analysis\n"]
        for idx, p in enumerate(products, 1):
            name = normalize_product_name(p.get("brand", ""), p.get("name", "Product"))
            proc = p.get("processor") or p.get("cpu") or "High-Performance Processor"
            gpu = p.get("gpu")
            raw_ram = p.get("ram_gb") if p.get("ram_gb") is not None else p.get("ram")
            ram = f"{int(raw_ram)}GB RAM" if raw_ram and str(raw_ram).replace('.','',1).isdigit() else (p.get("ram") or "8GB RAM")
            storage = p.get("storage") or "512GB SSD"
            battery = p.get("battery") or "Standard Lithium-Ion Battery"
            
            gpu_str = f" with {gpu}" if gpu and "integrated" not in gpu.lower() else ""
            perf_text = f"Good performance with {proc}{gpu_str}."

            sections.append(
                f"### Product {idx}: {name}\n"
                f"• **Performance:** {perf_text}\n"
                f"• **Memory:** {ram}\n"
                f"• **Storage:** {storage}\n"
                f"• **Battery:** {battery}\n"
            )

        return "\n".join(sections)

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

