from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import chromadb
from chromadb.utils import embedding_functions


# ============================================================
# PATHS / CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_VECTOR_DB = (
    PROJECT_ROOT
    / "data"
    / "vector_db"
)

DEFAULT_COLLECTION = "laptops"

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DEFAULT_TOP_K = 10

# Retrieve more candidates than eventually displayed.
# Ranking/recommendation will later reduce this.
DEFAULT_CANDIDATE_MULTIPLIER = 3


# ============================================================
# DATA CONTRACTS
# ============================================================

@dataclass
class RetrievalFilters:
    """
    Hard constraints extracted from the user's query.
    """

    brands: List[str] = field(default_factory=list)

    min_price: Optional[float] = None
    max_price: Optional[float] = None

    min_ram_gb: Optional[float] = None
    max_ram_gb: Optional[float] = None

    min_storage_gb: Optional[float] = None
    max_storage_gb: Optional[float] = None

    min_screen_size: Optional[float] = None
    max_screen_size: Optional[float] = None

    min_weight_kg: Optional[float] = None
    max_weight_kg: Optional[float] = None

    min_rating: Optional[float] = None

    dedicated_graphics: Optional[bool] = None
    touch_screen: Optional[bool] = None
    fingerprint_sensor: Optional[bool] = None

    storage_types: List[str] = field(default_factory=list)

    gpu_keywords: List[str] = field(default_factory=list)


@dataclass
class QueryInterpretation:
    """
    Output of the deterministic query understanding stage.
    """

    original_query: str

    semantic_query: str

    filters: RetrievalFilters

    # Terms such as "lightweight", "gaming", "coding", etc.
    preference_terms: List[str] = field(default_factory=list)

    # Original natural-language constraints retained for inspection.
    extracted_constraints: List[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    """
    One product returned from retrieval.
    """

    product_id: str

    document: str

    metadata: Dict[str, Any]

    distance: Optional[float]

    # Converted similarity value where possible.
    # Smaller Chroma distance generally means closer.
    similarity: Optional[float]

    matched_filters: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class RetrievalResponse:
    """
    Complete retrieval response.
    """

    query: QueryInterpretation

    results: List[RetrievalResult]

    filters_applied: bool

    filter_expression: Optional[Dict[str, Any]]

    candidate_count: int


# ============================================================
# NORMALIZATION
# ============================================================

BRAND_ALIASES = {
    "asus": "Asus",
    "asustek": "Asus",
    "hp": "HP",
    "hewlett packard": "HP",
    "hewlett-packard": "HP",
    "lenovo": "Lenovo",
    "dell": "Dell",
    "acer": "Acer",
    "apple": "Apple",
    "macbook": "Apple",
    "microsoft": "Microsoft",
    "msi": "MSI",
    "samsung": "Samsung",
    "lg": "LG",
    "avita": "Avita",
    "chuwi": "Chuwi",
    "micromax": "Micromax",
    "xiaomi": "Xiaomi",
    "redmi": "Xiaomi",
    "realme": "Realme",
    "honor": "Honor",
    "infinix": "Infinix",
    "moto": "Motorola",
    "motorola": "Motorola",
}


def normalize_query(text: str) -> str:
    """
    Normalize user text without destroying useful terms.
    """
    text = str(text or "").strip()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def normalize_brand(value: str) -> Optional[str]:
    text = value.strip().lower()

    if text in BRAND_ALIASES:
        return BRAND_ALIASES[text]

    # Handle simple punctuation/casing differences.
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    ).strip()

    if normalized in BRAND_ALIASES:
        return BRAND_ALIASES[normalized]

    # Unknown brand should not be invented.
    return None


def deduplicate_preserve_order(
    values: Sequence[str],
) -> List[str]:
    seen = set()
    result = []

    for value in values:
        normalized = value.strip()

        if not normalized:
            continue

        key = normalized.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(normalized)

    return result


# ============================================================
# NUMBER / CURRENCY PARSING
# ============================================================

def parse_number(value: str) -> Optional[float]:
    """
    Parse values such as:
        70000
        70,000
        70k
        70 K
    """
    if not value:
        return None

    text = value.lower().replace(",", "").strip()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac)?",
        text,
    )

    if match is None:
        return None

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix in {"k", "thousand"}:
        number *= 1_000

    elif suffix in {"lakh", "lac"}:
        number *= 100_000

    return number


def parse_price(text: str) -> Optional[float]:
    """
    Parse Indian-style prices.

    Examples:
        ₹70000
        ₹70,000
        70000 rupees
        70k
        70 K
        1 lakh
    """
    pattern = re.search(
        r"(?:₹|rs\.?|inr)?\s*"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*(k|thousand|lakh|lac)?"
        r"(?:\s*(?:rupees|rs|inr))?",
        text.lower(),
    )

    if pattern is None:
        return None

    number = float(
        pattern.group(1).replace(",", "")
    )

    suffix = pattern.group(2)

    if suffix in {"k", "thousand"}:
        number *= 1_000

    elif suffix in {"lakh", "lac"}:
        number *= 100_000

    return number


# ============================================================
# RANGE PARSING
# ============================================================

def parse_range_expression(
    text: str,
    unit_pattern: str,
) -> List[Tuple[str, float]]:
    """
    Returns operator + numeric value pairs.

    Supported natural expressions:
        under 70000
        below 70000
        less than 70000
        at most 70000
        over 50000
        above 50000
        more than 50000
        at least 16
        minimum 16
        max 16
        between 50000 and 70000
    """
    matches: List[Tuple[str, float]] = []

    number = (
        rf"(\d+(?:[.,]\d+)?)"
        rf"\s*"
        rf"(k|thousand|lakh|lac)?"
        rf"\s*"
        rf"(?:{unit_pattern})?"
    )

    # --------------------------------------------------------
    # Between X and Y
    # --------------------------------------------------------

    between_pattern = re.compile(
        rf"\bbetween\s+{number}\s+"
        rf"(?:and|to|-)\s+{number}",
        re.IGNORECASE,
    )

    for match in between_pattern.finditer(text):

        groups = match.groups()

        first_number = float(
            groups[0].replace(",", "")
        )

        first_suffix = groups[1]

        second_number = float(
            groups[2].replace(",", "")
        )

        second_suffix = groups[3]

        first_value = apply_number_suffix(
            first_number,
            first_suffix,
        )

        second_value = apply_number_suffix(
            second_number,
            second_suffix,
        )

        matches.append(
            (">=", first_value)
        )

        matches.append(
            ("<=", second_value)
        )

    # --------------------------------------------------------
    # At most / below / under
    # --------------------------------------------------------

    upper_pattern = re.compile(
        r"\b(?:under|below|less than|at most|up to|max(?:imum)?)"
        r"\s+(₹?\s*[\d,]+(?:\.\d+)?\s*(?:k|thousand|lakh|lac)?)"
        r"(?!\s*(?:gb|tb|mb|ram|inch|inches|kg))", # Prevents capturing RAM/Weight
        re.IGNORECASE,
    )

    for match in upper_pattern.finditer(text):

        groups = match.groups()

        value = float(
            groups[1].replace(",", "")
        )

        value = apply_number_suffix(
            value,
            groups[2],
        )

        matches.append(
            ("<=", value)
        )

    # --------------------------------------------------------
    # At least / above / over
    # --------------------------------------------------------

    lower_pattern = re.compile(
        r"\b(?:over|above|more than|at least|min(?:imum)?)"
        r"\s+(₹?\s*[\d,]+(?:\.\d+)?\s*(?:k|thousand|lakh|lac)?)"
        r"(?!\s*(?:gb|tb|mb|ram|inch|inches|kg))", # Prevents capturing RAM/Weight
        re.IGNORECASE,
    )

    for match in lower_pattern.finditer(text):

        groups = match.groups()

        value = float(
            groups[1].replace(",", "")
        )

        value = apply_number_suffix(
            value,
            groups[2],
        )

        matches.append(
            (">=", value)
        )

    return matches


def apply_number_suffix(
    number: float,
    suffix: Optional[str],
) -> float:
    if not suffix:
        return number

    suffix = suffix.lower()

    if suffix in {"k", "thousand"}:
        return number * 1_000

    if suffix in {"lakh", "lac"}:
        return number * 100_000

    return number


# ============================================================
# PRICE EXTRACTION
# ============================================================

def extract_price_filters(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []
    
    # Negative lookahead: Prevent capturing RAM, Storage, or Weight as currency
    anti_collision = r"(?!\s*(?:gb|tb|mb|ram|inch|inches|kg))"

    # --------------------------------------------------------
    # Between X and Y / range
    # --------------------------------------------------------
    range_pattern = re.compile(
        r"\bbetween\s+"
        r"(₹?\s*[\d,]+(?:\.\d+)?\s*(?:k|thousand|lakh|lac)?)"
        + anti_collision +
        r"\s+(?:and|to|-)\s+"
        r"(₹?\s*[\d,]+(?:\.\d+)?\s*(?:k|thousand|lakh|lac)?)"
        + anti_collision,
        re.IGNORECASE,
    )

    range_match = range_pattern.search(text)
    if range_match:
        lower = parse_price(range_match.group(1))
        upper = parse_price(range_match.group(2))
        if lower is not None:
            filters.min_price = lower
        if upper is not None:
            filters.max_price = upper
        extracted.append(range_match.group(0))
        return extracted

    # --------------------------------------------------------
    # Explicit upper bound
    # --------------------------------------------------------
    upper_pattern = re.compile(
        r"\b(?:under|below|less than|at most|up to|max(?:imum)?)"
        r"\s+(₹?\s*[\d,]+(?:\.\d+)?\s*(?:k|thousand|lakh|lac)?)"
        + anti_collision,
        re.IGNORECASE,
    )

    match = upper_pattern.search(text)
    if match:
        value = parse_price(match.group(1))
        if value is not None:
            filters.max_price = value
            extracted.append(match.group(0))

    # --------------------------------------------------------
    # Explicit lower bound
    # --------------------------------------------------------
    lower_pattern = re.compile(
        r"\b(?:over|above|more than|at least|min(?:imum)?)"
        r"\s+(₹?\s*[\d,]+(?:\.\d+)?\s*(?:k|thousand|lakh|lac)?)"
        + anti_collision,
        re.IGNORECASE,
    )

    match = lower_pattern.search(text)
    if match:
        value = parse_price(match.group(1))
        if value is not None:
            filters.min_price = value
            extracted.append(match.group(0))

    # --------------------------------------------------------
    # Bare ₹ amount + "budget"
    # --------------------------------------------------------
    if filters.min_price is None and filters.max_price is None:
        budget_pattern = re.search(
            r"\b(?:budget|spend|price)\b"
            r".{0,20}?"
            r"(₹?\s*[\d,]+(?:\.\d+)?\s*(?:k|thousand|lakh|lac)?)"
            + anti_collision,
            text,
            re.IGNORECASE,
        )

        if budget_pattern:
            value = parse_price(budget_pattern.group(1))
            if value is not None:
                filters.max_price = value
                extracted.append(budget_pattern.group(0))

    return extracted
# ============================================================
# RAM EXTRACTION
# ============================================================

def extract_ram_filter(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []

    # "at least 16GB RAM"
    lower = re.search(
        r"\b(?:at least|minimum|min)\s+"
        r"(\d+(?:\.\d+)?)\s*(?:gb|g)?\s*"
        r"(?:of\s+)?ram\b",
        text,
        re.IGNORECASE,
    )

    if lower:
        filters.min_ram_gb = float(
            lower.group(1)
        )

        extracted.append(
            lower.group(0)
        )

    # "16GB RAM or more"
    or_more = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:gb|g)\s*"
        r"ram\s+(?:or\s+more|and\s+above)\b",
        text,
        re.IGNORECASE,
    )

    if or_more:
        filters.min_ram_gb = float(
            or_more.group(1)
        )

        extracted.append(
            or_more.group(0)
        )

    # "up to 32GB RAM"
    upper = re.search(
        r"\b(?:up to|max(?:imum)?|no more than)\s+"
        r"(\d+(?:\.\d+)?)\s*(?:gb|g)\s*ram\b",
        text,
        re.IGNORECASE,
    )

    if upper:
        filters.max_ram_gb = float(
            upper.group(1)
        )

        extracted.append(
            upper.group(0)
        )

    # Generic "16GB RAM" when no stronger relation is present.
    if (
        filters.min_ram_gb is None
        and filters.max_ram_gb is None
    ):
        exact = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(?:gb|g)\s*ram\b",
            text,
            re.IGNORECASE,
        )

        if exact:
            filters.min_ram_gb = float(
                exact.group(1)
            )

            extracted.append(
                exact.group(0)
            )

    return extracted


# ============================================================
# STORAGE EXTRACTION
# ============================================================

def normalize_storage_value(
    value: float,
    unit: Optional[str],
) -> float:

    if unit is None:
        # Bare storage numbers are ambiguous.
        # Treat common 4-digit values as GB.
        return value

    unit = unit.lower()

    if unit == "tb":
        return value * 1024

    return value


def extract_storage_filters(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []

    pattern = re.compile(
        r"\b(?:at least|min(?:imum)?|minimum|"
        r"over|above|under|below|up to|max(?:imum)?|"
        r"(\d+(?:\.\d+)?)\s*(tb|gb))?"
        r"\s*(\d+(?:\.\d+)?)\s*(tb|gb)"
        r"(?:\s*(?:ssd|nvme|hdd))?",
        re.IGNORECASE,
    )

    # Simpler patterns are more reliable for natural laptop queries.
    lower_pattern = re.compile(
        r"\b(?:at least|minimum|min)\s+"
        r"(\d+(?:\.\d+)?)\s*(tb|gb)\s*"
        r"(?:storage|ssd|nvme|hdd)\b",
        re.IGNORECASE,
    )

    for match in lower_pattern.finditer(text):

        value = normalize_storage_value(
            float(match.group(1)),
            match.group(2),
        )

        filters.min_storage_gb = value

        extracted.append(
            match.group(0)
        )

    exact_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(tb|gb)\s*"
        r"(ssd|nvme|hdd)?\b",
        re.IGNORECASE,
    )

    if filters.min_storage_gb is None:
        for match in exact_pattern.finditer(text):

            unit = match.group(2)
            storage_type = match.group(3)

            value = normalize_storage_value(
                float(match.group(1)),
                unit,
            )

            # Only interpret this as storage when:
            #   - followed by known storage term, or
            #   - unit is TB, or
            #   - "storage" occurs nearby.
            context = text[
                max(0, match.start() - 15):
                min(len(text), match.end() + 15)
            ].lower()

            storage_signal = (
                storage_type is not None
                or "storage" in context
                or unit.lower() == "tb"
            )

            if not storage_signal:
                continue

            filters.min_storage_gb = value

            if storage_type:
                normalized_type = storage_type.upper()

                if normalized_type == "NVME":
                    normalized_type = "NVMe SSD"

                else:
                    normalized_type = (
                        normalized_type.upper()
                    )

                filters.storage_types.append(
                    normalized_type
                )

            extracted.append(
                match.group(0)
            )

    # Explicit storage type without capacity.
    if re.search(
        r"\bnvme(?:\s+ssd)?\b",
        text,
        re.IGNORECASE,
    ):
        filters.storage_types.append(
            "NVMe SSD"
        )

    elif re.search(
        r"\bssd\b",
        text,
        re.IGNORECASE,
    ):
        filters.storage_types.append(
            "SSD"
        )

    elif re.search(
        r"\bhdd\b",
        text,
        re.IGNORECASE,
    ):
        filters.storage_types.append(
            "HDD"
        )

    filters.storage_types = (
        deduplicate_preserve_order(
            filters.storage_types
        )
    )

    return extracted


# ============================================================
# SCREEN SIZE
# ============================================================

def extract_screen_filter(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []

    lower = re.search(
        r"\b(?:at least|min(?:imum)?)\s+"
        r"(\d+(?:\.\d+)?)\s*(?:inch|inches|in)\b",
        text,
        re.IGNORECASE,
    )

    if lower:
        filters.min_screen_size = float(
            lower.group(1)
        )

        extracted.append(
            lower.group(0)
        )

    upper = re.search(
        r"\b(?:up to|max(?:imum)?|no more than)\s+"
        r"(\d+(?:\.\d+)?)\s*(?:inch|inches|in)\b",
        text,
        re.IGNORECASE,
    )

    if upper:
        filters.max_screen_size = float(
            upper.group(1)
        )

        extracted.append(
            upper.group(0)
        )

    return extracted


# ============================================================
# WEIGHT
# ============================================================

def extract_weight_filter(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []

    upper = re.search(
        r"\b(?:under|below|less than|up to|max(?:imum)?)\s+"
        r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)\b",
        text,
        re.IGNORECASE,
    )

    if upper:
        filters.max_weight_kg = float(
            upper.group(1)
        )

        extracted.append(
            upper.group(0)
        )

    lower = re.search(
        r"\b(?:over|above|more than|at least|min(?:imum)?)\s+"
        r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)\b",
        text,
        re.IGNORECASE,
    )

    if lower:
        filters.min_weight_kg = float(
            lower.group(1)
        )

        extracted.append(
            lower.group(0)
        )

    return extracted


# ============================================================
# RATING
# ============================================================

def extract_rating_filter(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []

    match = re.search(
        r"\b(?:at least|minimum|min)"
        r"\s+(\d+(?:\.\d+)?)\s*(?:star|stars)?"
        r"(?:\s+(?:rating|rated))?",
        text,
        re.IGNORECASE,
    )

    if match:
        value = float(
            match.group(1)
        )

        if 0 < value <= 5:
            filters.min_rating = value

            extracted.append(
                match.group(0)
            )

    return extracted


# ============================================================
# FEATURE FILTERS
# ============================================================

def extract_feature_filters(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []

    # Dedicated graphics
    dedicated_patterns = [
        r"\bdedicated\s+(?:graphics|gpu|graphics card)\b",
        r"\bwith\s+(?:a\s+)?dedicated\s+(?:gpu|graphics)\b",
        r"\bdiscrete\s+(?:gpu|graphics)\b",
    ]

    if any(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        for pattern in dedicated_patterns
    ):
        filters.dedicated_graphics = True

    # Integrated-only
    if re.search(
        r"\bintegrated\s+(?:graphics|gpu)\s+only\b",
        text,
        re.IGNORECASE,
    ):
        filters.dedicated_graphics = False

    # Touch
    if re.search(
        r"\btouch(?:screen)?\b",
        text,
        re.IGNORECASE,
    ):
        filters.touch_screen = True

    # Fingerprint
    if re.search(
        r"\bfingerprint(?:\s+sensor|\s+reader)?\b",
        text,
        re.IGNORECASE,
    ):
        filters.fingerprint_sensor = True

    # GPU family/model keywords.
    gpu_terms = [
        "nvidia",
        "geforce",
        "rtx",
        "gtx",
        "radeon",
        "amd radeon",
        "intel arc",
        "arc graphics",
        "iris xe",
        "uhd graphics",
        "mx",
    ]

    for term in gpu_terms:
        if re.search(
            rf"\b{re.escape(term)}\b",
            text,
            re.IGNORECASE,
        ):
            filters.gpu_keywords.append(
                term
            )

    filters.gpu_keywords = (
        deduplicate_preserve_order(
            filters.gpu_keywords
        )
    )

    if filters.dedicated_graphics is not None:
        extracted.append(
            "dedicated graphics"
            if filters.dedicated_graphics
            else "integrated graphics only"
        )

    return extracted


# ============================================================
# BRAND EXTRACTION
# ============================================================

def extract_brands(
    text: str,
    filters: RetrievalFilters,
) -> List[str]:

    extracted = []

    # We use known aliases rather than accepting arbitrary
    # capitalized words as brands.
    ordered_aliases = sorted(
        BRAND_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for alias, canonical in ordered_aliases:

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(alias)
            + r"(?![a-z0-9])"
        )

        if re.search(
            pattern,
            text,
            re.IGNORECASE,
        ):
            filters.brands.append(
                canonical
            )

            extracted.append(
                alias
            )

    filters.brands = deduplicate_preserve_order(
        filters.brands
    )

    return extracted


# ============================================================
# SEMANTIC QUERY CLEANING
# ============================================================

def remove_constraint_phrases(
    query: str,
) -> str:

    cleaned = query

    patterns = [
        # Prices
        r"\b(?:under|below|less than|at most|up to|max(?:imum)?)"
        r"\s+(?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d+)?"
        r"\s*(?:k|thousand|lakh|lac)?"
        r"(?:\s*(?:rupees|rs|inr))?\b",

        r"\b(?:over|above|more than|at least|min(?:imum)?)"
        r"\s+(?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d+)?"
        r"\s*(?:k|thousand|lakh|lac)?"
        r"(?:\s*(?:rupees|rs|inr))?\b",

        r"\b(?:budget|price)\s*(?:is|of|:)?\s*"
        r"(?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d+)?"
        r"\s*(?:k|thousand|lakh|lac)?\b",

        # RAM
        r"\b(?:at least|minimum|min)\s+"
        r"\d+(?:\.\d+)?\s*(?:gb|g)\s*ram\b",

        r"\b\d+(?:\.\d+)?\s*(?:gb|g)\s*"
        r"ram\s+(?:or\s+more|and\s+above)\b",

        r"\b(?:up to|max(?:imum)?|no more than)\s+"
        r"\d+(?:\.\d+)?\s*(?:gb|g)\s*ram\b",

        # Weight
        r"\b(?:under|below|less than|up to|max(?:imum)?)\s+"
        r"\d+(?:\.\d+)?\s*(?:kg|kgs|kilograms?)\b",

        # Screen
        r"\b(?:at least|min(?:imum)?)\s+"
        r"\d+(?:\.\d+)?\s*(?:inch|inches|in)\b",

        r"\b(?:up to|max(?:imum)?|no more than)\s+"
        r"\d+(?:\.\d+)?\s*(?:inch|inches|in)\b",

        # Rating
        r"\b(?:at least|minimum|min)"
        r"\s+\d+(?:\.\d+)?\s*(?:star|stars)?"
        r"(?:\s+(?:rating|rated))?\b",
    ]

    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )

    # Do not remove brands entirely; brand names can also be
    # semantically useful.
    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    return cleaned


# ============================================================
# PREFERENCE TERM EXTRACTION
# ============================================================

PREFERENCE_SYNONYMS = {
    "coding": [
        "coding",
        "programming",
        "software development",
        "developer",
        "development",
    ],

    "gaming": [
        "gaming",
        "gamer",
        "games",
        "gaming laptop",
    ],

    "video editing": [
        "video editing",
        "video editor",
        "editing videos",
        "premiere pro",
        "davinci resolve",
        "after effects",
    ],

    "3d": [
        "3d",
        "3d modelling",
        "3d modeling",
        "blender",
        "rendering",
    ],

    "student": [
        "student",
        "college",
        "university",
        "school",
        "campus",
    ],

    "business": [
        "business",
        "office",
        "professional",
        "work",
        "productivity",
    ],

    "lightweight": [
        "lightweight",
        "light weight",
        "portable",
        "easy to carry",
        "travel",
        "travelling",
    ],

    "battery": [
        "battery life",
        "long battery",
        "battery backup",
    ],

    "performance": [
        "performance",
        "powerful",
        "high performance",
        "fast",
        "speed",
    ],

    "display": [
        "display",
        "screen",
        "color accurate",
        "colour accurate",
        "high resolution",
    ],
}


def extract_preference_terms(
    text: str,
) -> List[str]:

    found = []

    for canonical, synonyms in PREFERENCE_SYNONYMS.items():

        for synonym in synonyms:

            if re.search(
                rf"(?<![a-z0-9])"
                rf"{re.escape(synonym)}"
                rf"(?![a-z0-9])",
                text,
                re.IGNORECASE,
            ):
                found.append(
                    canonical
                )
                break

    return deduplicate_preserve_order(
        found
    )


# ============================================================
# QUERY INTERPRETATION
# ============================================================

def parse_user_query(
    query: str,
) -> QueryInterpretation:

    original_query = normalize_query(
        query
    )

    if not original_query:
        raise ValueError(
            "User query cannot be empty."
        )

    filters = RetrievalFilters()

    extracted_constraints: List[str] = []

    # --------------------------------------------------------
    # Extract hard constraints
    # --------------------------------------------------------

    extracted_constraints.extend(
        extract_price_filters(
            original_query,
            filters,
        )
    )

    extracted_constraints.extend(
        extract_ram_filter(
            original_query,
            filters,
        )
    )

    extracted_constraints.extend(
        extract_storage_filters(
            original_query,
            filters,
        )
    )

    extracted_constraints.extend(
        extract_screen_filter(
            original_query,
            filters,
        )
    )

    extracted_constraints.extend(
        extract_weight_filter(
            original_query,
            filters,
        )
    )

    extracted_constraints.extend(
        extract_rating_filter(
            original_query,
            filters,
        )
    )

    extracted_constraints.extend(
        extract_feature_filters(
            original_query,
            filters,
        )
    )

    extract_brands(
        original_query,
        filters,
    )

    # --------------------------------------------------------
    # Semantic preferences
    # --------------------------------------------------------

    preference_terms = extract_preference_terms(
        original_query
    )

    # --------------------------------------------------------
    # Build semantic query
    # --------------------------------------------------------

    semantic_query = remove_constraint_phrases(
        original_query
    )

    # Remove overly repetitive terms.
    semantic_query = re.sub(
        r"\b(?:please|find|show|give|me|want|need|i|am|looking|for)\b",
        " ",
        semantic_query,
        flags=re.IGNORECASE,
    )

    semantic_query = re.sub(
        r"\s+",
        " ",
        semantic_query,
    ).strip()

    # Never let constraint extraction accidentally empty the
    # semantic query completely.
    if not semantic_query:
        semantic_query = original_query

    return QueryInterpretation(
        original_query=original_query,
        semantic_query=semantic_query,
        filters=filters,
        preference_terms=preference_terms,
        extracted_constraints=(
            deduplicate_preserve_order(
                extracted_constraints
            )
        ),
    )


# ============================================================
# CHROMA FILTER CONSTRUCTION
# ============================================================

def build_where_filter(
    filters: RetrievalFilters,
) -> Optional[Dict[str, Any]]:
    """
    Convert structured RetrievalFilters into Chroma's metadata
    filter syntax.
    """
    conditions: List[Dict[str, Any]] = []

    # Brand
    if filters.brands:
        if len(filters.brands) == 1:
            conditions.append(
                {
                    "brand": filters.brands[0]
                }
            )
        else:
            conditions.append(
                {
                    "brand": {
                        "$in": filters.brands
                    }
                }
            )

    # Price
    if filters.min_price is not None:
        conditions.append(
            {
                "price_inr": {
                    "$gte": float(
                        filters.min_price
                    )
                }
            }
        )

    if filters.max_price is not None:
        conditions.append(
            {
                "price_inr": {
                    "$lte": float(
                        filters.max_price
                    )
                }
            }
        )

    # RAM
    if filters.min_ram_gb is not None:
        conditions.append(
            {
                "ram_gb": {
                    "$gte": float(
                        filters.min_ram_gb
                    )
                }
            }
        )

    if filters.max_ram_gb is not None:
        conditions.append(
            {
                "ram_gb": {
                    "$lte": float(
                        filters.max_ram_gb
                    )
                }
            }
        )

    # Storage
    if filters.min_storage_gb is not None:
        conditions.append(
            {
                "storage_gb": {
                    "$gte": float(
                        filters.min_storage_gb
                    )
                }
            }
        )

    if filters.max_storage_gb is not None:
        conditions.append(
            {
                "storage_gb": {
                    "$lte": float(
                        filters.max_storage_gb
                    )
                }
            }
        )

    # Screen
    if filters.min_screen_size is not None:
        conditions.append(
            {
                "screen_size_inch": {
                    "$gte": float(
                        filters.min_screen_size
                    )
                }
            }
        )

    if filters.max_screen_size is not None:
        conditions.append(
            {
                "screen_size_inch": {
                    "$lte": float(
                        filters.max_screen_size
                    )
                }
            }
        )

    # Weight
    if filters.min_weight_kg is not None:
        conditions.append(
            {
                "weight_kg": {
                    "$gte": float(
                        filters.min_weight_kg
                    )
                }
            }
        )

    if filters.max_weight_kg is not None:
        conditions.append(
            {
                "weight_kg": {
                    "$lte": float(
                        filters.max_weight_kg
                    )
                }
            }
        )

    # Rating
    if filters.min_rating is not None:
        conditions.append(
            {
                "rating_score": {
                    "$gte": float(
                        filters.min_rating
                    )
                }
            }
        )

    # Boolean fields
    if filters.dedicated_graphics is not None:
        conditions.append(
            {
                "dedicated_graphics": filters.dedicated_graphics
            }
        )

    if filters.touch_screen is not None:
        conditions.append(
            {
                "touch_screen": filters.touch_screen
            }
        )

    if filters.fingerprint_sensor is not None:
        conditions.append(
            {
                "fingerprint_sensor": (
                    filters.fingerprint_sensor
                )
            }
        )

    # Storage type
    if filters.storage_types:
        if len(filters.storage_types) == 1:
            conditions.append(
                {
                    "storage_type": filters.storage_types[0]
                }
            )
        else:
            conditions.append(
                {
                    "storage_type": {
                        "$in": filters.storage_types
                    }
                }
            )

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {
        "$and": conditions
    }


# ============================================================
# COLLECTION
# ============================================================

def create_embedding_function(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
):
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name
    )


def get_collection(
    persist_dir: Path,
    collection_name: str,
    embedding_model: str,
):
    if not persist_dir.exists():
        raise FileNotFoundError(
            "Vector database does not exist: "
            + str(persist_dir)
        )

    embedding_function = (
        create_embedding_function(
            embedding_model
        )
    )

    client = chromadb.PersistentClient(
        path=str(persist_dir)
    )

    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=embedding_function,
        )

    except Exception as exc:
        raise RuntimeError(
            f"Could not open Chroma collection "
            f"'{collection_name}'. "
            f"Make sure Task 2 indexing completed successfully."
        ) from exc

    if collection.count() == 0:
        raise RuntimeError(
            f"Chroma collection '{collection_name}' is empty."
        )

    return collection


# ============================================================
# RESULT CONVERSION
# ============================================================

def distance_to_similarity(
    distance: Optional[float],
) -> Optional[float]:
    """
    Convert a non-negative distance into a bounded similarity-like
    score for display/diagnostics.

    This should NOT be treated as a universal probability.
    """
    if distance is None:
        return None

    try:
        distance = float(distance)
    except (TypeError, ValueError):
        return None

    if distance < 0:
        return None

    return round(
        1.0 / (1.0 + distance),
        6,
    )


def convert_results(
    raw_results: Dict[str, Any],
) -> List[RetrievalResult]:

    ids = (
        raw_results.get("ids", [[]])[0]
    )

    documents = (
        raw_results.get("documents", [[]])[0]
    )

    metadatas = (
        raw_results.get("metadatas", [[]])[0]
    )

    distances = (
        raw_results.get("distances", [[]])[0]
    )

    results = []

    for index, product_id in enumerate(ids):

        document = (
            documents[index]
            if index < len(documents)
            else ""
        )

        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        distance = (
            distances[index]
            if index < len(distances)
            else None
        )

        results.append(
            RetrievalResult(
                product_id=str(product_id),
                document=str(document),
                metadata=metadata or {},
                distance=distance,
                similarity=distance_to_similarity(
                    distance
                ),
            )
        )

    return results


# ============================================================
# LOCAL GPU KEYWORD CHECK
# ============================================================

def metadata_matches_gpu_keywords(
    metadata: Dict[str, Any],
    gpu_keywords: Sequence[str],
) -> bool:

    if not gpu_keywords:
        return True

    gpu_text = str(
        metadata.get(
            "graphics_processor",
            ""
        )
    ).lower()

    if not gpu_text:
        return False

    return any(
        keyword.lower() in gpu_text
        for keyword in gpu_keywords
    )


def apply_local_non_chroma_constraints(
    results: List[RetrievalResult],
    filters: RetrievalFilters,
) -> List[RetrievalResult]:

    if not filters.gpu_keywords:
        return results

    return [
        result
        for result in results
        if metadata_matches_gpu_keywords(
            result.metadata,
            filters.gpu_keywords,
        )
    ]


# ============================================================
# RETRIEVAL ENGINE
# ============================================================

class RetrievalEngine:
    """
    Omni-channel hybrid retrieval engine.
    """

    def __init__(
        self,
        persist_dir: Path = DEFAULT_VECTOR_DB,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self.persist_dir = Path(persist_dir)
        self.embedding_model = embedding_model

    def get_target_collection(self, category: str):
        # Determine the collection name (e.g., "laptop" -> "laptops")
        collection_name = f"{category}s" if not category.endswith('s') else category
        return get_collection(
            persist_dir=self.persist_dir,
            collection_name=collection_name,
            embedding_model=self.embedding_model,
        )

    def search(
        self,
        user_query: str,
        category: str = "laptop",  # Added dynamic category routing
        top_k: int = DEFAULT_TOP_K,
        candidate_multiplier: int = DEFAULT_CANDIDATE_MULTIPLIER,
    ) -> RetrievalResponse:

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if candidate_multiplier <= 0:
            raise ValueError("candidate_multiplier must be greater than zero.")

        interpretation = parse_user_query(user_query)
        where_filter = build_where_filter(interpretation.filters)
        
        # Dynamically switch the active ChromaDB collection
        active_collection = self.get_target_collection(category)

        candidate_k = max(top_k * candidate_multiplier, top_k)
        candidate_k = min(candidate_k, active_collection.count())

        query_kwargs: Dict[str, Any] = {
            "query_texts": [interpretation.semantic_query],
            "n_results": candidate_k,
            "include": ["documents", "metadatas", "distances"],
        }

        if where_filter is not None:
            query_kwargs["where"] = where_filter

        raw_results = active_collection.query(**query_kwargs)
        results = convert_results(raw_results)

        results = apply_local_non_chroma_constraints(
            results,
            interpretation.filters,
        )

        results = results[:top_k]

        for result in results:
            result.matched_filters = self._get_matched_filter_metadata(
                result.metadata,
                interpretation.filters,
            )

        return RetrievalResponse(
            query=interpretation,
            results=results,
            filters_applied=where_filter is not None,
            filter_expression=where_filter,
            candidate_count=len(results),
        )

    @staticmethod
    def _get_matched_filter_metadata(
        metadata: Dict[str, Any],
        filters: RetrievalFilters,
    ) -> Dict[str, Any]:
        matched = {}
        if filters.brands: matched["brand"] = metadata.get("brand")
        if filters.min_price is not None: matched["price_inr"] = metadata.get("price_inr")
        if filters.min_ram_gb is not None: matched["ram_gb"] = metadata.get("ram_gb")
        if filters.min_storage_gb is not None: matched["storage_gb"] = metadata.get("storage_gb")
        return matched
# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def retrieve_products(
    user_query: str,
    category: str = "laptop",
    top_k: int = DEFAULT_TOP_K,
    persist_dir: Path = DEFAULT_VECTOR_DB,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> RetrievalResponse:

    engine = RetrievalEngine(
        persist_dir=persist_dir,
        embedding_model=embedding_model,
    )

    return engine.search(
        user_query=user_query,
        category=category,
        top_k=top_k,
    )
# ============================================================
# HUMAN-READABLE DIAGNOSTICS
# ============================================================

def print_response(
    response: RetrievalResponse,
) -> None:

    print("\n" + "=" * 72)
    print("VER2 HYBRID RETRIEVAL")
    print("=" * 72)

    print(
        "\nOriginal query:",
        response.query.original_query,
    )

    print(
        "\nSemantic query:",
        response.query.semantic_query,
    )

    print(
        "\nPreferences:",
        response.query.preference_terms,
    )

    print(
        "\nExtracted constraints:"
    )

    if response.query.extracted_constraints:
        for constraint in (
            response.query.extracted_constraints
        ):
            print(
                "  -",
                constraint,
            )
    else:
        print("  None")

    print(
        "\nMetadata filter:"
    )

    if response.filter_expression:
        print(
            response.filter_expression
        )
    else:
        print("  None")

    print(
        "\nCandidates:",
        response.candidate_count,
    )

    if not response.results:
        print(
            "\nNo products matched the requested constraints."
        )

        return

    print(
        "\nResults:"
    )

    for index, result in enumerate(
        response.results,
        start=1,
    ):

        metadata = result.metadata

        print(
            f"\n{index}. "
            f"{result.product_id}"
        )

        print(
            "   Brand:",
            metadata.get("brand", "Unknown"),
        )

        print(
            "   Product:",
            metadata.get(
                "product_name",
                "Unknown",
            ),
        )

        print(
            "   Processor:",
            metadata.get(
                "processor",
                "Unknown",
            ),
        )

        print(
            "   RAM:",
            metadata.get(
                "ram_gb",
                "Unknown",
            ),
        )

        print(
            "   Price:",
            metadata.get(
                "price_inr",
                "Unknown",
            ),
        )

        print(
            "   Distance:",
            result.distance,
        )

        print(
            "   Similarity:",
            result.similarity,
        )


# ============================================================
# CLI
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Run the ver2 omni-channel hybrid retrieval engine."
        )
    )

    parser.add_argument(
        "query",
        nargs="*",
        help="Natural-language product query.",
    )

    parser.add_argument(
        "--category",
        type=str,
        default="laptop",
        help="The product category to search (e.g., laptop, mobile, tablet).",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_VECTOR_DB,
    )

    parser.add_argument(
        "--embedding-model",
        type=str,
        default=DEFAULT_EMBEDDING_MODEL,
    )

    args = parser.parse_args()

    query = " ".join(
        args.query
    ).strip()

    if not query:
        query = input(
            f"Enter {args.category} query: "
        ).strip()

    response = retrieve_products(
        user_query=query,
        category=args.category.lower(),
        top_k=args.top_k,
        persist_dir=args.db,
        embedding_model=args.embedding_model,
    )

    print_response(
        response
    )


if __name__ == "__main__":
    main()