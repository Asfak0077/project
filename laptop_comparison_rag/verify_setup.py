import pandas as pd
import chromadb
from chromadb.utils import embedding_functions

print("--- VERIFYING RAG ENVIRONMENT ---")

# 1. Verify Pandas
df_test = pd.DataFrame({"status": ["Pandas operational"]})
print(f"[OK] {df_test['status'][0]}")

# 2. Verify Sentence-Transformers Embedding Function (Local CPU Execution)
try:
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    test_vector = embedding_fn(["Laptop comparison test"])
    print(f"[OK] Embedding model loaded successfully. Vector size: {len(test_vector[0])} dimensions.")
except Exception as e:
    print(f"[FAIL] Embedding model error: {e}")

# 3. Verify ChromaDB Client Initialization
try:
    test_client = chromadb.EphemeralClient()
    test_collection = test_client.create_collection(name="test_collection")
    print(f"[OK] ChromaDB initialized successfully.")
except Exception as e:
    print(f"[FAIL] ChromaDB error: {e}")

print("\nTask 1 Environment Verification Complete!")