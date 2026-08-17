from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass,  field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from retrieval_engine import (
    DEFAULT_COLLECTION,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    DEFAULT_VECTOR_DB,
    RetrievalEngine,
    RetrievalResult,
    RetrievalResponse,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_MAX_PRODUCTS = 10

DEFAULT_TABLE_COLUMNS = (
    "product_name",
    "brand",
    "processor",
    "ram_gb",
    "storage_gb",
    "storage_type",
    "graphics_processor",
    "dedicated_graphics",
    "screen_size_inch",
    "weight_kg",
    "price_inr",
    "rating_score",
)


# ============================================================
# DATA CONTRACTS
# ============================================================
@dataclass
class ProductRecord:
    """Clean, frontend-friendly representation of one product."""
    product_id: str
    product_name: Optional[str]
    brand: Optional[str]
    price_inr: Optional[float]
    rating_score: Optional[float]
    total_ratings: Optional[int]

    # Computing / Shared
    processor: Optional[str]
    ram_gb: Optional[float]
    storage_gb: Optional[float]
    screen_size_inch: Optional[float]
    weight_kg: Optional[float]
    resolution_width: Optional[int]
    resolution_height: Optional[int]

    # Laptop Specific
    storage_type: Optional[str] = None
    graphics_processor: Optional[str] = None
    dedicated_graphics: Optional[bool] = None

    # Mobile/Tablet Specific
    battery_capacity_mah: Optional[float] = None
    rear_camera_mp: Optional[float] = None
    front_camera_mp: Optional[float] = None
    os_family: Optional[str] = None

    similarity: Optional[float] = None
    distance: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonTable:
    """
    Deterministic table representation.
    """

    columns: List[str]

    rows: List[Dict[str, Any]]


@dataclass
class RAGResponse:
    """
    Complete output of rag_chain.py.

    This object is suitable for:
        - chatbot.py
        - REST API
        - React frontend
        - tests
        - evaluation
    """

    query: str

    semantic_query: str

    filters: Dict[str, Any]

    preferences: List[str]

    candidate_count: int

    products: List[ProductRecord]

    table: ComparisonTable

    markdown_table: str

    factual_context: str

    no_results: bool


# ============================================================
# SAFE VALUE HELPERS
# ============================================================

def safe_float(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        number = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(number):
        return None

    return number


def safe_int(
    value: Any,
) -> Optional[int]:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        number = int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    return number


def safe_bool(
    value: Any,
) -> Optional[bool]:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        (int, float),
    ):
        if value == 1:
            return True

        if value == 0:
            return False

    text = str(
        value
    ).strip().lower()

    if text in {
        "true",
        "yes",
        "1",
        "y",
    }:
        return True

    if text in {
        "false",
        "no",
        "0",
        "n",
    }:
        return False

    return None


def clean_text(
    value: Any,
) -> Optional[str]:

    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    return text


# ============================================================
# METADATA ACCESS
# ============================================================

def get_first(
    metadata: Dict[str, Any],
    keys: Sequence[str],
) -> Any:

    for key in keys:

        if key in metadata:

            value = metadata[key]

            if value is not None:
                return value

    return None


# ============================================================
# PRODUCT CONVERSION
# ============================================================

def result_to_product(result: RetrievalResult) -> ProductRecord:
    metadata = dict(result.metadata or {})

    return ProductRecord(
        product_id=str(result.product_id),
        product_name=clean_text(get_first(metadata, ("product_name", "model", "name"))),
        brand=clean_text(get_first(metadata, ("brand", "Brand"))),
        price_inr=safe_float(get_first(metadata, ("price_inr", "price", "Price"))),
        rating_score=safe_float(get_first(metadata, ("rating_score", "rating"))),
        total_ratings=safe_int(get_first(metadata, ("total_ratings", "ratings_count"))),
        
        processor=clean_text(get_first(metadata, ("processor", "Processor", "cpu"))),
        ram_gb=safe_float(get_first(metadata, ("ram_gb", "ram"))),
        storage_gb=safe_float(get_first(metadata, ("storage_gb", "storage", "internal_storage_gb"))),
        screen_size_inch=safe_float(get_first(metadata, ("screen_size_inch", "screen_size"))),
        weight_kg=safe_float(get_first(metadata, ("weight_kg", "weight_g"))), # Note: Mobiles use weight_g
        resolution_width=safe_int(get_first(metadata, ("resolution_width", "screen_width"))),
        resolution_height=safe_int(get_first(metadata, ("resolution_height", "screen_height"))),

        storage_type=clean_text(get_first(metadata, ("storage_type", "Storage_Type"))),
        graphics_processor=clean_text(get_first(metadata, ("graphics_processor", "gpu"))),
        dedicated_graphics=safe_bool(get_first(metadata, ("dedicated_graphics", "Dedicated_Graphics"))),

        # NEW: Mobile/Tablet extraction
        battery_capacity_mah=safe_float(get_first(metadata, ("battery_capacity_mah", "battery"))),
        rear_camera_mp=safe_float(get_first(metadata, ("rear_camera_mp", "primary_rear_camera_mp"))),
        front_camera_mp=safe_float(get_first(metadata, ("front_camera_mp", "primary_front_camera_mp"))),
        os_family=clean_text(get_first(metadata, ("os_family", "operating_system"))),

        similarity=result.similarity,
        distance=safe_float(result.distance),
        metadata=metadata,
    )


def convert_results(
    results: Iterable[RetrievalResult],
) -> List[ProductRecord]:

    products = []

    seen_ids = set()

    for result in results:

        product = result_to_product(
            result
        )

        if product.product_id in seen_ids:
            continue

        seen_ids.add(
            product.product_id
        )

        products.append(
            product
        )

    return products


# ============================================================
# VALUE NORMALIZATION
# ============================================================

def format_price(
    value: Optional[float],
) -> str:

    if value is None:
        return "N/A"

    return (
        "₹"
        + f"{value:,.0f}"
    )


def format_number(
    value: Any,
    decimals: int = 1,
) -> str:

    if value is None:
        return "N/A"

    try:
        number = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return "N/A"

    if not math.isfinite(number):
        return "N/A"

    if decimals == 0:
        return f"{number:.0f}"

    return f"{number:.{decimals}f}"


def format_bool(
    value: Optional[bool],
) -> str:

    if value is None:
        return "N/A"

    return (
        "Yes"
        if value
        else "No"
    )


def format_rating(
    rating: Optional[float],
) -> str:

    if rating is None:
        return "N/A"

    return (
        f"{rating:.1f}/5"
    )


# ============================================================
# TABLE ROW GENERATION
# ============================================================

COLUMN_LABELS = {
    "product_name": "Product",
    "brand": "Brand",
    "processor": "Processor",
    "ram_gb": "RAM",
    "storage_gb": "Storage",
    "storage_type": "Storage Type",
    "graphics_processor": "Graphics",
    "dedicated_graphics": "Dedicated GPU",
    "screen_size_inch": "Screen",
    "weight_kg": "Weight",
    "price_inr": "Price",
    "rating_score": "Rating",
    "total_ratings": "Ratings",
    "resolution_width": "Resolution Width",
    "resolution_height": "Resolution Height",
}


def product_to_row(
    product: ProductRecord,
    columns: Sequence[str],
) -> Dict[str, Any]:

    row: Dict[str, Any] = {}

    for column in columns:

        value = getattr(
            product,
            column,
            None,
        )

        if column == "price_inr":
            value = format_price(
                value
            )

        elif column == "ram_gb":
            value = (
                format_number(
                    value,
                    0,
                )
                + (
                    ""
                    if value is None
                    else " GB"
                )
            )

        elif column == "storage_gb":
            value = (
                format_number(
                    value,
                    0,
                )
                + (
                    ""
                    if value is None
                    else " GB"
                )
            )

        elif column == "screen_size_inch":
            value = (
                format_number(
                    value,
                    1,
                )
                + (
                    ""
                    if value is None
                    else '"'
                )
            )

        elif column == "weight_kg":
            value = (
                format_number(
                    value,
                    2,
                )
                + (
                    ""
                    if value is None
                    else " kg"
                )
            )

        elif column == "rating_score":
            value = format_rating(
                value
            )

        elif column == "dedicated_graphics":
            value = format_bool(
                value
            )

        elif column in {
            "total_ratings",
            "resolution_width",
            "resolution_height",
        }:
            value = (
                "N/A"
                if value is None
                else str(value)
            )

        else:
            value = (
                "N/A"
                if value is None
                else str(value)
            )

        row[column] = value

    return row


def build_comparison_table(
    products: Sequence[ProductRecord],
    columns: Sequence[str] = DEFAULT_TABLE_COLUMNS,
) -> ComparisonTable:

    valid_columns = []

    for column in columns:

        if column not in COLUMN_LABELS:
            continue

        # FIX: Correctly check if the column exists in the dataclass
        if column not in ProductRecord.__dataclass_fields__:
            continue

        valid_columns.append(
            column
        )

    rows = [
        product_to_row(
            product,
            valid_columns,
        )
        for product in products
    ]

    return ComparisonTable(
        columns=list(
            valid_columns
        ),
        rows=rows,
    )

# ============================================================
# MARKDOWN TABLE
# ============================================================

def escape_markdown(
    value: Any,
) -> str:

    text = str(
        value
        if value is not None
        else "N/A"
    )

    return text.replace(
        "|",
        "\\|",
    ).replace(
        "\n",
        " ",
    )


def build_markdown_table(
    table: ComparisonTable,
) -> str:

    if not table.columns:
        return ""

    headers = [
        COLUMN_LABELS[column]
        for column in table.columns
    ]

    lines = []

    lines.append(
        "| "
        + " | ".join(headers)
        + " |"
    )

    lines.append(
        "| "
        + " | ".join(
            "---"
            for _ in headers
        )
        + " |"
    )

    for row in table.rows:

        values = [
            escape_markdown(
                row.get(
                    column,
                    "N/A",
                )
            )
            for column in table.columns
        ]

        lines.append(
            "| "
            + " | ".join(values)
            + " |"
        )

    return "\n".join(
        lines
    )


# ============================================================
# FACTUAL CONTEXT
# ============================================================

def build_factual_context(
    products: Sequence[ProductRecord],
) -> str:
    """
    Build compact factual context for chatbot.py.

    This contains ONLY database-derived fields.

    It is deliberately not written as persuasive prose.
    """

    if not products:
        return (
            "No matching products were retrieved."
        )

    lines = []

    for index, product in enumerate(
        products,
        start=1,
    ):

        lines.append(
            f"PRODUCT {index}"
        )

        lines.append(
            f"product_id: {product.product_id}"
        )

        if product.product_name is not None:
            lines.append(
                f"product_name: "
                f"{product.product_name}"
            )

        if product.brand is not None:
            lines.append(
                f"brand: {product.brand}"
            )

        if product.processor is not None:
            lines.append(
                f"processor: {product.processor}"
            )

        if product.ram_gb is not None:
            lines.append(
                f"ram_gb: {product.ram_gb}"
            )

        if product.storage_gb is not None:
            lines.append(
                f"storage_gb: {product.storage_gb}"
            )

        if product.storage_type is not None:
            lines.append(
                f"storage_type: "
                f"{product.storage_type}"
            )

        if product.graphics_processor is not None:
            lines.append(
                f"graphics_processor: "
                f"{product.graphics_processor}"
            )

        if product.dedicated_graphics is not None:
            lines.append(
                f"dedicated_graphics: "
                f"{product.dedicated_graphics}"
            )

        if product.screen_size_inch is not None:
            lines.append(
                f"screen_size_inch: "
                f"{product.screen_size_inch}"
            )

        if product.weight_kg is not None:
            lines.append(
                f"weight_kg: "
                f"{product.weight_kg}"
            )

        if product.price_inr is not None:
            lines.append(
                f"price_inr: "
                f"{product.price_inr}"
            )

        if product.rating_score is not None:
            lines.append(
                f"rating_score: "
                f"{product.rating_score}"
            )

        if product.total_ratings is not None:
            lines.append(
                f"total_ratings: "
                f"{product.total_ratings}"
            )

        if product.resolution_width is not None:
            lines.append(
                f"resolution_width: "
                f"{product.resolution_width}"
            )

        if product.resolution_height is not None:
            lines.append(
                f"resolution_height: "
                f"{product.resolution_height}"
            )

        lines.append(
            f"semantic_similarity: "
            f"{product.similarity}"
        )

        lines.append(
            ""
        )

    return "\n".join(
        lines
    ).strip()


# ============================================================
# SERIALIZATION
# ============================================================

def product_to_dict(
    product: ProductRecord,
) -> Dict[str, Any]:

    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "brand": product.brand,
        "processor": product.processor,
        "ram_gb": product.ram_gb,
        "storage_gb": product.storage_gb,
        "storage_type": product.storage_type,
        "graphics_processor": (
            product.graphics_processor
        ),
        "dedicated_graphics": (
            product.dedicated_graphics
        ),
        "screen_size_inch": (
            product.screen_size_inch
        ),
        "weight_kg": product.weight_kg,
        "price_inr": product.price_inr,
        "rating_score": product.rating_score,
        "total_ratings": product.total_ratings,
        "resolution_width": (
            product.resolution_width
        ),
        "resolution_height": (
            product.resolution_height
        ),
        "similarity": product.similarity,
        "distance": product.distance,

        # Useful for debugging and future UI details.
        "metadata": product.metadata,
    }


# ============================================================
# MAIN RAG CHAIN
# ============================================================

class RAGChain:
    """Deterministic Multi-Category RAG presentation pipeline."""

    def __init__(
        self,
        vector_db: Path = DEFAULT_VECTOR_DB,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self.engine = RetrievalEngine(
            persist_dir=vector_db,
            embedding_model=embedding_model,
        )

    def run(
        self,
        user_query: str,
        category: str = "laptop", # <-- ADDED CATEGORY
        top_k: int = DEFAULT_TOP_K,
        columns: Sequence[str] = DEFAULT_TABLE_COLUMNS,
    ) -> RAGResponse:

        if not str(user_query or "").strip():
            raise ValueError("user_query cannot be empty.")

        # Pass category to the upgraded engine
        retrieval = self.engine.search(
            user_query=user_query,
            category=category, 
            top_k=top_k,
        )

        products = convert_results(retrieval.results)

        table = build_comparison_table(products=products, columns=columns)
        markdown_table = build_markdown_table(table)
        factual_context = build_factual_context(products)
        filters = asdict(retrieval.query.filters)

        return RAGResponse(
            query=retrieval.query.original_query,
            semantic_query=retrieval.query.semantic_query,
            filters=filters,
            preferences=list(retrieval.query.preference_terms),
            candidate_count=len(products),
            products=products,
            table=table,
            markdown_table=markdown_table,
            factual_context=factual_context,
            no_results=(len(products) == 0),
        )
# ============================================================
# JSON API OUTPUT
# ============================================================

def response_to_dict(
    response: RAGResponse,
) -> Dict[str, Any]:

    return {
        "query": response.query,

        "semantic_query": (
            response.semantic_query
        ),

        "filters": response.filters,

        "preferences": response.preferences,

        "candidate_count": (
            response.candidate_count
        ),

        "no_results": (
            response.no_results
        ),

        "products": [
            product_to_dict(
                product
            )
            for product in response.products
        ],

        "table": {
            "columns": response.table.columns,
            "rows": response.table.rows,
        },

        "markdown_table": (
            response.markdown_table
        ),

        "factual_context": (
            response.factual_context
        ),
    }


# ============================================================
# OUTPUT HELPERS
# ============================================================

def save_json(
    response: RAGResponse,
    output_path: Path,
) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            response_to_dict(
                response
            ),
            file,
            indent=2,
            ensure_ascii=False,
        )


def print_response(
    response: RAGResponse,
) -> None:

    print(
        "\n"
        + "=" * 72
    )

    print(
        "VER2 - DETERMINISTIC RAG CHAIN"
    )

    print(
        "=" * 72
    )

    print(
        "\nQuery:",
        response.query,
    )

    print(
        "Semantic query:",
        response.semantic_query,
    )

    print(
        "Candidates:",
        response.candidate_count,
    )

    print(
        "No results:",
        response.no_results,
    )

    print(
        "\nExtracted filters:"
    )

    for key, value in response.filters.items():

        if value is None:
            continue

        if value == []:
            continue

        print(
            f"  {key}: {value}"
        )

    print(
        "\nPreferences:"
    )

    if response.preferences:
        for preference in response.preferences:
            print(
                "  -",
                preference,
            )
    else:
        print(
            "  None"
        )

    if response.no_results:

        print(
            "\nNo matching products."
        )

        return

    print(
        "\nComparison table:"
    )

    print(
        response.markdown_table
    )

    print(
        "\nFactual context:"
    )

    print(
        response.factual_context
    )
# ============================================================
# CLI
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Run the ver2 deterministic multi-category RAG chain."
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
        help="The product category to search (e.g., laptop, mobile, tablet)."
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

    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    query = " ".join(
        args.query
    ).strip()

    if not query:
        query = input(
            f"Enter {args.category} query: "
        ).strip()

    # REMOVED collection_name from initialization
    chain = RAGChain(
        vector_db=args.db,
        embedding_model=args.embedding_model,
    )

    # ADDED category to the run method
    response = chain.run(
        user_query=query,
        category=args.category.lower(),
        top_k=args.top_k,
    )

    print_response(
        response
    )

    if args.json_output is not None:

        save_json(
            response,
            args.json_output,
        )

        print(
            "\nJSON saved to:",
            args.json_output,
        )


if __name__ == "__main__":
    main()