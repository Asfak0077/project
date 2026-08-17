import os
import re
import ast
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

# Point to the raw tablets dataset
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "tablets.csv"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_CSV = OUTPUT_DIR / "tablets_rag_ready.csv"
OUTPUT_JSON = OUTPUT_DIR / "tablet_rag_corpus.json"

QUALITY_REPORT = OUTPUT_DIR / "tablet_data_quality_report.json"
CONFLICT_REPORT = OUTPUT_DIR / "tablet_specification_conflicts.csv"
ANOMALY_REPORT = OUTPUT_DIR / "tablet_numeric_anomalies.csv"
DUPLICATE_REPORT = OUTPUT_DIR / "tablet_duplicate_analysis.csv"
REMOVED_REPORT = OUTPUT_DIR / "tablet_removed_rows.csv"

# Critical fields must be present
DROP_INVALID_ROWS = True

# ============================================================
# HELPERS
# ============================================================

def clean_string(value):

    if pd.isna(value):
        return "Unknown"

    value = str(value).strip()

    if not value:
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

    if pd.isna(value):
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def format_number(value, decimals=2):

    value = safe_float(value)

    if value is None:
        return "Unknown"

    if float(value).is_integer():
        return str(int(value))

    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def normalize_boolean(value):

    if pd.isna(value):
        return "Unknown"

    value = str(value).strip().lower()

    if value in {"yes", "y", "true", "1"}:
        return True

    if value in {"no", "n", "false", "0"}:
        return False

    return "Unknown"


def boolean_text(value):

    value = normalize_boolean(value)

    if value is True:
        return "Yes"

    if value is False:
        return "No"

    return "Unknown"


def normalize_key(value):

    value = clean_string(value).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


# ============================================================
# OTHER_INFO PARSER
# ============================================================

def parse_other_info(value):

    if pd.isna(value):
        return {}

    try:

        data = ast.literal_eval(
            str(value)
        )

        if isinstance(data, dict):
            return data

    except (ValueError, SyntaxError):
        pass

    return {}


# ============================================================
# UNIT PARSING
# ============================================================

def parse_memory(value):

    """
    Convert RAM/storage values into GB.

    Examples:
        512MB -> 0.5 GB
        1GB   -> 1 GB
        2GB   -> 2 GB
        1TB   -> 1024 GB
    """

    value = clean_string(value)

    if value == "Unknown":
        return None

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)",
        value,
        flags=re.I
    )

    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).upper()

    if unit == "TB":
        return number * 1024

    if unit == "GB":
        return number

    if unit == "MB":
        return number / 1024

    if unit == "KB":
        return number / (1024 * 1024)

    return None


def parse_ram(value):

    return parse_memory(value)


def parse_storage(value):

    return parse_memory(value)


def parse_price(value):

    if pd.isna(value):
        return None

    value = str(value)

    value = re.sub(
        r"[₹,\s]",
        "",
        value
    )

    match = re.search(
        r"\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    return float(match.group())


# ============================================================
# PRODUCT NAME SPECIFICATION EXTRACTION
# ============================================================

def extract_ram_from_name(product_name):

    if is_unknown(product_name):
        return None

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(GB|MB)\s*RAM",
        product_name,
        flags=re.I
    )

    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).upper()

    if unit == "MB":
        return number / 1024

    return number


def extract_storage_from_name(product_name):

    if is_unknown(product_name):
        return None

    text = str(product_name)

    # Case:
    # 1GB RAM, 8GB
    ram_match = re.search(
        r"\d+(?:\.\d+)?\s*(?:GB|MB)\s*RAM",
        text,
        flags=re.I
    )

    if ram_match:

        remaining = (
            text[
                ram_match.end():
            ]
        )

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(GB|TB|MB)",
            remaining,
            flags=re.I
        )

        if match:

            number = float(
                match.group(1)
            )

            unit = match.group(2).upper()

            if unit == "TB":
                return number * 1024

            if unit == "MB":
                return number / 1024

            return number

    # Standard tablet names:
    #
    # Tablet (16GB, 7 Inches...)
    #
    matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*(GB|TB|MB)",
        text,
        flags=re.I
    )

    if matches:

        for number, unit in matches:

            number = float(number)
            unit = unit.upper()

            if unit == "TB":
                return number * 1024

            if unit == "MB":
                return number / 1024

            return number

    return None


# ============================================================
# DIMENSION PARSING
# ============================================================

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


def extract_thickness(other_info):

    value = other_info.get(
        "Thickness"
    )

    if value is None:
        return None

    return safe_float(value)


# ============================================================
# RESOLUTION
# ============================================================

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

    return (
        f"{width}x{height}",
        width,
        height
    )


# ============================================================
# OS NORMALIZATION
# ============================================================

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
        return (
            "Android",
            match.group(1)
        )

    if "ios" in value.lower():

        match = re.search(
            r"ios\s*([0-9]+(?:\.[0-9]+)*)",
            value,
            flags=re.I
        )

        if match:
            return (
                "iOS",
                match.group(1)
            )

        return "iOS", "Unknown"

    return value, "Unknown"


# ============================================================
# BOOLEAN FIELD NORMALIZATION
# ============================================================

BOOLEAN_FIELDS = [
    "Touchscreen",
    "Wi-Fi",
    "Bluetooth",
    "Expandable storage",
    "Accelerometer",
    "GPS",
    "Ambient light sensor",
    "Gyroscope",
    "Removable battery",
    "Compass/ Magnetometer",
    "Proximity sensor",
    "Barometer",
    "Wi-Fi Direct",
    "FM",
    "USB OTG",
    "NFC",
    "Temperature sensor",
    "Infrared",
    "Mobile High-Definition Link (MHL)"
]


# ============================================================
# OTHER_INFO RECOVERY
# ============================================================

def recover_from_other_info(df):

    fields = {
        "3G": "Sim 1 3G",
        "4G/ LTE": "Sim 1 4G/ LTE",
        "Supports 4G in India (Band 40)":
            "Sim 1 Supports 4G in India (Band 40)",
        "GSM/CDMA": "Sim 1 GSM/CDMA",
        "SIM Type": "Sim 1 SIM Type"
    }

    for index, row in df.iterrows():

        info = parse_other_info(
            row["other_info"]
        )

        for target, source in fields.items():

            current = row[target]

            if pd.isna(current) or is_unknown(current):

                recovered = info.get(
                    source
                )

                if recovered is not None:

                    df.at[
                        index,
                        target
                    ] = clean_string(
                        recovered
                    )

    # Recover second SIM 3G where possible.
    for index, row in df.iterrows():

        info = parse_other_info(
            row["other_info"]
        )

        if (
            pd.isna(row["Sim 2 3G"])
            or is_unknown(row["Sim 2 3G"])
        ):

            value = info.get(
                "Sim 2 3G"
            )

            if value is not None:

                df.at[
                    index,
                    "Sim 2 3G"
                ] = clean_string(value)

    return df


# ============================================================
# RAM / STORAGE RECONCILIATION
# ============================================================

def reconcile_ram_storage(df, conflicts):

    final_ram = []
    final_storage = []

    for index, row in df.iterrows():

        product_name = clean_string(
            row["Product Name"]
        )

        structured_ram = parse_ram(
            row["RAM"]
        )

        structured_storage = parse_storage(
            row["Internal storage"]
        )

        name_ram = extract_ram_from_name(
            product_name
        )

        name_storage = extract_storage_from_name(
            product_name
        )

        # --------------------------------------------
        # RAM
        # --------------------------------------------

        ram = structured_ram

        if name_ram is not None:

            if (
                structured_ram is not None
                and abs(
                    structured_ram - name_ram
                ) > 0.01
            ):

                conflicts.append({
                    "row_index": index,
                    "url": row["url"],
                    "field": "RAM",
                    "original_value":
                        row["RAM"],
                    "name_value":
                        name_ram,
                    "action":
                        "corrected_from_product_name"
                })

            ram = name_ram

        # --------------------------------------------
        # STORAGE
        # --------------------------------------------

        storage = structured_storage

        if name_storage is not None:

            if (
                structured_storage is not None
                and abs(
                    structured_storage -
                    name_storage
                ) > 0.01
            ):

                conflicts.append({
                    "row_index": index,
                    "url": row["url"],
                    "field":
                        "Internal storage",
                    "original_value":
                        row["Internal storage"],
                    "name_value":
                        name_storage,
                    "action":
                        "corrected_from_product_name"
                })

            storage = name_storage

        final_ram.append(ram)
        final_storage.append(storage)

    df["ram_gb"] = final_ram
    df["internal_storage_gb"] = final_storage

    return df


# ============================================================
# RATING NORMALIZATION
# ============================================================

def normalize_ratings(df):

    for star in range(1, 6):

        df[
            f"rating_{star}_pct"
        ] = pd.to_numeric(
            df[f"{star} Stars"],
            errors="coerce"
        )

    df[
        "rating_distribution_sum"
    ] = df[
        [
            f"rating_{i}_pct"
            for i in range(1, 6)
        ]
    ].sum(
        axis=1
    )

    # 0 means no usable rating distribution.
    df[
        "has_rating_distribution"
    ] = (
        df["rating_distribution_sum"] > 0
    )

    return df


# ============================================================
# CANONICAL KEYS
# ============================================================

def create_keys(df):

    def product_key(row):

        brand = normalize_key(
            row["Brand"]
        )

        model = normalize_key(
            row["Model"]
        )

        ram = format_number(
            row["ram_gb"]
        )

        storage = format_number(
            row["internal_storage_gb"]
        )

        raw = (
            f"{brand}|"
            f"{model}|"
            f"{ram}|"
            f"{storage}"
        )

        return hashlib.sha1(
            raw.encode("utf-8")
        ).hexdigest()[:16]

    df[
        "canonical_product_key"
    ] = df.apply(
        product_key,
        axis=1
    )

    def variant_key(row):

        base = row[
            "canonical_product_key"
        ]

        colour = normalize_key(
            row["Colours"]
        )

        price = format_number(
            row["price_inr"],
            decimals=0
        )

        raw = (
            f"{base}|"
            f"{colour}|"
            f"{price}"
        )

        return hashlib.sha1(
            raw.encode("utf-8")
        ).hexdigest()[:16]

    df[
        "variant_key"
    ] = df.apply(
        variant_key,
        axis=1
    )

    return df


# ============================================================
# NUMERIC ANOMALY DETECTION
# ============================================================

def detect_numeric_anomalies(df):

    anomalies = []

    ranges = {

        "screen_size_inch":
            (5.0, 15.0),

        "ram_gb":
            (0.125, 64),

        "internal_storage_gb":
            (1, 4096),

        "battery_capacity_mah":
            (1000, 30000),

        "weight_g":
            (100, 3000),

        "price_inr":
            (500, 1000000),

        "number_of_sims":
            (1, 4),

        "pixels_per_inch":
            (50, 1000),

        "expandable_storage_up_to_gb":
            (1, 4096),

        "bluetooth_version":
            (1, 6)
    }

    for column, (
        minimum,
        maximum
    ) in ranges.items():

        if column not in df.columns:
            continue

        for index, value in df[column].items():

            number = safe_float(
                value
            )

            if number is None:
                continue

            if (
                number < minimum
                or number > maximum
            ):

                anomalies.append({

                    "row_index":
                        index,

                    "url":
                        df.at[
                            index,
                            "url"
                        ],

                    "field":
                        column,

                    "value":
                        number,

                    "issue":
                        "outside_expected_range",

                    "action":
                        "flagged_not_imputed"
                })

    return anomalies


# ============================================================
# RAG TEXT
# ============================================================

def create_rag_text(row):

    product_name = clean_string(
        row["Product Name"]
    )

    if product_name == "Unknown":

        product_name = (
            f"{clean_string(row['Brand'])} "
            f"{clean_string(row['Model'])} "
            "Tablet"
        )

    os_family, os_version = normalize_os(
        row["Operating system"]
    )

    resolution, width, height = (
        normalize_resolution(
            row["Resolution"]
        )
    )

    dimensions = normalize_dimensions(
        row["Dimensions (mm)"]
    )

    thickness = safe_float(
        row["thickness_mm"]
    )

    lines = [

        "Category: Tablet.",

        f"Brand: {clean_string(row['Brand'])}.",

        f"Model: {clean_string(row['Model'])}.",

        f"Product: {product_name}.",

        f"Launch information: "
        f"{clean_string(row['Launched'])}.",

        f"Processor: "
        f"{clean_string(row['Processor'])}.",

        f"Processor make/chipset: "
        f"{clean_string(row['Processor make'])}.",

        f"RAM: "
        f"{format_number(row['ram_gb'])} GB.",

        f"Internal storage: "
        f"{format_number(row['internal_storage_gb'])} GB.",

        f"Expandable storage: "
        f"{boolean_text(row['Expandable storage'])}.",

        f"Expandable storage type: "
        f"{clean_string(row['Expandable storage type'])}.",

        f"Expandable storage capacity: "
        f"{format_number(row['expandable_storage_up_to_gb'])} GB.",

        f"Screen size: "
        f"{format_number(row['Screen size (inches)'])} inches.",

        f"Resolution: {resolution}.",

        f"Pixels per inch: "
        f"{format_number(row['Pixels per inch (PPI)'])}.",

        f"Touchscreen: "
        f"{boolean_text(row['Touchscreen'])}.",

        f"Front camera: "
        f"{clean_string(row['Front camera'])}.",

        f"Rear camera: "
        f"{clean_string(row['Rear camera'])}.",

        f"Rear flash: "
        f"{clean_string(row['Rear Flash'])}.",

        f"Operating system: "
        f"{clean_string(row['Operating system'])}.",

        f"OS family: {os_family}.",

        f"OS version: {os_version}.",

        f"Battery capacity: "
        f"{format_number(row['Battery capacity (mAh)'])} mAh.",

        f"Removable battery: "
        f"{boolean_text(row['Removable battery'])}.",

        f"Weight: "
        f"{format_number(row['Weight (g)'])} grams.",

        f"Dimensions: {dimensions}.",

        f"Thickness: "
        f"{format_number(thickness)} mm.",

        f"Colour: "
        f"{clean_string(row['Colours'])}.",

        f"Wi-Fi: "
        f"{boolean_text(row['Wi-Fi'])}.",

        f"Wi-Fi standards: "
        f"{clean_string(row['Wi-Fi standards supported'])}.",

        f"Wi-Fi Direct: "
        f"{boolean_text(row['Wi-Fi Direct'])}.",

        f"Bluetooth: "
        f"{boolean_text(row['Bluetooth'])}.",

        f"Bluetooth version: "
        f"{format_number(row['Bluetooth version'])}.",

        f"GPS: "
        f"{boolean_text(row['GPS'])}.",

        f"Number of SIMs: "
        f"{format_number(row['Number of SIMs'], 0)}.",

        f"3G: "
        f"{clean_string(row['3G'])}.",

        f"4G/LTE: "
        f"{clean_string(row['4G/ LTE'])}.",

        f"4G Band 40 support in India: "
        f"{clean_string(row['Supports 4G in India (Band 40)'])}.",

        f"GSM/CDMA: "
        f"{clean_string(row['GSM/CDMA'])}.",

        f"SIM type: "
        f"{clean_string(row['SIM Type'])}.",

        f"Accelerometer: "
        f"{boolean_text(row['Accelerometer'])}.",

        f"Ambient light sensor: "
        f"{boolean_text(row['Ambient light sensor'])}.",

        f"Gyroscope: "
        f"{boolean_text(row['Gyroscope'])}.",

        f"Compass/magnetometer: "
        f"{boolean_text(row['Compass/ Magnetometer'])}.",

        f"Proximity sensor: "
        f"{boolean_text(row['Proximity sensor'])}.",

        f"Barometer: "
        f"{boolean_text(row['Barometer'])}.",

        f"NFC: "
        f"{boolean_text(row['NFC'])}.",

        f"USB OTG: "
        f"{boolean_text(row['USB OTG'])}.",

        f"USB Type-C information: "
        f"{clean_string(row['usb_type_c'])}.",

        f"FM: "
        f"{boolean_text(row['FM'])}.",

        f"Infrared: "
        f"{boolean_text(row['Infrared'])}.",

        f"Temperature sensor: "
        f"{boolean_text(row['Temperature sensor'])}.",

        f"Headphones: "
        f"{clean_string(row['Headphones'])}.",

        f"MHL: "
        f"{boolean_text(row['Mobile High-Definition Link (MHL)'])}.",

        f"Form factor: "
        f"{clean_string(row['Form factor'])}.",

        f"Listed price: "
        f"₹{format_number(row['price_inr'], 0)}.",

        f"Rating count: "
        f"{format_number(row['total_ratings'], 0)}.",

        f"Rating distribution: "
        f"1-star {format_number(row['rating_1_pct'])}%, "
        f"2-star {format_number(row['rating_2_pct'])}%, "
        f"3-star {format_number(row['rating_3_pct'])}%, "
        f"4-star {format_number(row['rating_4_pct'])}%, "
        f"5-star {format_number(row['rating_5_pct'])}%."
    ]

    return " ".join(lines)


# ============================================================
# METADATA
# ============================================================

def create_metadata(row):

    resolution, width, height = (
        normalize_resolution(
            row["Resolution"]
        )
    )

    os_family, os_version = normalize_os(
        row["Operating system"]
    )

    return {

        "product_id":
            row["document_id"],

        "source_url":
            clean_string(row["url"]),

        "brand":
            clean_string(row["Brand"]),

        "model":
            clean_string(row["Model"]),

        "product_name": 
            clean_string(row["Product Name"]),

        "canonical_product_key":
            row["canonical_product_key"],

        "variant_key":
            row["variant_key"],

        "ram_gb":
            safe_float(row["ram_gb"]),

        "internal_storage_gb":
            safe_float(row["internal_storage_gb"]),

        "screen_size_inch":
            safe_float(
                row["Screen size (inches)"]
            ),

        "resolution":
            resolution,

        "resolution_width":
            width,

        "resolution_height":
            height,

        "ppi":
            safe_float(
                row["Pixels per inch (PPI)"]
            ),

        "battery_capacity_mah":
            safe_float(
                row["Battery capacity (mAh)"]
            ),

        "weight_g":
            safe_float(
                row["Weight (g)"]
            ),

        "thickness_mm":
            safe_float(
                row["thickness_mm"]
            ),

        "price_inr":
            safe_float(
                row["price_inr"]
            ),

        "processor":
            clean_string(
                row["Processor"]
            ),

        "processor_make":
            clean_string(
                row["Processor make"]
            ),

        "os_family":
            os_family,

        "os_version":
            os_version,

        "wifi":
            normalize_boolean(
                row["Wi-Fi"]
            ),

        "bluetooth":
            normalize_boolean(
                row["Bluetooth"]
            ),

        "bluetooth_version":
            safe_float(
                row["Bluetooth version"]
            ),

        "gps":
            normalize_boolean(
                row["GPS"]
            ),

        "touchscreen":
            normalize_boolean(
                row["Touchscreen"]
            ),

        "expandable_storage":
            normalize_boolean(
                row["Expandable storage"]
            ),

        "expandable_storage_up_to_gb":
            safe_float(
                row[
                    "expandable_storage_up_to_gb"
                ]
            ),

        "number_of_sims":
            safe_float(
                row["Number of SIMs"]
            ),

        "three_g":
            clean_string(
                row["3G"]
            ),

        "four_g_lte":
            clean_string(
                row["4G/ LTE"]
            ),

        "band_40":
            clean_string(
                row[
                    "Supports 4G in India (Band 40)"
                ]
            ),

        "sim_type":
            clean_string(
                row["SIM Type"]
            ),

        "colour":
            clean_string(
                row["Colours"]
            ),

        "rating_total":
            safe_float(
                row["total_ratings"]
            ),

        "rating_1_pct":
            safe_float(
                row["rating_1_pct"]
            ),

        "rating_2_pct":
            safe_float(
                row["rating_2_pct"]
            ),

        "rating_3_pct":
            safe_float(
                row["rating_3_pct"]
            ),

        "rating_4_pct":
            safe_float(
                row["rating_4_pct"]
            ),

        "rating_5_pct":
            safe_float(
                row["rating_5_pct"]
            )
    }


# ============================================================
# MAIN
# ============================================================

def preprocess():

    print("=" * 70)
    print("TABLET DATASET → RAG PREPROCESSOR")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    if not os.path.exists(INPUT_FILE):

        raise FileNotFoundError(
            f"File not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False
    )

    original_rows = len(df)

    print(
        f"\nInput rows: {original_rows:,}"
    )

    print(
        f"Input columns: {len(df.columns):,}"
    )

    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    required = [
        "url",
        "Brand",
        "Model",
        "Product Name",
        "RAM",
        "Internal storage",
        "Processor",
        "Processor make",
        "Screen size (inches)",
        "Resolution",
        "Operating system",
        "Battery capacity (mAh)",
        "Weight (g)",
        "Price in India",
        "Total Ratings",
        "1 Stars",
        "2 Stars",
        "3 Stars",
        "4 Stars",
        "5 Stars",
        "other_info"
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing)
        )

    # --------------------------------------------------------
    # STRING CLEANING
    # --------------------------------------------------------

    string_columns = [
        c for c in df.columns
        if df[c].dtype == "object"
    ]

    for column in string_columns:

        df[column] = df[column].apply(
            clean_string
        )

    # --------------------------------------------------------
    # PARSE OTHER_INFO
    # --------------------------------------------------------

    parsed_info = df[
        "other_info"
    ].apply(
        parse_other_info
    )

    df[
        "other_info_parsed"
    ] = parsed_info

    # --------------------------------------------------------
    # RECOVER VALUES
    # --------------------------------------------------------

    df = recover_from_other_info(
        df
    )

    # --------------------------------------------------------
    # NUMERIC FIELDS
    # --------------------------------------------------------

    df["price_inr"] = df[
        "Price in India"
    ].apply(
        parse_price
    )

    df["total_ratings"] = pd.to_numeric(
        df["Total Ratings"],
        errors="coerce"
    )

    df["number_of_sims"] = pd.to_numeric(
        df["Number of SIMs"],
        errors="coerce"
    )

    df["Bluetooth version"] = pd.to_numeric(
        df["Bluetooth version"],
        errors="coerce"
    )

    df["Pixels per inch (PPI)"] = pd.to_numeric(
        df["Pixels per inch (PPI)"],
        errors="coerce"
    )

    df["Battery capacity (mAh)"] = pd.to_numeric(
        df["Battery capacity (mAh)"],
        errors="coerce"
    )

    df["Weight (g)"] = pd.to_numeric(
        df["Weight (g)"],
        errors="coerce"
    )

    df[
        "Screen size (inches)"
    ] = pd.to_numeric(
        df["Screen size (inches)"],
        errors="coerce"
    )

    df[
        "expandable_storage_up_to_gb"
    ] = pd.to_numeric(
        df[
            "Expandable storage up to (GB)"
        ],
        errors="coerce"
    )

    # --------------------------------------------------------
    # RAM / STORAGE
    # --------------------------------------------------------

    conflicts = []

    df = reconcile_ram_storage(
        df,
        conflicts
    )

    # --------------------------------------------------------
    # OTHER_INFO EXTRACTION
    # --------------------------------------------------------

    df["thickness_mm"] = df[
        "other_info_parsed"
    ].apply(
        extract_thickness
    )

    df["usb_type_c"] = df[
        "other_info_parsed"
    ].apply(
        lambda x: clean_string(
            x.get("USB Type-C")
        )
        if x.get("USB Type-C") is not None
        else "Unknown"
    )

    # --------------------------------------------------------
    # RATINGS
    # --------------------------------------------------------

    df = normalize_ratings(
        df
    )

    # --------------------------------------------------------
    # IDENTIFIER
    # --------------------------------------------------------

    def make_document_id(row):

        raw = (
            f"{clean_string(row['url'])}|"
            f"{clean_string(row['Brand'])}|"
            f"{clean_string(row['Model'])}|"
            f"{row['ram_gb']}|"
            f"{row['internal_storage_gb']}|"
            f"{clean_string(row['Colours'])}|"
            f"{row['price_inr']}"
        )

        return (
            "TAB_" +
            hashlib.sha1(
                raw.encode("utf-8")
            ).hexdigest()[:16]
        )

    df["document_id"] = df.apply(
        make_document_id,
        axis=1
    )
    df = df.drop_duplicates(subset=["document_id"], keep="first").reset_index(drop=True)
    # --------------------------------------------------------
    # CANONICAL KEYS
    # --------------------------------------------------------

    df = create_keys(
        df
    )

    # --------------------------------------------------------
    # NUMERIC ANOMALIES
    # --------------------------------------------------------

    anomalies = detect_numeric_anomalies(
        df
    )

    # --------------------------------------------------------
    # DUPLICATE ANALYSIS
    # --------------------------------------------------------

    duplicate_records = []

    url_counts = (
        df["url"]
        .value_counts()
    )

    for url, count in url_counts.items():

        if count > 1:

            duplicate_records.append({

                "duplicate_type":
                    "URL",

                "key":
                    url,

                "count":
                    int(count)
            })

    product_counts = (
        df["canonical_product_key"]
        .value_counts()
    )

    for key, count in product_counts.items():

        if count > 1:

            duplicate_records.append({

                "duplicate_type":
                    "canonical_product",

                "key":
                    key,

                "count":
                    int(count)
            })

    # --------------------------------------------------------
    # RAG TEXT
    # --------------------------------------------------------

    df["text"] = df.apply(
        create_rag_text,
        axis=1
    )

    # --------------------------------------------------------
    # QUALITY FLAGS
    # --------------------------------------------------------

    conflict_ids = set()

    for item in conflicts:

        conflict_ids.add(
            item["url"]
        )

    anomaly_ids = set()

    for item in anomalies:

        anomaly_ids.add(
            item["url"]
        )

    df[
        "has_specification_conflict"
    ] = df["url"].isin(
        conflict_ids
    )

    df[
        "has_numeric_anomaly"
    ] = df["url"].isin(
        anomaly_ids
    )

    # --------------------------------------------------------
    # SAVE CLEAN CSV
    # --------------------------------------------------------

    output_df = df.drop(
        columns=[
            "other_info_parsed"
        ]
    )

    output_df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # RAG DOCUMENTS
    # --------------------------------------------------------

    documents = []

    for _, row in df.iterrows():

        documents.append({

            "id":
                row["document_id"],

            "text":
                row["text"],

            "metadata":
                create_metadata(row)
        })

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
    # REPORTS
    # --------------------------------------------------------

    pd.DataFrame(
        conflicts
    ).to_csv(
        CONFLICT_REPORT,
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(
        anomalies
    ).to_csv(
        ANOMALY_REPORT,
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(
        duplicate_records
    ).to_csv(
        DUPLICATE_REPORT,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # REMOVED ROWS
    # --------------------------------------------------------

    pd.DataFrame(
        columns=[
            "row_index",
            "reason"
        ]
    ).to_csv(
        REMOVED_REPORT,
        index=False
    )

    # --------------------------------------------------------
    # QUALITY REPORT
    # --------------------------------------------------------

    rating_sums = df[
        [
            "rating_1_pct",
            "rating_2_pct",
            "rating_3_pct",
            "rating_4_pct",
            "rating_5_pct"
        ]
    ].sum(
        axis=1
    )

    report = {

        "input": {

            "file":
                str(INPUT_FILE), # <-- Fixed with str()

            "rows":
                original_rows,

            "columns":
                len(df.columns)
        },

        "output": {

            "rows":
                len(df),

            "rag_documents":
                len(documents)
        },

        "conflicts": {

            "ram_storage_conflicts":
                len(conflicts)
        },

        "numeric_anomalies": {

            "count":
                len(anomalies)
        },

        "duplicates": {

            "duplicate_urls":
                int(
                    df["url"]
                    .duplicated()
                    .sum()
                ),

            "duplicate_product_names":
                int(
                    df["Product Name"]
                    .duplicated()
                    .sum()
                ),

            "duplicate_brand_model":
                int(
                    df[
                        ["Brand", "Model"]
                    ]
                    .astype(str)
                    .agg(
                        "|".join,
                        axis=1
                    )
                    .duplicated()
                    .sum()
                ),

            "unique_canonical_products":
                int(
                    df[
                        "canonical_product_key"
                    ].nunique()
                ),

            "unique_variants":
                int(
                    df[
                        "variant_key"
                    ].nunique()
                )
        },

        "ratings": {

            "distribution_sum_min":
                float(
                    rating_sums.min()
                ),

            "distribution_sum_max":
                float(
                    rating_sums.max()
                ),

            "zero_distribution_rows":
                int(
                    (
                        rating_sums == 0
                    ).sum()
                ),

            "valid_distribution_rows":
                int(
                    (
                        rating_sums.between(
                            98,
                            102
                        )
                    ).sum()
                )
        },

        "missingness": {},

        "output_files": {

            "csv":
                str(OUTPUT_CSV),

            "json":
                str(OUTPUT_JSON),

            "quality_report":
                str(QUALITY_REPORT),

            "conflicts":
                str(CONFLICT_REPORT),

            "anomalies":
                str(ANOMALY_REPORT),

            "duplicates":
                str(DUPLICATE_REPORT),

            "removed":
                str(REMOVED_REPORT)
        },

        "rag_status":
            "READY_FOR_RAG_VALIDATION"
    }

    for column in df.columns:

        count = int(
            df[column]
            .apply(is_unknown)
            .sum()
        )

        if count:
            report[
                "missingness"
            ][column] = count

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
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TABLET PREPROCESSING COMPLETED")
    print("=" * 70)

    print(
        f"\nInput rows              : "
        f"{original_rows:,}"
    )

    print(
        f"Output rows             : "
        f"{len(df):,}"
    )

    print(
        f"RAG documents           : "
        f"{len(documents):,}"
    )

    print(
        f"RAM/storage conflicts   : "
        f"{len(conflicts):,}"
    )

    print(
        f"Numeric anomalies       : "
        f"{len(anomalies):,}"
    )

    print(
        f"Unique canonical models : "
        f"{df['canonical_product_key'].nunique():,}"
    )

    print(
        f"Unique variants         : "
        f"{df['variant_key'].nunique():,}"
    )

    print(
        f"\nOutput directory: "
        f"{OUTPUT_DIR}"
    )

    print("\n" + "=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    preprocess()