from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Replaced hardcoded paths with dynamic generation functions
def get_corpus_path(category: str) -> Path:
    return PROJECT_ROOT / "data" / "processed" / f"{category}_rag_corpus.json"

def get_collection_name(category: str) -> str:
    return f"{category}s" if not category.endswith('s') else category

DEFAULT_DB = (
    PROJECT_ROOT
    / "data"
    / "vector_db"
)

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DEFAULT_BATCH_SIZE = 100


# ============================================================
# EMBEDDING CONFIGURATION
# ============================================================

def create_embedding_function(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
):
    """
    Create the embedding function used by both indexing and
    retrieval.

    IMPORTANT:
    retrieval_engine.py must use the same model.
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name
    )


# ============================================================
# JSON LOADING
# ============================================================

def load_corpus(
    corpus_path: Path,
) -> List[Dict[str, Any]]:
    """
    Load and validate the preprocessed RAG corpus.
    """
    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Corpus file does not exist: {corpus_path}"
        )

    if corpus_path.stat().st_size == 0:
        raise ValueError(
            f"Corpus file is empty: {corpus_path}"
        )

    try:
        with corpus_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON corpus: {corpus_path}"
        ) from exc

    if not isinstance(data, list):
        raise ValueError(
            "RAG corpus must contain a JSON list."
        )

    return data


# ============================================================
# METADATA VALIDATION
# ============================================================

def sanitize_metadata(
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Chroma metadata should contain scalar values.

    Keep valid False and 0 values.
    Remove None and unsupported structures.
    """
    sanitized = {}

    for key, value in metadata.items():

        if value is None:
            continue

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            sanitized[str(key)] = value
            continue

        # Convert simple values such as NumPy scalar types.
        if hasattr(value, "item"):
            try:
                converted = value.item()

                if isinstance(
                    converted,
                    (str, int, float, bool),
                ):
                    sanitized[str(key)] = converted

            except Exception:
                pass

    return sanitized


def validate_and_prepare_record(
    record: Dict[str, Any],
    category: str,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Validate one corpus record and convert it into the exact
    representation required by Chroma.
    """
    if not isinstance(record, dict):
        raise ValueError(
            "Each corpus entry must be an object."
        )

    product_id = record.get("id")
    document = record.get("text")
    metadata = record.get("metadata", {})

    if product_id is None:
        raise ValueError(
            "Corpus record is missing 'id'."
        )

    if document is None:
        raise ValueError(
            f"Product {product_id} is missing 'text'."
        )

    if not isinstance(metadata, dict):
        raise ValueError(
            f"Metadata for {product_id} must be an object."
        )

    product_id = str(product_id).strip()
    document = str(document).strip()

    if not product_id:
        raise ValueError(
            "Encountered an empty product ID."
        )

    if not document:
        raise ValueError(
            f"Product {product_id} has an empty document."
        )

    metadata = sanitize_metadata(metadata)

    # Guarantee that product_id exists in metadata too.
    metadata["product_id"] = product_id
    # Ensure category is present in metadata for multi-category safety
    metadata["category"] = category

    return product_id, document, metadata


# ============================================================
# CORPUS PREPARATION
# ============================================================

def prepare_records(
    corpus: Iterable[Dict[str, Any]],
    category: str,
) -> Tuple[
    List[str],
    List[str],
    List[Dict[str, Any]],
]:
    """
    Convert the full JSON corpus into three aligned lists:
        IDs
        documents
        metadatas

    Duplicate IDs are rejected instead of silently overwriting
    products.
    """
    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    seen_ids = set()

    for index, record in enumerate(corpus):

        try:
            product_id, document, metadata = (
                validate_and_prepare_record(record, category)
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid corpus record at index {index}: {exc}"
            ) from exc

        if product_id in seen_ids:
            raise ValueError(
                f"Duplicate product ID detected: {product_id}"
            )

        seen_ids.add(product_id)

        ids.append(product_id)
        documents.append(document)
        metadatas.append(metadata)

    if not ids:
        raise ValueError(
            "The processed corpus contains no valid products."
        )

    return ids, documents, metadatas


# ============================================================
# BATCHING
# ============================================================

def batch_items(
    ids: List[str],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    batch_size: int,
):
    """
    Yield aligned batches.
    """
    if batch_size <= 0:
        raise ValueError(
            "batch_size must be greater than zero."
        )

    for start in range(
        0,
        len(ids),
        batch_size,
    ):
        end = start + batch_size

        yield (
            ids[start:end],
            documents[start:end],
            metadatas[start:end],
        )


# ============================================================
# CHROMA CONNECTION
# ============================================================

def create_client(
    persist_dir: Path,
):
    """
    Create a persistent local Chroma client.
    """
    persist_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False)
    )


def get_or_create_collection(
    client,
    collection_name: str,
    embedding_function,
):
    """
    Get an existing collection or create it.

    The embedding function is explicitly attached so indexing
    and querying use the intended model.
    """
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )


# ============================================================
# COLLECTION INFORMATION
# ============================================================

def collection_count(
    collection,
) -> int:
    """
    Safely retrieve collection size.
    """
    return int(collection.count())


# ============================================================
# RESET COLLECTION ONLY
# ============================================================

def reset_collection(
    persist_dir: Path,
    collection_name: str,
) -> None:
    """
    Delete only the specified Chroma collection.

    The surrounding database remains available.
    """
    if not persist_dir.exists():
        print(
            "Vector DB does not exist:",
            persist_dir,
        )
        return

    client = create_client(
        persist_dir
    )

    try:
        client.delete_collection(
            name=collection_name
        )
    except Exception as exc:
        # A missing collection is harmless.
        message = str(exc).lower()

        if (
            "not found" not in message
            and "does not exist" not in message
        ):
            raise

    print(
        "Collection reset:",
        collection_name,
    )


# ============================================================
# INDEXING
# ============================================================

def index_corpus(
    category: str,
    corpus_path: Path,
    collection_name: str,
    persist_dir: Path = DEFAULT_DB,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    reset: bool = False,
) -> Dict[str, Any]:
    """
    Main indexing operation.

    Behavior:
      - reset=False:
            Existing IDs are updated with upsert().
      - reset=True:
            Only the specific collection is removed first.

    Returns a summary dictionary.
    """
    print("=" * 72)
    print(f"VER2 - CHROMA VECTOR STORE ({category.upper()})")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load corpus
    # --------------------------------------------------------

    print("\n[1/6] Loading processed corpus...")

    corpus = load_corpus(corpus_path)

    print(
        "Corpus records:",
        len(corpus),
    )

    # --------------------------------------------------------
    # 2. Prepare / validate records
    # --------------------------------------------------------

    print("\n[2/6] Validating corpus records...")

    ids, documents, metadatas = prepare_records(
        corpus, category
    )

    print(
        "Valid records:",
        len(ids),
    )

    # --------------------------------------------------------
    # 3. Create embedding function
    # --------------------------------------------------------

    print("\n[3/6] Initializing embedding model...")

    embedding_function = create_embedding_function(
        embedding_model
    )

    print(
        "Embedding model:",
        embedding_model,
    )

    # --------------------------------------------------------
    # 4. Create / reset database
    # --------------------------------------------------------

    print("\n[4/6] Initializing ChromaDB...")

    if reset and persist_dir.exists():
        print(
            f"Reset requested. Removing existing {collection_name} collection..."
        )
        # CRITICAL FIX: Safe isolated deletion instead of shutil.rmtree
        reset_collection(persist_dir, collection_name)

    client = create_client(
        persist_dir
    )

    collection = get_or_create_collection(
        client=client,
        collection_name=collection_name,
        embedding_function=embedding_function,
    )

    print(
        "Collection:",
        collection_name,
    )

    print(
        "Existing records:",
        collection_count(collection),
    )

    # --------------------------------------------------------
    # 5. Batch upsert
    # --------------------------------------------------------

    print("\n[5/6] Indexing products...")

    total = len(ids)
    batches = 0

    for batch_ids, batch_documents, batch_metadatas in batch_items(
        ids,
        documents,
        metadatas,
        batch_size,
    ):
        batches += 1

        print(
            f"  Batch {batches}: "
            f"{len(batch_ids)} products"
        )

        collection.upsert(
            ids=batch_ids,
            documents=batch_documents,
            metadatas=batch_metadatas,
        )

    # --------------------------------------------------------
    # 6. Verify
    # --------------------------------------------------------

    print("\n[6/6] Verifying index...")

    final_count = collection_count(
        collection
    )

    if final_count < total:
        raise RuntimeError(
            "Verification failed. "
            f"Expected at least {total} records, "
            f"but collection contains {final_count}."
        )

    print(
        "Expected products:",
        total,
    )

    print(
        "Collection products:",
        final_count,
    )

    print(
        "Database:",
        persist_dir,
    )

    print("\n" + "=" * 72)
    print("VECTOR STORE COMPLETE")
    print("=" * 72)

    return {
        "corpus_path": str(corpus_path),
        "persist_dir": str(persist_dir),
        "collection_name": collection_name,
        "embedding_model": embedding_model,
        "corpus_records": total,
        "collection_records": final_count,
        "batches": batches,
        "reset": reset,
    }


# ============================================================
# TEST QUERY
# ============================================================

def test_collection(
    persist_dir: Path,
    collection_name: str,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    query: str = "good options for heavy usage",
    n_results: int = 3,
) -> Dict[str, Any]:
    """
    Basic smoke test for the indexed collection.
    """
    if n_results <= 0:
        raise ValueError(
            "n_results must be greater than zero."
        )

    embedding_function = create_embedding_function(
        embedding_model
    )

    client = create_client(
        persist_dir
    )

    collection = client.get_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )

    count = collection_count(
        collection
    )

    if count == 0:
        raise ValueError(
            "Collection is empty."
        )

    result = collection.query(
        query_texts=[query],
        n_results=min(
            n_results,
            count,
        ),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    print("\n" + "=" * 72)
    print(f"VECTOR STORE SMOKE TEST ({collection_name.upper()})")
    print("=" * 72)

    documents = (
        result.get("documents", [[]])[0]
    )

    metadatas = (
        result.get("metadatas", [[]])[0]
    )

    distances = (
        result.get("distances", [[]])[0]
    )

    for index, document in enumerate(documents):

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

        print(
            f"\n{index + 1}. "
            f"{metadata.get('product_id', 'UNKNOWN')}"
        )

        print(
            "   Brand:",
            metadata.get("brand", "Unknown"),
        )

        print(
            "   Price:",
            metadata.get("price_inr", "Unknown"),
        )

        print(
            "   Distance:",
            distance,
        )

        print(
            "   Document:",
            document[:200],
            "...",
        )

    return result


# ============================================================
# CLI
# ============================================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and manage the ver2 ChromaDB vector store."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # -----------------------------
    # COMMON ARGUMENTS
    # -----------------------------
    # We add a parent parser for shared arguments like --category
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--category",
        type=str,
        default="laptop",
        help="Target category (e.g., laptop, mobile)"
    )

    # -----------------------------
    # INDEX
    # -----------------------------

    index_parser = subparsers.add_parser(
        "index",
        parents=[parent_parser],
        help="Index the processed RAG corpus.",
    )

    index_parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )

    index_parser.add_argument(
        "--embedding-model",
        type=str,
        default=DEFAULT_EMBEDDING_MODEL,
    )

    index_parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )

    index_parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and rebuild ONLY the target collection.",
    )

    # -----------------------------
    # RESET
    # -----------------------------

    reset_parser = subparsers.add_parser(
        "reset",
        parents=[parent_parser],
        help="Delete one Chroma collection.",
    )

    reset_parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )

    # -----------------------------
    # TEST
    # -----------------------------

    test_parser = subparsers.add_parser(
        "test",
        parents=[parent_parser],
        help="Run a vector retrieval smoke test.",
    )

    test_parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )

    test_parser.add_argument(
        "--embedding-model",
        type=str,
        default=DEFAULT_EMBEDDING_MODEL,
    )

    test_parser.add_argument(
        "--query",
        type=str,
        default="good options for heavy usage",
    )

    test_parser.add_argument(
        "--n-results",
        type=int,
        default=3,
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    args = parse_arguments()

    category = args.category.lower()
    corpus_path = get_corpus_path(category)
    collection_name = get_collection_name(category)

    if args.command == "index":

        index_corpus(
            category=category,
            corpus_path=corpus_path,
            collection_name=collection_name,
            persist_dir=args.db,
            embedding_model=args.embedding_model,
            batch_size=args.batch_size,
            reset=args.reset,
        )

    elif args.command == "reset":

        reset_collection(
            persist_dir=args.db,
            collection_name=collection_name,
        )

    elif args.command == "test":

        test_collection(
            persist_dir=args.db,
            collection_name=collection_name,
            embedding_model=args.embedding_model,
            query=args.query,
            n_results=args.n_results,
        )


if __name__ == "__main__":
    main()