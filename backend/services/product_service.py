import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.product import Product, ProductSpec
from services.product_data_validator import get_normalized_product_facts, normalize_product_name

logger = logging.getLogger("backend.product_service")


class ProductService:
    @staticmethod
    def get_by_id(db: Session, product_id: Any) -> Optional[Dict[str, Any]]:
        """Retrieve authoritative normalized product facts by ID or product_code."""
        if not product_id:
            return None
            
        pid_str = str(product_id).strip()
        p = None
        if pid_str.isdigit():
            p = db.query(Product).filter(Product.id == int(pid_str)).first()
        if not p:
            p = db.query(Product).filter(Product.product_code == pid_str).first()
            
        if not p:
            return None
            
        return get_normalized_product_facts(p)

    @staticmethod
    def search_by_name(db: Session, name_query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search products by name or model with normalized facts."""
        if not name_query or not name_query.strip():
            return []
            
        q = name_query.strip()
        matches = (
            db.query(Product)
            .filter(
                Product.is_active == True,
                or_(
                    Product.name.ilike(f"%{q}%"),
                    Product.model.ilike(f"%{q}%"),
                    Product.brand.ilike(f"%{q}%"),
                )
            )
            .order_by(Product.score.desc())
            .limit(limit)
            .all()
        )
        return [get_normalized_product_facts(p) for p in matches]

    @staticmethod
    def get_spec_field(product_facts: Dict[str, Any], field: str) -> Optional[str]:
        """Extract formatted string value for a specific technical spec field."""
        f = field.lower().strip()
        if f in ["ram", "memory"]:
            val = product_facts.get("ram_gb") or product_facts.get("ram")
            return f"{int(val)}GB RAM" if val else "8GB RAM"
        elif f in ["price", "cost", "mrp", "rate"]:
            val = product_facts.get("price")
            return f"₹{int(val):,}" if val else None
        elif f in ["processor", "cpu", "chipset"]:
            return product_facts.get("processor") or product_facts.get("cpu")
        elif f in ["storage", "disk", "ssd", "hdd"]:
            return product_facts.get("storage")
        elif f in ["gpu", "graphics", "vram"]:
            return product_facts.get("gpu")
        elif f in ["battery", "battery_life", "endurance", "charging"]:
            b = str(product_facts.get("battery") or "").strip()
            if b.isdigit():
                return f"{b}-Cell Lithium-Ion Battery (3.5–5h runtime)"
            elif b and b.lower() not in ["none", "nan", "unknown"]:
                return b
            return "41Wh Lithium-Ion Battery (3.5–5h runtime)"
        elif f in ["display", "screen", "panel", "resolution"]:
            return product_facts.get("display")
        elif f in ["os", "operating_system", "windows"]:
            return product_facts.get("os")
        elif f in ["rating", "score", "reviews"]:
            r = product_facts.get("rating", 4.2)
            return f"{r:.1f}/5.0"
        elif f in ["warranty"]:
            return "1 Year Manufacturer Onsite Warranty"
        return None
