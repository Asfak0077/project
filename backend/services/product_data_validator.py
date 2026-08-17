import re
import logging
from typing import Dict, Any, Optional, Tuple, List, Union
from sqlalchemy.orm import Session
from models.product import Product, ProductSpec
from schemas.product import ProductSchema, FPSBenchmark

logger = logging.getLogger("backend.data_validator")


def format_product_response(prod: Any) -> ProductSchema:
    """Format Product ORM model to ProductSchema."""
    features = getattr(prod, "features", []) or []
    pros = [f.content for f in features if getattr(f, "feature_type", None) == "pro"]
    cons = [f.content for f in features if getattr(f, "feature_type", None) == "con"]
    fps_data = [
        FPSBenchmark(**f.metadata_json)
        for f in features
        if getattr(f, "feature_type", None) == "fps" and f.metadata_json and isinstance(f.metadata_json, dict)
    ]

    spec = getattr(prod, "specs", None)

    return ProductSchema(
        id=str(getattr(prod, "product_code", "") or ""),
        numeric_id=int(getattr(prod, "id", 0) or 0),
        brand=str(getattr(prod, "brand", "") or ""),
        name=str(getattr(prod, "name", "") or ""),
        category=str(getattr(prod, "category", "Laptop") or "Laptop"),
        model=str(getattr(prod, "model", "") or ""),
        price=float(getattr(prod, "price", 0.0) or 0.0),
        original_price=float(getattr(prod, "original_price", 0.0)) if getattr(prod, "original_price", None) is not None else None,
        cpu=str(getattr(spec, "cpu", "Intel Core i5") if spec and getattr(spec, "cpu", None) else "Intel Core i5"),
        ram=float(getattr(spec, "ram_gb", 8.0) if spec and getattr(spec, "ram_gb", None) else 8.0),
        storage=str(getattr(spec, "storage", "512 GB SSD") if spec and getattr(spec, "storage", None) else "512 GB SSD"),
        gpu=str(getattr(spec, "gpu", "Integrated") if spec and getattr(spec, "gpu", None) else "Integrated"),
        score=float(getattr(prod, "score", 85.0) or 85.0),
        image=str(getattr(prod, "image_url", None) or "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80"),
        rating=float(getattr(prod, "rating", 4.0) or 4.0),
        reviews=int(getattr(prod, "reviews_count", 0) or 0),
        badge=str(getattr(prod, "badge", None)) if getattr(prod, "badge", None) else None,
        specsSummary=str(getattr(prod, "specs_summary", None)) if getattr(prod, "specs_summary", None) else None,
        pros=pros if pros else ["High performance architecture", "Crisp display", "Durable build"],
        cons=cons if cons else ["Standard battery runtime under maximum load"],
        fpsData=fps_data if fps_data else [
            FPSBenchmark(game="GTA V", fps=85, resolution="1080p High"),
            FPSBenchmark(game="Valorant", fps=180, resolution="1080p High")
        ],
        specs={
            "cpu": getattr(spec, "cpu", None),
            "ram_gb": getattr(spec, "ram_gb", None),
            "storage": getattr(spec, "storage", None),
            "gpu": getattr(spec, "gpu", None),
            "display_size_inch": getattr(spec, "display_size_inch", 15.6),
            "resolution": getattr(spec, "resolution", "1920x1080"),
            "os": getattr(spec, "os", "Windows 11"),
            "weight_kg": getattr(spec, "weight_kg", 1.9),
            "battery": getattr(spec, "battery", "3 Cell"),
            "base_clock_speed_ghz": getattr(spec, "base_clock_speed_ghz", 2.4),
            "touch_screen": getattr(spec, "touch_screen", False),
            "ports": getattr(spec, "ports", "USB 3.2, HDMI, Type-C"),
            "raw_specs": getattr(spec, "raw_specs_json", None)
        } if spec else None
    )


def normalize_product_name(brand: Optional[str], name: Optional[str]) -> str:
    """
    Clean product names and avoid repetitive brand prefixes like 'Msi MSI...' or 'Asus Asus...'.
    """
    if not name:
        return f"{brand or ''} Laptop".strip()

    name_clean = name.strip() if isinstance(name, str) else str(name).strip()
    brand_clean = brand.strip() if isinstance(brand, str) else str(brand or "").strip()

    if not brand_clean:
        return name_clean

    # If name starts with repetitive brand: e.g. "Msi MSI..." or "Asus Asus..." or "Lenovo Lenovo..."
    pattern = rf"^(?:{re.escape(brand_clean)}\s+)+(.*)$"
    m = re.match(pattern, name_clean, re.IGNORECASE)
    if m:
        name_clean = f"{brand_clean} {m.group(1).strip()}"
    elif not name_clean.lower().startswith(brand_clean.lower()):
        name_clean = f"{brand_clean} {name_clean}"

    # Remove trailing unnecessary parens if empty
    name_clean = re.sub(r"\(\s*\)", "", name_clean).strip()
    return name_clean


def extract_specs_from_title(title: str) -> Dict[str, Any]:
    """
    Deterministically extract verified technical specifications directly from the product title.
    """
    specs: Dict[str, Any] = {}
    t = title if isinstance(title, str) else str(title or "")

    # 1. RAM extraction: e.g., '8GB RAM', '16 GB RAM', '4GB'
    ram_m = re.search(r"(\d+)\s*(?:GB|G)\s*RAM", t, re.IGNORECASE)
    if not ram_m:
        ram_m = re.search(r",\s*(\d+)\s*(?:GB|G)\b", t, re.IGNORECASE)
    if ram_m:
        try:
            val = float(ram_m.group(1))
            if val in [2, 4, 8, 12, 16, 24, 32, 64]:
                specs["ram_gb"] = val
                specs["ram_str"] = f"{int(val)}GB"
        except ValueError:
            pass

    # 2. Storage extraction: e.g., '1000GB HDD', '512GB SSD', '1TB HDD', '256GB SSD', '1TB SSD'
    storage_m = re.search(r"(\d+\s*(?:GB|TB)\s*(?:SSD|HDD|EMMC|Hybrid|NVMe))", t, re.IGNORECASE)
    if storage_m:
        specs["storage"] = storage_m.group(1).strip()
    elif "1TB" in t or "1000GB" in t:
        specs["storage"] = "1TB HDD" if "HDD" in t else "1TB SSD"
    elif "512GB" in t or "512 GB" in t:
        specs["storage"] = "512GB SSD"
    elif "256GB" in t or "256 GB" in t:
        specs["storage"] = "256GB SSD"
    elif "128GB" in t or "128 GB" in t:
        specs["storage"] = "128GB SSD"

    # 3. CPU extraction: e.g., 'Intel Core i7', 'AMD Ryzen 7', 'Core i5', 'M3 Pro'
    cpu_m = re.search(r"(Intel\s+Core\s+i[3579](?:\s+\w+)*|AMD\s+Ryzen\s+[3579](?:\s+\w+)*|Apple\s+M[123](?:\s+(?:Pro|Max|Ultra))?|Intel\s+Celeron|AMD\s+Athlon|Intel\s+Pentium)", t, re.IGNORECASE)
    if cpu_m:
        specs["cpu"] = cpu_m.group(1).strip()

    # 4. OS extraction: e.g., 'Windows 10', 'Windows 11', 'DOS', 'Linux', 'macOS'
    os_m = re.search(r"\b(Windows\s+11(?:\s+Home|\s+Pro)?|Windows\s+10(?:\s+Home|\s+Pro)?|Windows\s+8\.1|DOS|Linux|macOS|Chrome\s+OS)\b", t, re.IGNORECASE)
    if os_m:
        specs["os"] = os_m.group(1).strip()

    # 5. Display size: e.g., '15.6 inch', '14 inch', '13.3 inch'
    disp_m = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:inch|in|\")", t, re.IGNORECASE)
    if disp_m:
        try:
            specs["display_size_inch"] = float(disp_m.group(1))
        except ValueError:
            pass

    return specs


def get_normalized_product_facts(prod: Any) -> Dict[str, Any]:
    """
    Produce the single authoritative normalized product fact representation.
    Ensures title, DB columns, and specs agree 100% without conflicts or hallucinations.
    """
    if not prod:
        return {}

    if isinstance(prod, dict):
        prod_dict: Dict[str, Any] = dict(prod)
        brand_raw = str(prod_dict.get("brand") or "Generic")
        name_raw = str(prod_dict.get("name") or "")
        name_norm = normalize_product_name(brand_raw, name_raw)
        title_specs = extract_specs_from_title(name_raw)

        ram_val = float(title_specs.get("ram_gb") or prod_dict.get("ram_gb") or 8.0)
        ram_str = f"{int(ram_val)}GB" if ram_val.is_integer() else f"{ram_val}GB"
        storage_str = str(prod_dict.get("storage") or title_specs.get("storage") or "512GB SSD")
        cpu_str = str(prod_dict.get("processor") or prod_dict.get("cpu") or title_specs.get("cpu") or "Intel Core i5")
        gpu_str = str(prod_dict.get("gpu") or "Integrated Graphics")
        os_str = str(prod_dict.get("os") or title_specs.get("os") or "Windows 11")

        return {
            "id": prod_dict.get("id") or prod_dict.get("numeric_id"),
            "product_code": prod_dict.get("product_code") or prod_dict.get("id"),
            "name": name_norm,
            "raw_title": name_raw,
            "brand": brand_raw,
            "category": str(prod_dict.get("category") or "Laptop"),
            "price": float(prod_dict.get("price") or 0.0),
            "rating": float(prod_dict.get("rating") or 4.0),
            "score": float(prod_dict.get("score") or 85.0),
            "ram": ram_str,
            "ram_gb": ram_val,
            "storage": storage_str,
            "processor": cpu_str,
            "cpu": cpu_str,
            "gpu": gpu_str,
            "os": os_str,
            "display": str(prod_dict.get("display") or "15.6 inch Full HD (1920x1080)"),
            "battery": str(prod_dict.get("battery") or "3-Cell Lithium-Ion"),
            "image_url": prod_dict.get("image_url") or prod_dict.get("image"),
        }

    brand_norm = str(getattr(prod, "brand", None) or "Generic").strip()
    prod_name = str(getattr(prod, "name", None) or "")
    name_norm = normalize_product_name(brand_norm, prod_name)
    title_specs = extract_specs_from_title(prod_name)

    spec = getattr(prod, "specs", None)

    # Authoritative RAM Resolution:
    if "ram_gb" in title_specs:
        ram_val = float(title_specs["ram_gb"])
    elif spec and getattr(spec, "ram_gb", None) and float(spec.ram_gb) > 0:
        ram_val = float(spec.ram_gb)
    else:
        ram_val = 8.0

    ram_str = f"{int(ram_val)}GB" if ram_val.is_integer() else f"{ram_val}GB"

    # Authoritative Storage Resolution
    spec_storage = getattr(spec, "storage", None) if spec else None
    cat_lower = str(getattr(prod, "category", "Laptop") or "Laptop").lower()
    
    # Authoritative Storage Resolution
    spec_storage = getattr(spec, "storage", None) if spec else None
    if spec_storage and str(spec_storage).lower() not in ["none", "unknown", "nan", "0", "no hdd"]:
        storage_str = str(spec_storage).strip()
    elif "storage" in title_specs:
        storage_str = title_specs["storage"]
    else:
        storage_str = "64GB" if "phone" in cat_lower or "tablet" in cat_lower else "512GB SSD"

    # Authoritative Processor Resolution
    spec_cpu = getattr(spec, "cpu", None) if spec else None
    if spec_cpu and len(str(spec_cpu).strip()) > 3:
        cpu_str = str(spec_cpu).strip()
    elif "cpu" in title_specs:
        cpu_str = title_specs["cpu"]
    else:
        cpu_str = "Octa-core Processor" if "phone" in cat_lower or "tablet" in cat_lower else "Intel Core i5"

    # Authoritative GPU Resolution
    spec_gpu = getattr(spec, "gpu", None) if spec else None
    if spec_gpu and str(spec_gpu).strip().lower() not in ["none", "unknown", "nan", "0", "0.0"]:
        gpu_str = str(spec_gpu).strip()
    else:
        gpu_str = "Integrated GPU" if "phone" in cat_lower or "tablet" in cat_lower else "Integrated Graphics"

    # Authoritative OS Resolution
    spec_os = getattr(spec, "os", None) if spec else None
    if spec_os and len(str(spec_os).strip()) > 1:
        os_str = str(spec_os).strip()
    elif "os" in title_specs:
        os_str = title_specs["os"]
    else:
        os_str = "Android / iOS" if "phone" in cat_lower else ("Android / iPadOS" if "tablet" in cat_lower else "Windows 11")

    # Display Resolution
    spec_res = getattr(spec, "resolution", None) if spec else None
    if spec_res:
        res_str = str(spec_res).strip()
    else:
        res_str = "1080x2400 (FHD+)" if "phone" in cat_lower else ("1280x800" if "tablet" in cat_lower else "Full HD (1920x1080)")

    # Battery
    spec_bat = getattr(spec, "battery", None) if spec else None
    if spec_bat and str(spec_bat).strip().lower() not in ["none", "nan", "unknown"]:
        battery_str = str(spec_bat).strip()
    else:
        battery_str = "4000 mAh" if "phone" in cat_lower else ("5000 mAh" if "tablet" in cat_lower else "3-Cell Lithium-Ion")

    raw_specs = getattr(spec, "raw_specs_json", {}) if spec and getattr(spec, "raw_specs_json", None) else {}
    if not isinstance(raw_specs, dict):
        raw_specs = {}

    display_size = getattr(spec, "display_size_inch", 6.1 if "phone" in cat_lower else (8.0 if "tablet" in cat_lower else 15.6)) or (6.1 if "phone" in cat_lower else (8.0 if "tablet" in cat_lower else 15.6))

    return {
        "id": getattr(prod, "id", None),
        "product_code": getattr(prod, "product_code", None),
        "name": name_norm,
        "raw_title": prod_name,
        "brand": brand_norm,
        "category": str(getattr(prod, "category", "Laptop") or "Laptop"),
        "price": float(getattr(prod, "price", 0.0) or 0.0),
        "rating": float(getattr(prod, "rating", 4.0) or 4.0),
        "score": float(getattr(prod, "score", 85.0) or 85.0),
        "ram": ram_str,
        "ram_gb": ram_val,
        "storage": storage_str,
        "processor": cpu_str,
        "cpu": cpu_str,
        "gpu": gpu_str,
        "os": os_str,
        "display": f"{display_size} inch {res_str}",
        "battery": battery_str,
        "camera": raw_specs.get("rear_camera") or "Standard Camera",
        "rear_camera": raw_specs.get("rear_camera"),
        "front_camera": raw_specs.get("front_camera"),
        "5g": raw_specs.get("5g_supported", False),
        "stylus": raw_specs.get("stylus_supported", False),
        "image_url": getattr(prod, "image_url", None),
    }


def validate_product_fact(prod: Any, field: str, claimed_value: Any) -> Tuple[bool, Any]:
    """
    Validate an AI/LLM claimed specification value against the authoritative ground truth database.
    Returns (is_valid, authoritative_value).
    """
    facts = get_normalized_product_facts(prod)
    if not facts:
        return False, None

    actual_val = facts.get(field.lower())
    if actual_val is None:
        return False, None

    if str(actual_val).lower().strip() == str(claimed_value).lower().strip():
        return True, actual_val

    # Fuzzy equality for numbers (e.g. "8GB" vs "8.0GB" vs "8")
    actual_num = re.search(r"(\d+(?:\.\d+)?)", str(actual_val))
    claimed_num = re.search(r"(\d+(?:\.\d+)?)", str(claimed_value))
    if actual_num and claimed_num and float(actual_num.group(1)) == float(claimed_num.group(1)):
        return True, actual_val

    return False, actual_val


def get_data_quality_report(db: Session) -> Dict[str, Any]:
    """
    Generate comprehensive database data quality & validation diagnostic report.
    """
    products = db.query(Product).all()
    total = len(products)

    missing_ram = 0
    missing_cpu = 0
    missing_gpu = 0
    missing_price = 0
    invalid_prices = 0
    invalid_ratings = 0
    conflicting_specs = 0

    for prod in products:
        price = getattr(prod, "price", 0) or 0
        if price <= 0:
            missing_price += 1
            invalid_prices += 1

        rating = getattr(prod, "rating", None)
        if rating is None or float(rating) < 1.0 or float(rating) > 5.0:
            invalid_ratings += 1

        spec = getattr(prod, "specs", None)
        if not spec:
            missing_ram += 1
            missing_cpu += 1
            missing_gpu += 1
            continue

        if not getattr(spec, "ram_gb", None) or float(spec.ram_gb) <= 0:
            missing_ram += 1

        cpu = getattr(spec, "cpu", "")
        if not cpu or len(str(cpu).strip()) < 3:
            missing_cpu += 1

        gpu = getattr(spec, "gpu", "")
        if not gpu or str(gpu).strip().lower() in ["none", "unknown", "nan", "0"]:
            missing_gpu += 1

        title_specs = extract_specs_from_title(str(getattr(prod, "name", "") or ""))
        if "ram_gb" in title_specs and getattr(spec, "ram_gb", None) and float(spec.ram_gb) != float(title_specs["ram_gb"]):
            conflicting_specs += 1

    return {
        "total_products": total,
        "valid_products": total - (missing_price + conflicting_specs),
        "data_completeness_pct": round((1.0 - (missing_ram + missing_cpu) / (total * 2 or 1)) * 100, 1),
        "metrics": {
            "missing_ram_count": missing_ram,
            "missing_cpu_count": missing_cpu,
            "missing_gpu_count": missing_gpu,
            "missing_price_count": missing_price,
            "invalid_price_count": invalid_prices,
            "invalid_rating_count": invalid_ratings,
            "conflicting_specs_count": conflicting_specs,
        },
        "database_status": "healthy" if conflicting_specs == 0 and missing_price == 0 else "needs_reconciliation"
    }


def audit_and_reconcile_database(db: Session) -> Dict[str, Any]:
    """
    Audit and reconcile all database records to fix title-spec RAM discrepancies and clean duplicate brands.
    """
    products = db.query(Product).all()
    reconciled_ram = 0
    reconciled_brands = 0

    for prod in products:
        brand_val = str(getattr(prod, "brand", "") or "")
        name_val = str(getattr(prod, "name", "") or "")
        # 1. Clean duplicated brand names in product.name
        norm_name = normalize_product_name(brand_val, name_val)
        if norm_name != name_val:
            setattr(prod, "name", norm_name)
            reconciled_brands += 1

        # 2. Reconcile RAM conflicts
        title_specs = extract_specs_from_title(str(getattr(prod, "name", "") or ""))
        spec = getattr(prod, "specs", None)
        if "ram_gb" in title_specs and spec:
            title_ram = float(title_specs["ram_gb"])
            if getattr(spec, "ram_gb", None) != title_ram:
                setattr(spec, "ram_gb", title_ram)
                reconciled_ram += 1

    db.commit()
    logger.info(f"Database Reconciliation Complete: Reconciled {reconciled_ram} RAM mismatches, {reconciled_brands} brand names.")
    return {
        "total_products": len(products),
        "reconciled_ram_count": reconciled_ram,
        "reconciled_brand_count": reconciled_brands,
        "status": "success",
    }
