import os
import re
import json
import math
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# CORRECTED: Point to the cleaned CSV from the previous step, not the raw one
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "cleaned_mobiles.csv"

# Define the processed output directory
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

# Map the outputs to the final RAG destination
OUTPUT_CSV = OUTPUT_DIR / "mobiles_rag_ready.csv"
OUTPUT_JSON = OUTPUT_DIR / "mobile_rag_corpus.json"

# Keep the audit reports routing to the processed directory
QUALITY_REPORT = OUTPUT_DIR / "data_quality_report.json"
CONFLICT_REPORT = OUTPUT_DIR / "specification_conflicts.csv"
REMOVED_REPORT = OUTPUT_DIR / "removed_rows.csv"

# If True, rows missing critical identity fields are removed.
DROP_INVALID_ROWS = True

# Critical fields required for a useful mobile-phone document.
CRITICAL_FIELDS = [
    "product_id",
    "brand",
    "model",
    "product_name"
]
# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_string(value):
    """Normalize text without destroying useful information."""

    if pd.isna(value):
        return "Unknown"

    value = str(value).strip()

    if value == "":
        return "Unknown"

    if value.lower() in {
        "nan",
        "none",
        "null",
        "n/a",
        "na",
        "-",
        "--"
    }:
        return "Unknown"

    return re.sub(r"\s+", " ", value)


def is_unknown(value):
    return clean_string(value).lower() == "unknown"


def safe_float(value):
    try:
        if pd.isna(value):
            return None

        value = str(value).strip()

        if value.lower() == "unknown":
            return None

        return float(value)

    except (ValueError, TypeError):
        return None


def clean_number(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return None

    if decimals == 0:
        return int(round(value))

    return round(value, decimals)


def format_number(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return "Unknown"

    if float(value).is_integer():
        return str(int(value))

    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def normalize_bool(value):
    """Convert common boolean representations to True/False/Unknown."""

    if pd.isna(value):
        return "Unknown"

    value = str(value).strip().lower()

    if value in {"true", "yes", "y", "1", "supported"}:
        return True

    if value in {"false", "no", "n", "0", "not supported"}:
        return False

    return "Unknown"


def bool_text(value):
    value = normalize_bool(value)

    if value is True:
        return "Yes"

    if value is False:
        return "No"

    return "Unknown"


# ============================================================
# SPECIFICATION EXTRACTION
# ============================================================

def extract_ram_from_product_name(product_name):
    """
    Extract explicit RAM from product names.

    Examples:
        (6GB RAM, 64GB) -> 6
        (4 GB RAM, 128 GB) -> 4
    """

    if is_unknown(product_name):
        return None

    patterns = [
        r"(\d+(?:\.\d+)?)\s*GB\s*RAM",
        r"(\d+(?:\.\d+)?)\s*GB\s*ram",
        r"RAM\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*GB"
    ]

    for pattern in patterns:
        match = re.search(pattern, product_name, flags=re.I)

        if match:
            return float(match.group(1))

    return None


def extract_storage_from_product_name(product_name):
    """
    Extract storage from product names.

    Priority:
        1. Explicit storage after RAM.
        2. Explicit parenthesized configuration.
        3. Standalone GB configuration where appropriate.
    """

    if is_unknown(product_name):
        return None

    # Example:
    # (6GB RAM, 64GB)
    # (4GB RAM, 128GB)
    pattern = (
        r"\(\s*\d+(?:\.\d+)?\s*GB\s*RAM\s*,\s*"
        r"(\d+(?:\.\d+)?)\s*GB\s*\)"
    )

    match = re.search(pattern, product_name, flags=re.I)

    if match:
        return float(match.group(1))

    # More flexible:
    # (6GB RAM / 128GB)
    pattern = (
        r"\d+(?:\.\d+)?\s*GB\s*RAM"
        r".{0,15}?"
        r"(\d+(?:\.\d+)?)\s*GB"
    )

    match = re.search(pattern, product_name, flags=re.I)

    if match:
        return float(match.group(1))

    # Examples:
    # Xiaomi Redmi 6A (32GB)
    # Vivo V5 (32GB)
    # If there is only one GB number and it is inside
    # parentheses, treat it as storage.
    pattern = r"\(\s*(\d+(?:\.\d+)?)\s*GB\s*\)"

    match = re.search(pattern, product_name, flags=re.I)

    if match:
        return float(match.group(1))

    return None


def extract_configuration(product_name):
    """Return RAM and storage extracted from product name."""

    ram = extract_ram_from_product_name(product_name)
    storage = extract_storage_from_product_name(product_name)

    return ram, storage


# ============================================================
# SPECIFICATION CONFLICT HANDLING
# ============================================================

def values_differ(a, b):
    if a is None or b is None:
        return False

    try:
        return not math.isclose(
            float(a),
            float(b),
            rel_tol=0.0,
            abs_tol=0.001
        )

    except (ValueError, TypeError):
        return str(a).strip().lower() != str(b).strip().lower()


def reconcile_ram_storage(df, conflicts):
    """
    Product name contains explicit configuration information.

    When structured fields disagree with explicit product-name
    specifications, product-name values are used as canonical
    values and the conflict is logged.
    """

    corrected_ram = []
    corrected_storage = []

    for index, row in df.iterrows():

        product_name = clean_string(row["product_name"])

        extracted_ram, extracted_storage = extract_configuration(
            product_name
        )

        original_ram = safe_float(row["ram_gb"])
        original_storage = safe_float(row["internal_storage_gb"])

        final_ram = original_ram
        final_storage = original_storage

        if extracted_ram is not None:

            if values_differ(original_ram, extracted_ram):

                conflicts.append({
                    "row_index": index,
                    "product_id": row["product_id"],
                    "field": "ram_gb",
                    "original_value": original_ram,
                    "extracted_value": extracted_ram,
                    "source": "product_name",
                    "action": "corrected"
                })

            final_ram = extracted_ram

        if extracted_storage is not None:

            if values_differ(original_storage, extracted_storage):

                conflicts.append({
                    "row_index": index,
                    "product_id": row["product_id"],
                    "field": "internal_storage_gb",
                    "original_value": original_storage,
                    "extracted_value": extracted_storage,
                    "source": "product_name",
                    "action": "corrected"
                })

            final_storage = extracted_storage

        corrected_ram.append(final_ram)
        corrected_storage.append(final_storage)

    df["ram_gb"] = corrected_ram
    df["internal_storage_gb"] = corrected_storage

    return df


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_processor(row):
    processor = clean_string(row["processor"])
    chipset = clean_string(row["processor_make"])

    if chipset == "Unknown":
        return processor

    return chipset


def extract_chipset_brand(chipset):
    chipset = clean_string(chipset)

    if chipset == "Unknown":
        return "Unknown"

    chipset_lower = chipset.lower()

    brands = {
        "qualcomm": "Qualcomm",
        "snapdragon": "Qualcomm",
        "mediatek": "MediaTek",
        "helio": "MediaTek",
        "samsung": "Samsung",
        "exynos": "Samsung",
        "hisilicon": "HiSilicon",
        "kirin": "HiSilicon",
        "apple": "Apple",
        "bionic": "Apple",
        "unisoc": "UNISOC",
        "spreadtrum": "UNISOC"
    }

    for key, brand in brands.items():
        if key in chipset_lower:
            return brand

    return "Unknown"


def normalize_bluetooth(value):
    """
    Convert:
        Yes, v 5.00
        Yes, v 4.20
        5.00
        No
    into:
        supported
        version
    """

    value = clean_string(value)

    if value == "Unknown":
        return False, "Unknown"

    lower = value.lower()

    if "no" in lower:
        return False, "Unknown"

    version_match = re.search(
        r"(?:v(?:ersion)?\.?\s*)?(\d+(?:\.\d+)?)",
        value,
        flags=re.I
    )

    version = "Unknown"

    if version_match:
        version = version_match.group(1)

    return True, version


def normalize_os(value):
    value = clean_string(value)

    if value == "Unknown":
        return "Unknown", "Unknown"

    match = re.search(
        r"android\s*([0-9]+(?:\.[0-9]+)*)",
        value,
        flags=re.I
    )

    if match:
        version = match.group(1)
        return "Android", version

    if "ios" in value.lower():
        match = re.search(
            r"ios\s*([0-9]+(?:\.[0-9]+)*)",
            value,
            flags=re.I
        )

        if match:
            return "iOS", match.group(1)

        return "iOS", "Unknown"

    return value, "Unknown"


def normalize_resolution(value):
    value = clean_string(value)

    if value == "Unknown":
        return "Unknown", None, None

    match = re.search(
        r"(\d+)\s*x\s*(\d+)",
        value,
        flags=re.I
    )

    if not match:
        return value, None, None

    width = int(match.group(1))
    height = int(match.group(2))

    return f"{width}x{height}", width, height


def normalize_dimensions(value):
    value = clean_string(value)

    if value == "Unknown":
        return "Unknown"

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        value
    )

    if len(numbers) >= 3:
        return (
            f"{float(numbers[0]):.2f} x "
            f"{float(numbers[1]):.2f} x "
            f"{float(numbers[2]):.2f} mm"
        )

    return value


# ============================================================
# RATING HANDLING
# ============================================================

def normalize_rating_distribution(row):
    """
    Existing columns are *_count but behave like percentages.

    Convert them into *_pct columns.
    """

    percentages = {}

    for star in range(1, 6):

        column = f"rating_{star}_count"

        value = safe_float(row[column])

        if value is None:
            percentages[f"rating_{star}_pct"] = None
        else:
            percentages[f"rating_{star}_pct"] = round(value, 2)

    return percentages


def rating_distribution_sum(row):
    values = []

    for star in range(1, 6):
        value = safe_float(
            row[f"rating_{star}_count"]
        )

        if value is not None:
            values.append(value)

    if not values:
        return None

    return round(sum(values), 2)


# ============================================================
# NUMERIC QUALITY VALIDATION
# ============================================================

def validate_numeric_ranges(df, quality):

    ranges = {
        "ram_gb": (0.25, 32),
        "internal_storage_gb": (1, 2048),
        "battery_capacity_mah": (500, 20000),
        "screen_size_inch": (2.0, 15.0),
        "rear_camera_mp": (0.1, 300),
        "front_camera_mp": (0.1, 200),
        "weight_g": (50, 500),
        "price_inr": (100, 1000000),
        "rating_score": (0, 5),
        "total_ratings": (0, 100000000)
    }

    for column, (minimum, maximum) in ranges.items():

        if column not in df.columns:
            continue

        for index, value in df[column].items():

            number = safe_float(value)

            if number is None:
                continue

            if number < minimum or number > maximum:

                quality.append({
                    "row_index": index,
                    "product_id": df.at[index, "product_id"],
                    "field": column,
                    "value": number,
                    "issue": "out_of_expected_range",
                    "action": "flagged_not_automatically_corrected"
                })


# ============================================================
# DUPLICATE / CANONICAL PRODUCT HANDLING
# ============================================================

def normalize_key_text(value):
    value = clean_string(value)

    if value == "Unknown":
        return "unknown"

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def create_product_keys(df):

    df["brand_normalized"] = (
        df["brand"]
        .apply(normalize_key_text)
    )

    df["model_normalized"] = (
        df["model"]
        .apply(normalize_key_text)
    )

    def configuration_key(row):

        brand = normalize_key_text(row["brand"])
        model = normalize_key_text(row["model"])

        ram = safe_float(row["ram_gb"])
        storage = safe_float(
            row["internal_storage_gb"]
        )

        ram_text = (
            format_number(ram)
            if ram is not None
            else "unknown"
        )

        storage_text = (
            format_number(storage)
            if storage is not None
            else "unknown"
        )

        raw = (
            f"{brand}|{model}|"
            f"{ram_text}|{storage_text}"
        )

        return hashlib.sha1(
            raw.encode("utf-8")
        ).hexdigest()[:16]

    df["canonical_product_key"] = df.apply(
        configuration_key,
        axis=1
    )

    def variant_key(row):

        base = row["canonical_product_key"]

        colour = normalize_key_text(
            row["colour"]
        )

        raw = f"{base}|{colour}"

        return hashlib.sha1(
            raw.encode("utf-8")
        ).hexdigest()[:16]

    df["variant_key"] = df.apply(
        variant_key,
        axis=1
    )

    return df


# ============================================================
# RAG TEXT GENERATION
# ============================================================

def create_rag_text(row):

    processor = normalize_processor(row)

    chipset = clean_string(
        row["processor_make"]
    )

    chipset_brand = extract_chipset_brand(
        chipset
    )

    bluetooth_supported, bluetooth_version = (
        normalize_bluetooth(
            row["bluetooth"]
        )
    )

    os_family, os_version = normalize_os(
        row["operating_system"]
    )

    resolution, resolution_width, resolution_height = (
        normalize_resolution(
            row["resolution"]
        )
    )

    dimensions = normalize_dimensions(
        row["dimensions"]
    )

    ram = format_number(row["ram_gb"])
    storage = format_number(
        row["internal_storage_gb"]
    )

    battery = format_number(
        row["battery_capacity_mah"]
    )

    screen = format_number(
        row["screen_size_inch"]
    )

    rear_mp = format_number(
        row["rear_camera_mp"]
    )

    front_mp = format_number(
        row["front_camera_mp"]
    )

    weight = format_number(
        row["weight_g"]
    )

    price = format_number(
        row["price_inr"],
        decimals=0
    )

    rating = format_number(
        row["rating_score"]
    )

    total_ratings = format_number(
        row["total_ratings"],
        decimals=0
    )

    sim_count = format_number(
        row["number_of_sims"],
        decimals=0
    )

    colour = clean_string(
        row["colour"]
    )

    text_parts = [
        "Category: Mobile Phone.",
        f"Brand: {clean_string(row['brand'])}.",
        f"Model: {clean_string(row['model'])}.",
        f"Product: {clean_string(row['product_name'])}.",

        f"Processor: {processor}.",
        f"Chipset: {chipset}.",
        f"Chipset manufacturer: {chipset_brand}.",

        f"RAM: {ram} GB.",
        f"Internal storage: {storage} GB.",

        f"Battery capacity: {battery} mAh.",

        f"Display size: {screen} inches.",
        f"Display resolution: {resolution}.",

        f"Rear camera: {clean_string(row['rear_camera'])}.",
        f"Rear primary camera: {rear_mp} MP.",

        f"Front camera: {clean_string(row['front_camera'])}.",
        f"Front camera: {front_mp} MP.",

        f"Operating system: {clean_string(row['operating_system'])}.",
        f"OS family: {os_family}.",
        f"OS version: {os_version}.",

        f"Wi-Fi: {bool_text(row['wifi'])}.",
        f"Bluetooth: {'Yes' if bluetooth_supported else 'No' if bluetooth_supported is False else 'Unknown'}.",
        f"Bluetooth version: {bluetooth_version}.",
        f"Touchscreen: {bool_text(row['touchscreen'])}.",
        f"GPS: {bool_text(row['gps'])}.",

        f"SIM support: {sim_count} SIM.",

        f"Dimensions: {dimensions}.",
        f"Weight: {weight} grams.",

        f"Colour information: {colour}.",

        f"Listed price: ₹{price}.",
        f"Rating: {rating} out of 5.",
        f"Total ratings: {total_ratings}."
    ]

    return " ".join(text_parts)


# ============================================================
# RAG METADATA
# ============================================================

def create_metadata(row):

    bluetooth_supported, bluetooth_version = (
        normalize_bluetooth(
            row["bluetooth"]
        )
    )

    os_family, os_version = normalize_os(
        row["operating_system"]
    )

    resolution, width, height = normalize_resolution(
        row["resolution"]
    )

    return {
        "product_id": clean_string(row["product_id"]),
        "brand": clean_string(row["brand"]),
        "model": clean_string(row["model"]),

        "canonical_product_key": row[
            "canonical_product_key"
        ],

        "variant_key": row["variant_key"],

        "ram_gb": clean_number(row["ram_gb"]),
        "internal_storage_gb": clean_number(
            row["internal_storage_gb"]
        ),

        "battery_capacity_mah": clean_number(
            row["battery_capacity_mah"]
        ),

        "screen_size_inch": clean_number(
            row["screen_size_inch"]
        ),

        "resolution": resolution,
        "resolution_width": width,
        "resolution_height": height,

        "rear_camera_mp": clean_number(
            row["rear_camera_mp"]
        ),

        "front_camera_mp": clean_number(
            row["front_camera_mp"]
        ),

        "processor": clean_string(
            row["processor"]
        ),

        "chipset": clean_string(
            row["processor_make"]
        ),

        "chipset_brand": extract_chipset_brand(
            row["processor_make"]
        ),

        "os_family": os_family,
        "os_version": os_version,

        "wifi": normalize_bool(row["wifi"]),
        "bluetooth": bluetooth_supported,
        "bluetooth_version": bluetooth_version,
        "touchscreen": normalize_bool(
            row["touchscreen"]
        ),
        "gps": normalize_bool(row["gps"]),

        "number_of_sims": clean_number(
            row["number_of_sims"],
            decimals=0
        ),

        "weight_g": clean_number(
            row["weight_g"]
        ),

        "colour": clean_string(row["colour"]),

        "price_inr": clean_number(
            row["price_inr"]
        ),

        "rating_score": clean_number(
            row["rating_score"]
        ),

        "total_ratings": clean_number(
            row["total_ratings"],
            decimals=0
        ),

        # Important:
        # These are percentages, not counts.
        "rating_1_pct": clean_number(
            row["rating_1_count"]
        ),

        "rating_2_pct": clean_number(
            row["rating_2_count"]
        ),

        "rating_3_pct": clean_number(
            row["rating_3_count"]
        ),

        "rating_4_pct": clean_number(
            row["rating_4_count"]
        ),

        "rating_5_pct": clean_number(
            row["rating_5_count"]
        ),

        "product_type": "mobile"
    }


# ============================================================
# QUALITY REPORT
# ============================================================

def build_quality_report(
    original_df,
    final_df,
    conflicts,
    anomalies,
    removed_rows
):

    report = {}

    report["input"] = {
        "file": str(INPUT_FILE), # <-- ADD str() HERE
        "rows": int(len(original_df)),
        "columns": int(len(original_df.columns))
    }

    report["output"] = {
        "rows": int(len(final_df)),
        "columns": int(len(final_df.columns))
    }

    report["rows_removed"] = len(
        removed_rows
    )

    report["ram_storage_corrections"] = len(
        conflicts
    )

    report["numeric_anomalies"] = len(
        anomalies
    )

    report["duplicate_statistics"] = {}

    if len(final_df) > 0:

        report["duplicate_statistics"][
            "duplicate_product_ids"
        ] = int(
            final_df["product_id"]
            .duplicated()
            .sum()
        )

        report["duplicate_statistics"][
            "duplicate_canonical_products"
        ] = int(
            final_df["canonical_product_key"]
            .duplicated()
            .sum()
        )

        report["duplicate_statistics"][
            "unique_canonical_products"
        ] = int(
            final_df["canonical_product_key"]
            .nunique()
        )

        report["duplicate_statistics"][
            "unique_variants"
        ] = int(
            final_df["variant_key"]
            .nunique()
        )

    report["rating_distribution"] = {
        "mean_sum": None,
        "invalid_distribution_rows": 0
    }

    rating_sums = []

    for _, row in final_df.iterrows():

        values = []

        for star in range(1, 6):

            value = safe_float(
                row[f"rating_{star}_count"]
            )

            if value is not None:
                values.append(value)

        if values:

            total = sum(values)
            rating_sums.append(total)

            if not 98 <= total <= 102:
                report["rating_distribution"][
                    "invalid_distribution_rows"
                ] += 1

    if rating_sums:
        report["rating_distribution"][
            "mean_sum"
        ] = round(
            float(np.mean(rating_sums)),
            2
        )

    report["unknown_values"] = {}

    for column in final_df.columns:

        count = int(
            final_df[column]
            .apply(is_unknown)
            .sum()
        )

        if count > 0:
            report["unknown_values"][column] = count

    report["status"] = (
        "READY_FOR_RAG_INDEXING"
        if (
            len(final_df) > 0
            and len(final_df["product_id"].unique())
            == len(final_df)
        )
        else "REQUIRES_REVIEW"
    )

    return report


# ============================================================
# MAIN PREPROCESSING
# ============================================================

def preprocess():

    print("=" * 70)
    print("MOBILE DATASET → RAG PREPROCESSOR")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # 1. LOAD
    # --------------------------------------------------------

    if not os.path.exists(INPUT_FILE):

        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False
    )

    original_df = df.copy()

    print(f"\nLoaded rows: {len(df):,}")
    print(f"Loaded columns: {len(df.columns):,}")

    # --------------------------------------------------------
    # 2. SCHEMA VALIDATION
    # --------------------------------------------------------

    required_columns = [
        "product_id",
        "brand",
        "model",
        "product_name",
        "processor",
        "processor_make",
        "ram_gb",
        "internal_storage_gb",
        "battery_capacity_mah",
        "screen_size_inch",
        "resolution",
        "rear_camera",
        "rear_camera_mp",
        "front_camera",
        "front_camera_mp",
        "operating_system",
        "wifi",
        "bluetooth",
        "touchscreen",
        "gps",
        "number_of_sims",
        "dimensions",
        "weight_g",
        "colour",
        "price_inr",
        "rating_score",
        "total_ratings",
        "rating_1_count",
        "rating_2_count",
        "rating_3_count",
        "rating_4_count",
        "rating_5_count"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing_columns)
        )

    # --------------------------------------------------------
    # 3. NORMALIZE STRING VALUES
    # --------------------------------------------------------

    string_columns = [
        "product_id",
        "brand",
        "model",
        "product_name",
        "processor",
        "processor_make",
        "resolution",
        "rear_camera",
        "front_camera",
        "operating_system",
        "wifi",
        "bluetooth",
        "dimensions",
        "colour",
        "product_type"
    ]

    for column in string_columns:

        if column in df.columns:

            df[column] = df[column].apply(
                clean_string
            )

    # --------------------------------------------------------
    # 4. NUMERIC CONVERSION
    # --------------------------------------------------------

    numeric_columns = [
        "ram_gb",
        "internal_storage_gb",
        "battery_capacity_mah",
        "screen_size_inch",
        "rear_camera_mp",
        "front_camera_mp",
        "number_of_sims",
        "weight_g",
        "price_inr",
        "rating_score",
        "total_ratings",
        "rating_1_count",
        "rating_2_count",
        "rating_3_count",
        "rating_4_count",
        "rating_5_count"
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # 5. REMOVE INVALID IDENTITY ROWS
    # --------------------------------------------------------

    removed_rows = []

    for index, row in df.iterrows():

        invalid = False

        for field in CRITICAL_FIELDS:

            value = clean_string(
                row[field]
            )

            if value == "Unknown":

                invalid = True
                break

        if invalid:

            removed_rows.append({
                "row_index": index,
                "product_id": row.get(
                    "product_id",
                    "Unknown"
                ),
                "reason": "missing_critical_identity_field"
            })

    if DROP_INVALID_ROWS and removed_rows:

        invalid_indices = [
            item["row_index"]
            for item in removed_rows
        ]

        df = df.drop(
            index=invalid_indices
        ).copy()

    # --------------------------------------------------------
    # 6. DUPLICATE PRODUCT IDs
    # --------------------------------------------------------

    duplicate_id_mask = (
        df["product_id"]
        .duplicated(keep="first")
    )

    duplicate_ids = df[
        duplicate_id_mask
    ].copy()

    if len(duplicate_ids) > 0:

        for _, row in duplicate_ids.iterrows():

            removed_rows.append({
                "row_index": row.name,
                "product_id": row["product_id"],
                "reason": "duplicate_product_id"
            })

        df = df[
            ~duplicate_id_mask
        ].copy()

    # --------------------------------------------------------
    # 7. RECONCILE RAM / STORAGE
    # --------------------------------------------------------

    conflicts = []

    df = reconcile_ram_storage(
        df,
        conflicts
    )

    # --------------------------------------------------------
    # 8. NORMALIZE RATINGS
    # --------------------------------------------------------

    df["rating_distribution_sum"] = df.apply(
        rating_distribution_sum,
        axis=1
    )

    # Rename semantics.

    df["rating_1_pct"] = df[
        "rating_1_count"
    ]

    df["rating_2_pct"] = df[
        "rating_2_count"
    ]

    df["rating_3_pct"] = df[
        "rating_3_count"
    ]

    df["rating_4_pct"] = df[
        "rating_4_count"
    ]

    df["rating_5_pct"] = df[
        "rating_5_count"
    ]

    # --------------------------------------------------------
    # 9. NUMERIC QUALITY CHECKS
    # --------------------------------------------------------

    anomalies = []

    validate_numeric_ranges(
        df,
        anomalies
    )

    # --------------------------------------------------------
    # 10. CANONICAL PRODUCT KEYS
    # --------------------------------------------------------

    df = create_product_keys(
        df
    )

    # --------------------------------------------------------
    # 11. COMPLETE RAG TEXT
    # --------------------------------------------------------

    df["text"] = df.apply(
        create_rag_text,
        axis=1
    )

    # --------------------------------------------------------
    # 12. REMOVE REDUNDANT ID COLUMN
    # --------------------------------------------------------

    if "id" in df.columns:

        df = df.drop(
            columns=["id"]
        )

    # product_type is retained because it is useful metadata.

    # --------------------------------------------------------
    # 13. FINAL DATA QUALITY FLAGS
    # --------------------------------------------------------

    df["has_specification_conflict"] = (
        df["product_id"].isin(
            {
                item["product_id"]
                for item in conflicts
            }
        )
    )

    df["has_numeric_anomaly"] = (
        df["product_id"].isin(
            {
                item["product_id"]
                for item in anomalies
            }
        )
    )

    # --------------------------------------------------------
    # 14. SAVE CLEAN CSV
    # --------------------------------------------------------

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 15. CREATE RAG JSON DOCUMENTS
    # --------------------------------------------------------

    documents = []

    for _, row in df.iterrows():

        metadata = create_metadata(
            row
        )

        document = {
            "id": clean_string(
                row["product_id"]
            ),

            "text": row["text"],

            "metadata": metadata
        }

        documents.append(
            document
        )

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            documents,
            file,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # 16. SAVE CONFLICT REPORT
    # --------------------------------------------------------

    if conflicts:

        pd.DataFrame(
            conflicts
        ).to_csv(
            CONFLICT_REPORT,
            index=False,
            encoding="utf-8-sig"
        )

    else:

        pd.DataFrame(
            columns=[
                "row_index",
                "product_id",
                "field",
                "original_value",
                "extracted_value",
                "source",
                "action"
            ]
        ).to_csv(
            CONFLICT_REPORT,
            index=False
        )

    # --------------------------------------------------------
    # 17. SAVE ANOMALY REPORT
    # --------------------------------------------------------

    anomaly_file = (
        OUTPUT_DIR /
        "numeric_anomalies.csv"
    )

    if anomalies:

        pd.DataFrame(
            anomalies
        ).to_csv(
            anomaly_file,
            index=False,
            encoding="utf-8-sig"
        )

    # --------------------------------------------------------
    # 18. SAVE REMOVED ROW REPORT
    # --------------------------------------------------------

    pd.DataFrame(
        removed_rows
    ).to_csv(
        REMOVED_REPORT,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 19. QUALITY REPORT
    # --------------------------------------------------------

    report = build_quality_report(
        original_df=original_df,
        final_df=df,
        conflicts=conflicts,
        anomalies=anomalies,
        removed_rows=removed_rows
    )

    report["output_files"] = {
        "clean_csv": str(OUTPUT_CSV),
        "rag_json": str(OUTPUT_JSON),
        "quality_report": str(QUALITY_REPORT),
        "conflict_report": str(CONFLICT_REPORT),
        "anomaly_report": str(anomaly_file),
        "removed_rows": str(REMOVED_REPORT)
    }

    with open(
        QUALITY_REPORT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # 20. FINAL SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("PREPROCESSING COMPLETED")
    print("=" * 70)

    print(
        f"\nOriginal rows       : {len(original_df):,}"
    )

    print(
        f"Final rows          : {len(df):,}"
    )

    print(
        f"Rows removed        : {len(removed_rows):,}"
    )

    print(
        f"RAM/storage fixes   : {len(conflicts):,}"
    )

    print(
        f"Numeric anomalies   : {len(anomalies):,}"
    )

    print(
        f"Unique products     : "
        f"{df['canonical_product_key'].nunique():,}"
    )

    print(
        f"Unique variants     : "
        f"{df['variant_key'].nunique():,}"
    )

    print(
        f"\nRAG status          : "
        f"{report['status']}"
    )

    print("\nGenerated files:")

    print(
        f"  1. {OUTPUT_CSV}"
    )

    print(
        f"  2. {OUTPUT_JSON}"
    )

    print(
        f"  3. {QUALITY_REPORT}"
    )

    print(
        f"  4. {CONFLICT_REPORT}"
    )

    print(
        f"  5. {anomaly_file}"
    )

    print(
        f"  6. {REMOVED_REPORT}"
    )

    print("\n" + "=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    preprocess()