import json
import chromadb
from chromadb.utils import embedding_functions

def index_laptops_to_chroma(json_path, persist_dir):
    print("Initializing ChromaDB and Embedding Model...")
    print("(If this is the first run, downloading the model takes a few seconds)")
    
    # 1. Initialize the local embedding model (runs on CPU without costs)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # 2. Initialize ChromaDB persistent client to save data locally
    client = chromadb.PersistentClient(path=persist_dir)
    
    # 3. Create or access the collection (similar to a SQL table)
    collection = client.get_or_create_collection(
        name="laptops_collection",
        embedding_function=sentence_transformer_ef
    )
    
    print(f"Loading data from {json_path}...")
    try:
        with open(json_path, 'r') as f:
            corpus = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Could not find {json_path}.")
        return
        
    documents = []
    metadatas = []
    ids = []
    
    # Parse JSON data into individual lists for ChromaDB
    for item in corpus:
        ids.append(item['id'])
        documents.append(item['text'])
        metadatas.append(item['metadata'])
        
    print(f"Generating vectors and indexing {len(documents)} laptops...")
    
    # 4. Add data to the collection
    # ChromaDB automatically converts the 'documents' list into vector embeddings here
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"[OK] Successfully indexed {collection.count()} items into the collection.")
    print(f"[OK] Database saved securely in the '{persist_dir}' folder.")

if __name__ == "__main__":
    # Define relative paths from the root folder
    input_json = 'data/processed/vector_laptops_corpus.json'
    chroma_db_dir = './chroma_laptop_db'
    
    index_laptops_to_chroma(input_json, chroma_db_dir)