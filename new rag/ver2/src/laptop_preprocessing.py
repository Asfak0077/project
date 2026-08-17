from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "optimized_laptops.csv"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "processed" / "laptop_rag_corpus.json"
)
DEFAULT_CLEANED_OUTPUT = (
    PROJECT_ROOT / "data" / "processed" / "cleaned_laptops.csv"
)
DEFAULT_REPORT_OUTPUT = (
    PROJECT_ROOT / "data" / "processed" / "data_quality_report.json"
)


# ============================================================
# COLUMN DEFINITIONS
# ============================================================

COLUMN_ALIASES = {
    "brand": ["Brand", "brand"],
    "model": ["Model", "model"],
    "company": ["Company", "company"],
    "model_number": ["Model Number", "model_number", "Model_Number"],
    "product_name": ["Product Name", "product_name", "Product_Name"],
    "processor": ["Processor", "processor"],
    "graphics_processor": [
        "Graphics Processor",
        "graphics_processor",
        "Graphics_Processor",
    ],
    "dedicated_graphics": [
        "Dedicated Graphics",
        "dedicated_graphics",
        "Dedicated_Graphics",
    ],
    "operating_system": [
        "Operating system",
        "Operating System",
        "operating_system",
    ],
    "hard_disk": ["Hard disk", "Hard Disk", "hard_disk"],
    "ssd": ["SSD", "ssd"],
    "ram_gb": ["RAM_GB", "RAM", "ram_gb"],
    "screen_size_inch": [
        "Screen_Size_inch",
        "Screen Size",
        "screen_size_inch",
    ],
    "base_clock_speed": [
        "Base_Clock_Speed_GHz",
        "Base Clock Speed",
        "base_clock_speed_ghz",
    ],
    "resolution": ["Resolution", "resolution"],
    "weight_kg": ["Weight (kg)", "Weight", "weight_kg"],
    "dimensions_mm": ["Dimensions (mm)", "Dimensions", "dimensions_mm"],
    "bluetooth": ["Bluetooth version", "Bluetooth", "bluetooth_version"],
    "usb_count": ["Number of USB Ports", "USB Count", "number_of_usb_ports"],
    "usb_ports": ["USB Ports", "usb_ports"],
    "series": ["Series", "series"],
    "touch_screen": ["Touch Screen", "touch_screen"],
    "fingerprint": [
        "Finger Print Sensor",
        "Fingerprint Sensor",
        "fingerprint_sensor",
    ],
    "wifi": [
        "Wi-Fi standards supported",
        "WiFi",
        "wifi",
        "Wi-Fi",
    ],
    "cache": ["Cache", "cache"],
    "battery_cell": ["Battery Cell", "Battery", "battery_cell"],
    "colour": ["Colours", "Color", "Colour", "Colours"],
    "internal_mic": ["Internal Mic", "internal_mic"],
    "touchpad": ["Touchpad", "touchpad"],
    "pointer_device": ["Pointer Device", "pointer_device"],
    "mic_in": ["Mic In", "mic_in"],
    "speakers": ["Speakers", "speakers"],
    "multi_card_slot": ["Multi Card Slot", "multi_card_slot"],
    "rj45": ["RJ45 (LAN)", "RJ45", "rj45_lan"],
    "hdmi": ["HDMI Port", "HDMI", "hdmi_port"],
    "ethernet": ["Ethernet", "ethernet"],
    "price": ["Price_Clean", "Price", "price_inr"],
    "total_ratings": ["Total_Ratings", "Total Ratings", "total_ratings"],
    "rating_1": ["1 stars", "1 star"],
    "rating_2": ["2 stars", "2 star"],
    "rating_3": ["3 stars", "3 star"],
    "rating_4": ["4 stars", "4 star"],
    "rating_5": ["5 stars", "5 star"],
}


# ============================================================
# VALUES CONSIDERED UNKNOWN
# ============================================================

UNKNOWN_VALUES = {
    "",
    "unknown",
    "unk",
    "n/a",
    "na",
    "none",
    "null",
    "nan",
    "-",
    "--",
    "not available",
    "not applicable",
}


# ============================================================
# GENERIC HELPERS
# ============================================================

def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    text = str(value).strip().lower()
    return text in UNKNOWN_VALUES

def clean_text(value: Any) -> Optional[str]:
    if is_missing(value):
        return None
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else None

def safe_float(value: Any) -> Optional[float]:
    if is_missing(value):
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        try:
            number = float(value)
            return number if pd.notna(number) else None
        except (TypeError, ValueError):
            return None
    text = clean_text(value)
    if text is None:
        return None
    text = text.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if match is None:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None

def safe_int(value: Any) -> Optional[int]:
    number = safe_float(value)
    if number is None:
        return None
    return int(round(number))

def safe_bool(value: Any) -> Optional[bool]:
    if is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    number = safe_float(value)
    if number is not None:
        if number == 1:
            return True
        if number == 0:
            return False
    text = clean_text(value)
    if text is None:
        return None
    text = text.lower()
    if text in {"yes", "true", "y", "present", "supported"}:
        return True
    if text in {"no", "false", "n", "absent", "not supported"}:
        return False
    return None

def json_safe(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value

def clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for key, value in metadata.items():
        value = json_safe(value)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        cleaned[key] = value
    return cleaned


# ============================================================
# COLUMN RESOLUTION
# ============================================================

def resolve_columns(df: pd.DataFrame) -> Dict[str, str]:
    actual_columns = {str(column).strip(): column for column in df.columns}
    resolved = {}
    for canonical_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in actual_columns:
                resolved[canonical_name] = actual_columns[alias]
                break
    return resolved

def get_value(
    row: pd.Series,
    columns: Dict[str, str],
    canonical_name: str,
) -> Any:
    source_column = columns.get(canonical_name)
    if source_column is None:
        return None
    return row.get(source_column)


# ============================================================
# NORMALIZATION & OPTIMIZATION
# ============================================================

def normalize_price(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None or number < 0:
        return None
    return round(number, 2)

def normalize_ram(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number <= 0 or number > 512:
        return None
    return float(number)

# OPTIMIZATION: Extract RAM directly from Product Title
def normalize_ram_from_title(title: Optional[str]) -> Optional[float]:
    text = clean_text(title)
    if text is None:
        return None
    match = re.search(r"\b(\d+)\s*(?:gb|g)?\s*ram\b", text, re.IGNORECASE)
    if match:
        return normalize_ram(match.group(1))
    return None

def normalize_screen_size(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number < 8 or number > 30:
        return None
    return round(number, 1)

def normalize_weight(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number <= 0 or number > 15:
        return None
    return round(number, 2)

def normalize_clock_speed(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number > 20:
        number = number / 1000.0
    if number <= 0 or number > 10:
        return None
    return round(number, 2)

def normalize_bluetooth(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number <= 0 or number > 10:
        return None
    return round(number, 1)

# OPTIMIZATION: Verify Dedicated Graphics Logic
def sanitize_dedicated_graphics(
    dedicated_graphics: Optional[bool],
    price_inr: Optional[float],
    processor: Optional[str],
) -> Optional[bool]:
    if dedicated_graphics is None:
        return None
    if not dedicated_graphics:
        return False
    # GPU Sanity Check: Budget laptops < 25K cannot have a dedicated GPU
    if price_inr is not None and price_inr < 25000:
        return False
    # GPU Sanity Check: Celeron/Pentium/Atom processors don't pair with GPUs
    proc_lower = str(processor or "").lower()
    if any(p in proc_lower for p in ["atom", "celeron", "pentium", "apu"]):
        if price_inr is None or price_inr < 35000:
            return False
    return dedicated_graphics


# ============================================================
# STORAGE
# ============================================================

def parse_storage_gb(value: Any) -> Optional[float]:
    text = clean_text(value)
    if text is None:
        return None
    text = text.lower().replace(",", "")
    matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*(tb|gb)",
        text,
        flags=re.IGNORECASE,
    )
    if not matches:
        return None
    capacities = []
    for number_text, unit in matches:
        number = float(number_text)
        if unit.lower() == "tb":
            number *= 1024
        capacities.append(number)
    if not capacities:
        return None
    return round(sum(capacities), 2)

# OPTIMIZATION: Extract Storage directly from Product Title
def normalize_storage_from_title(title: Optional[str]) -> Optional[float]:
    text = clean_text(title)
    if text is None:
        return None
    match = re.search(r"\b(\d+)\s*(tb|gb)\s*(hdd|ssd|emmc|nvme|flash|hybrid)?\b", text, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "tb":
            val *= 1024
        return round(val, 2)
    return None

def infer_storage_type(
    hard_disk: Optional[str],
    product_name: Optional[str],
) -> Optional[str]:
    combined = " ".join(
        item.lower()
        for item in [hard_disk, product_name]
        if item
    )
    if "nvme" in combined:
        return "NVMe SSD"
    if "ssd" in combined:
        return "SSD"
    if "hdd" in combined:
        return "HDD"
    return None


# ============================================================
# DISPLAY
# ============================================================

def parse_resolution(value: Any) -> Dict[str, Any]:
    text = clean_text(value)
    result = {
        "resolution": text,
        "resolution_width": None,
        "resolution_height": None,
        "resolution_pixels": None,
    }
    if text is None:
        return result
    match = re.search(
        r"(\d{3,5})\s*[x×]\s*(\d{3,5})",
        text.lower(),
    )
    if match is None:
        return result
    width = int(match.group(1))
    height = int(match.group(2))
    result["resolution_width"] = width
    result["resolution_height"] = height
    result["resolution_pixels"] = width * height
    return result


# ============================================================
# DIMENSIONS & PORTS & RATINGS
# ============================================================

def parse_dimensions(value: Any) -> Dict[str, Any]:
    text = clean_text(value)
    result = {
        "dimensions": text,
        "length_mm": None,
        "width_mm": None,
        "thickness_mm": None,
    }
    if text is None:
        return result
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if len(numbers) < 3:
        return result
    result["length_mm"] = round(float(numbers[0]), 2)
    result["width_mm"] = round(float(numbers[1]), 2)
    result["thickness_mm"] = round(float(numbers[2]), 2)
    return result


def parse_usb_ports(value: Any) -> Dict[str, Any]:
    text = clean_text(value)
    result = {
        "usb_port_description": text,
        "usb_2_count": 0,
        "usb_3_count": 0,
        "usb_total_parsed": None,
    }
    if text is None:
        return result
    patterns = re.findall(
        r"(\d+)\s*x?\s*USB\s*([0-9.]+)",
        text,
        flags=re.IGNORECASE,
    )
    for count_text, version_text in patterns:
        count = int(count_text)
        try:
            version = float(version_text)
        except ValueError:
            continue
        if version < 3:
            result["usb_2_count"] += count
        else:
            result["usb_3_count"] += count
    total = result["usb_2_count"] + result["usb_3_count"]
    result["usb_total_parsed"] = total if total > 0 else None
    return result


def calculate_rating(
    row: pd.Series,
    columns: Dict[str, str],
) -> Dict[str, Any]:
    star_values = {}
    for star in range(1, 6):
        canonical = "rating_" + str(star)
        value = safe_float(get_value(row, columns, canonical))
        star_values[star] = value if value is not None else 0.0

    total = sum(star_values.values())
    rating_score = None

    if total > 0:
        rating_score = round(
            sum(star * percentage for star, percentage in star_values.items()) / total,
            2,
        )

    total_ratings = safe_int(get_value(row, columns, "total_ratings"))
    return {
        "rating_score": rating_score,
        "total_ratings": total_ratings,
        "rating_1_pct": star_values[1],
        "rating_2_pct": star_values[2],
        "rating_3_pct": star_values[3],
        "rating_4_pct": star_values[4],
        "rating_5_pct": star_values[5],
    }


# ============================================================
# PRODUCT CLASSIFICATION
# ============================================================

NON_LAPTOP_KEYWORDS = (
    "xbox", "playstation", "smartphone", "mobile phone", "tablet", "ipad", "iphone",
)
LAPTOP_KEYWORDS = (
    "laptop", "notebook", "chromebook", "ultrabook",
)

def detect_product_type(
    row: pd.Series,
    columns: Dict[str, str],
) -> str:
    product_name = clean_text(get_value(row, columns, "product_name"))
    model = clean_text(get_value(row, columns, "model"))
    operating_system = clean_text(get_value(row, columns, "operating_system"))
    processor = clean_text(get_value(row, columns, "processor"))

    searchable_text = " ".join(part.lower() for part in [product_name, model] if part)

    for keyword in NON_LAPTOP_KEYWORDS:
        if keyword in searchable_text:
            return "non_laptop"

    if operating_system:
        if operating_system.lower().startswith("android"):
            return "non_laptop"

    for keyword in LAPTOP_KEYWORDS:
        if keyword in searchable_text:
            return "laptop"

    screen_size = normalize_screen_size(get_value(row, columns, "screen_size_inch"))
    hard_disk = clean_text(get_value(row, columns, "hard_disk"))
    laptop_os = False

    if operating_system:
        os_text = operating_system.lower()
        laptop_os = any(
            item in os_text for item in ("windows", "linux", "dos", "chrome os", "macos", "mac os")
        )

    signals = sum([bool(processor), screen_size is not None, bool(hard_disk), laptop_os])
    if signals >= 3:
        return "laptop"

    return "non_laptop"


# ============================================================
# PRODUCT ID
# ============================================================

def normalize_identity_text(value: Any) -> str:
    text = clean_text(value)
    if text is None:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

def generate_product_id(
    brand: Optional[str],
    model: Optional[str],
    model_number: Optional[str],
    product_name: Optional[str],
) -> str:
    identity = "|".join([
        normalize_identity_text(brand),
        normalize_identity_text(model),
        normalize_identity_text(model_number),
        normalize_identity_text(product_name),
    ])
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return "LAP_" + digest


# ============================================================
# CANONICAL PRODUCT METADATA
# ============================================================

def build_metadata(
    row: pd.Series,
    columns: Dict[str, str],
    product_id: str,
) -> Dict[str, Any]:
    
    brand = clean_text(get_value(row, columns, "brand"))
    model = clean_text(get_value(row, columns, "model"))
    model_number = clean_text(get_value(row, columns, "model_number"))
    product_name = clean_text(get_value(row, columns, "product_name"))
    processor = clean_text(get_value(row, columns, "processor"))
    hard_disk = clean_text(get_value(row, columns, "hard_disk"))

    # Baseline Parse
    price_inr = normalize_price(get_value(row, columns, "price"))
    ram_gb = normalize_ram(get_value(row, columns, "ram_gb"))
    storage_gb = parse_storage_gb(hard_disk)

    # --------------------------------------------------------
    # OPTIMIZATION: CROSS-COLUMN SANITY FIXES
    # --------------------------------------------------------
    
    # 1. RAM Mismatch: Trust the title over the column extraction
    title_ram = normalize_ram_from_title(product_name)
    if title_ram is not None and title_ram != ram_gb:
        ram_gb = title_ram

    # 2. Storage Mismatch: Trust the title
    if storage_gb is None:
        storage_gb = parse_storage_gb(product_name)

    title_storage = normalize_storage_from_title(product_name)
    if title_storage is not None and title_storage != storage_gb:
        storage_gb = title_storage

    # 3. GPU Sanity: Revoke GPUs from budget laptops
    dedicated_graphics = safe_bool(get_value(row, columns, "dedicated_graphics"))
    dedicated_graphics = sanitize_dedicated_graphics(
        dedicated_graphics=dedicated_graphics,
        price_inr=price_inr,
        processor=processor,
    )

    # --------------------------------------------------------

    resolution_data = parse_resolution(get_value(row, columns, "resolution"))
    dimensions_data = parse_dimensions(get_value(row, columns, "dimensions_mm"))
    usb_data = parse_usb_ports(get_value(row, columns, "usb_ports"))
    ratings = calculate_rating(row, columns)

    metadata = {
        "product_id": product_id,
        "brand": brand,
        "model": model,
        "model_number": model_number,
        "company": clean_text(get_value(row, columns, "company")),
        "product_name": product_name,
        "series": clean_text(get_value(row, columns, "series")),

        "processor": processor,
        "graphics_processor": clean_text(get_value(row, columns, "graphics_processor")),
        "dedicated_graphics": dedicated_graphics,
        "ram_gb": ram_gb,
        "base_clock_ghz": normalize_clock_speed(get_value(row, columns, "base_clock_speed")),
        "cache": clean_text(get_value(row, columns, "cache")),

        "storage_description": hard_disk,
        "storage_gb": storage_gb,
        "storage_type": infer_storage_type(hard_disk, product_name),

        "screen_size_inch": normalize_screen_size(get_value(row, columns, "screen_size_inch")),
        **resolution_data,

        "weight_kg": normalize_weight(get_value(row, columns, "weight_kg")),
        **dimensions_data,

        "operating_system": clean_text(get_value(row, columns, "operating_system")),
        "wifi": clean_text(get_value(row, columns, "wifi")),
        "bluetooth_version": normalize_bluetooth(get_value(row, columns, "bluetooth")),
        "number_of_usb_ports": safe_int(get_value(row, columns, "usb_count")),
        **usb_data,

        "touch_screen": safe_bool(get_value(row, columns, "touch_screen")),
        "fingerprint_sensor": safe_bool(get_value(row, columns, "fingerprint")),
        "internal_mic": clean_text(get_value(row, columns, "internal_mic")),
        "touchpad": clean_text(get_value(row, columns, "touchpad")),
        "pointer_device": clean_text(get_value(row, columns, "pointer_device")),
        "battery_cell": clean_text(get_value(row, columns, "battery_cell")),
        "colour": clean_text(get_value(row, columns, "colour")),
        "mic_in": clean_text(get_value(row, columns, "mic_in")),
        "speakers": clean_text(get_value(row, columns, "speakers")),
        "multi_card_slot": clean_text(get_value(row, columns, "multi_card_slot")),
        "rj45_lan": clean_text(get_value(row, columns, "rj45")),
        "hdmi_port": clean_text(get_value(row, columns, "hdmi")),
        "ethernet": clean_text(get_value(row, columns, "ethernet")),

        "price_inr": price_inr,
        **ratings,
    }

    return clean_metadata(metadata)


# ============================================================
# SEMANTIC DOCUMENT
# ============================================================

def add_text_field(parts: List[str], label: str, value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text:
        parts.append(label + ": " + text)

def build_document(metadata: Dict[str, Any]) -> str:
    parts: List[str] = []
    add_text_field(parts, "Brand", metadata.get("brand"))
    add_text_field(parts, "Model", metadata.get("model"))
    add_text_field(parts, "Product", metadata.get("product_name"))
    add_text_field(parts, "Processor", metadata.get("processor"))

    if metadata.get("base_clock_ghz") is not None:
        add_text_field(parts, "Base clock speed", str(metadata["base_clock_ghz"]) + " GHz")

    if metadata.get("ram_gb") is not None:
        add_text_field(parts, "RAM", str(metadata["ram_gb"]) + " GB")

    add_text_field(parts, "Graphics processor", metadata.get("graphics_processor"))

    if metadata.get("dedicated_graphics") is not None:
        add_text_field(parts, "Dedicated graphics", "Yes" if metadata["dedicated_graphics"] else "No")

    add_text_field(parts, "Storage", metadata.get("storage_description"))

    if metadata.get("storage_gb") is not None:
        add_text_field(parts, "Storage capacity", str(metadata["storage_gb"]) + " GB")

    add_text_field(parts, "Storage type", metadata.get("storage_type"))

    if metadata.get("screen_size_inch") is not None:
        add_text_field(parts, "Screen size", str(metadata["screen_size_inch"]) + " inches")

    add_text_field(parts, "Resolution", metadata.get("resolution"))
    add_text_field(parts, "Operating system", metadata.get("operating_system"))

    if metadata.get("weight_kg") is not None:
        add_text_field(parts, "Weight", str(metadata["weight_kg"]) + " kg")

    add_text_field(parts, "Wi-Fi", metadata.get("wifi"))

    if metadata.get("bluetooth_version") is not None:
        add_text_field(parts, "Bluetooth", str(metadata["bluetooth_version"]))

    add_text_field(parts, "USB ports", metadata.get("usb_port_description"))

    if metadata.get("touch_screen") is not None:
        add_text_field(parts, "Touch screen", "Yes" if metadata["touch_screen"] else "No")

    if metadata.get("fingerprint_sensor") is not None:
        add_text_field(parts, "Fingerprint sensor", "Yes" if metadata["fingerprint_sensor"] else "No")

    add_text_field(parts, "Battery", metadata.get("battery_cell"))
    add_text_field(parts, "Colour", metadata.get("colour"))

    if metadata.get("price_inr") is not None:
        add_text_field(parts, "Price", "₹" + str(int(metadata["price_inr"])))

    if metadata.get("rating_score") is not None:
        add_text_field(parts, "Rating", str(metadata["rating_score"]) + " out of 5")

    if metadata.get("total_ratings") is not None:
        add_text_field(parts, "Total ratings", str(metadata["total_ratings"]))

    return ". ".join(parts) + "."


# ============================================================
# PRODUCT DEDUPLICATION
# ============================================================

def deduplicate_products(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    seen = set()
    unique_records = []
    duplicates = 0

    for record in records:
        product_id = record["id"]
        if product_id in seen:
            duplicates += 1
            continue
        seen.add(product_id)
        unique_records.append(record)

    return unique_records, duplicates


# ============================================================
# QUALITY REPORT
# ============================================================

def build_quality_report(
    original_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    excluded_non_laptops: int,
    duplicate_products: int,
    invalid_dropped: int,
    resolved_columns: Dict[str, str],
) -> Dict[str, Any]:
    missing_values = {}
    for column in original_df.columns:
        count = int(original_df[column].isna().sum())
        if count > 0:
            missing_values[column] = count

    report = {
        "source": {
            "rows": int(len(original_df)),
            "columns": int(len(original_df.columns)),
            "column_names": [str(column) for column in original_df.columns],
        },
        "output": {
            "rows": int(len(cleaned_df)),
            "columns": int(len(cleaned_df.columns)),
        },
        "transformations": {
            "excluded_non_laptop_rows": int(excluded_non_laptops),
            "duplicate_product_records_removed": int(duplicate_products),
            "exact_duplicate_rows": int(original_df.duplicated().sum()),
            "invalid_ghost_laptops_dropped": int(invalid_dropped),
        },
        "column_mapping": {
            canonical: str(source) for canonical, source in resolved_columns.items()
        },
        "unresolved_canonical_fields": [
            canonical for canonical in COLUMN_ALIASES if canonical not in resolved_columns
        ],
        "missing_values": missing_values,
    }
    return report


# ============================================================
# MAIN PIPELINE
# ============================================================

def prepare_rag_corpus(
    input_csv: Path,
    output_json: Path,
    cleaned_csv: Path,
    report_json: Path,
    include_non_laptops: bool = False,
) -> None:
    print("=" * 72)
    print("VER2 - LAPTOP DATA PREPROCESSING (OPTIMIZED)")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. LOAD
    # --------------------------------------------------------
    if not input_csv.exists():
        raise FileNotFoundError("Input CSV does not exist: " + str(input_csv))

    print("\n[1/8] Loading dataset...")
    print("Path:", input_csv)

    df = pd.read_csv(input_csv, low_memory=False)

    if df.empty:
        raise ValueError("The input dataset is empty.")

    print(f"Loaded: {len(df)} rows x {len(df.columns)} columns")

    # --------------------------------------------------------
    # 2. RESOLVE SCHEMA
    # --------------------------------------------------------
    print("\n[2/8] Resolving schema...")
    resolved_columns = resolve_columns(df)

    required_fields = ["brand", "model", "product_name", "processor", "price"]
    missing_required = [field for field in required_fields if field not in resolved_columns]

    if missing_required:
        raise ValueError("Required fields could not be resolved: " + ", ".join(missing_required))

    print(f"Resolved canonical fields: {len(resolved_columns)} / {len(COLUMN_ALIASES)}")

    # --------------------------------------------------------
    # 3. REMOVE EXACT DUPLICATES
    # --------------------------------------------------------
    print("\n[3/8] Removing exact duplicate rows...")
    before = len(df)
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    exact_duplicates_removed = before - len(df)
    print("Exact duplicate rows removed:", exact_duplicates_removed)

    # --------------------------------------------------------
    # 4. CLASSIFY PRODUCTS
    # --------------------------------------------------------
    print("\n[4/8] Classifying products...")
    df["_product_type"] = df.apply(lambda row: detect_product_type(row, resolved_columns), axis=1)

    laptop_count = int((df["_product_type"] == "laptop").sum())
    non_laptop_count = int((df["_product_type"] == "non_laptop").sum())

    print("Laptop:", laptop_count)
    print("Non-laptop:", non_laptop_count)

    if include_non_laptops:
        working_df = df.copy()
    else:
        working_df = df[df["_product_type"] == "laptop"].copy()

    # --------------------------------------------------------
    # 5. BUILD CANONICAL PRODUCTS & ENFORCE OPTIMIZATION
    # --------------------------------------------------------
    print("\n[5/8] Building canonical product records (Applying Anti-Ghost Protocols)...")
    records = []
    invalid_dropped = 0

    for _, row in working_df.iterrows():
        brand = clean_text(get_value(row, resolved_columns, "brand"))
        model = clean_text(get_value(row, resolved_columns, "model"))
        model_number = clean_text(get_value(row, resolved_columns, "model_number"))
        product_name = clean_text(get_value(row, resolved_columns, "product_name"))

        product_id = generate_product_id(brand, model, model_number, product_name)
        metadata = build_metadata(row, resolved_columns, product_id)

        # OPTIMIZATION: Drop Ghost Laptops Missing Critical Data
        if (metadata.get("price_inr") is None or
            metadata.get("ram_gb") is None or
            metadata.get("storage_gb") is None or
            not metadata.get("product_name")):
            invalid_dropped += 1
            continue

        metadata["product_type"] = row["_product_type"]
        document = build_document(metadata)

        if not document:
            continue

        records.append({
            "id": product_id,
            "text": document,
            "metadata": metadata,
        })

    print(f"Invalid 'Ghost' records dropped: {invalid_dropped}")

    # --------------------------------------------------------
    # 6. DEDUPLICATE CANONICAL PRODUCTS
    # --------------------------------------------------------
    print("\n[6/8] Deduplicating canonical products...")
    unique_records, duplicate_products = deduplicate_products(records)
    print("Canonical records:", len(records))
    print("Duplicate product records removed:", duplicate_products)

    # --------------------------------------------------------
    # 7. SAVE
    # --------------------------------------------------------
    print("\n[7/8] Saving processed data...")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    cleaned_csv.parent.mkdir(parents=True, exist_ok=True)
    report_json.parent.mkdir(parents=True, exist_ok=True)

    with output_json.open("w", encoding="utf-8") as file:
        json.dump(unique_records, file, indent=2, ensure_ascii=False)

    cleaned_rows = []
    for record in unique_records:
        row = dict(record["metadata"])
        row["id"] = record["id"]
        row["text"] = record["text"]
        cleaned_rows.append(row)

    cleaned_df = pd.DataFrame(cleaned_rows)
    cleaned_df.to_csv(cleaned_csv, index=False)

    report = build_quality_report(
        original_df=df.drop(columns=["_product_type"], errors="ignore"),
        cleaned_df=cleaned_df,
        excluded_non_laptops=(0 if include_non_laptops else non_laptop_count),
        duplicate_products=duplicate_products,
        invalid_dropped=invalid_dropped,
        resolved_columns=resolved_columns,
    )
    report["exact_duplicate_rows_removed"] = exact_duplicates_removed

    with report_json.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    # --------------------------------------------------------
    # 8. SUMMARY
    # --------------------------------------------------------
    print("\n[8/8] Completed.")
    print("=" * 72)
    print("VER2 PREPROCESSING SUMMARY (OPTIMIZED)")
    print("=" * 72)
    print("Source rows              :", len(df))
    print("Laptop products          :", laptop_count)
    print("Excluded non-laptops     :", (0 if include_non_laptops else non_laptop_count))
    print("Invalid/Ghost drops      :", invalid_dropped)
    print("Final unique products    :", len(unique_records))
    print("Exact duplicates removed :", exact_duplicates_removed)
    print("Product duplicates       :", duplicate_products)
    print()
    print("RAG corpus               :", output_json)
    print("Cleaned dataset          :", cleaned_csv)
    print("Quality report           :", report_json)
    print("=" * 72)


# ============================================================
# CLI
# ============================================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare laptop dataset for the ver2 RAG pipeline."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to source CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Path to RAG corpus JSON.")
    parser.add_argument("--cleaned-output", type=Path, default=DEFAULT_CLEANED_OUTPUT, help="Path to cleaned CSV.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_OUTPUT, help="Path to quality report JSON.")
    parser.add_argument("--include-non-laptops", action="store_true", help="Keep non-laptop records instead of excluding them.")
    return parser.parse_args()

def main() -> None:
    args = parse_arguments()
    prepare_rag_corpus(
        input_csv=args.input,
        output_json=args.output,
        cleaned_csv=args.cleaned_output,
        report_json=args.report,
        include_non_laptops=args.include_non_laptops,
    )

if __name__ == "__main__":
    main()