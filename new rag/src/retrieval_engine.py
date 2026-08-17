import chromadb
from chromadb.utils import embedding_functions

def retrieve_laptops(user_query, max_price=None, top_k=3):
    print(f"\n[SEARCH] Semantic Query: '{user_query}'")
    
    # 1. Initialize the embedding function (translates the new query into vectors)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # 2. Connect to your existing local database folder
    client = chromadb.PersistentClient(path="./chroma_laptop_db")
    
    # Access the collection we created in Task 3
    collection = client.get_collection(
        name="laptops_collection",
        embedding_function=sentence_transformer_ef
    )
    
    # 3. Construct the exact metadata filter (Hybrid Search feature)
    where_clause = None
    if max_price:
        print(f"[SEARCH] Applying exact filter: Price <= {max_price} INR")
        # ChromaDB uses MongoDB-like syntax for metadata filters ($lte = Less Than or Equal)
        where_clause = {"price": {"$lte": float(max_price)}}
        
    # 4. Perform the vector similarity search
    results = collection.query(
        query_texts=[user_query],
        n_results=top_k,
        where=where_clause
    )
    
    # 5. Display the retrieved results
    print("\n[RESULTS] Top Matches:")
    if not results['documents'][0]:
        print("No laptops found matching those criteria.")
        return []
        
    for idx, doc in enumerate(results['documents'][0]):
        metadata = results['metadatas'][0][idx]
        print(f"{idx+1}. {doc}")
        print(f"   (Hidden Metadata - Brand: {metadata['brand']}, Price: {metadata['price']})")
        
    return results['documents'][0]

if __name__ == "__main__":
    print("--- RUNNING RETRIEVAL TESTS ---")
    
    # Test 1: Pure semantic search (Intent-based)
    retrieve_laptops(
        user_query="I need a heavy duty machine for 3D modeling and rendering", 
        top_k=2
    )
    
    # Test 2: Hybrid search (Semantic Intent + Strict Price Filter)
    retrieve_laptops(
        user_query="Good lightweight laptop for college coding", 
        max_price=50000, 
        top_k=2
    )