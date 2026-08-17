import os
from google import genai
from retrieval_engine import retrieve_laptops

# 1. Initialize the GenAI client (it automatically finds your GEMINI_API_KEY)
client = genai.Client()

def generate_comparison(user_query, max_price=None, top_k=3):
    print(f"\n[RAG] Processing User Query: '{user_query}'")
    
    # 2. Retrieve exact factual context from local ChromaDB
    retrieved_docs = retrieve_laptops(user_query, max_price=max_price, top_k=top_k)
    
    if not retrieved_docs:
        return "I'm sorry, but I couldn't find any laptops in our database matching those exact criteria."
        
    # 3. Format the retrieved list into a single text block
    context_str = "\n".join([f"- {doc}" for doc in retrieved_docs])
    
    # 4. Assemble the prompt instruction (The core of RAG)
    prompt = f"""
    You are an expert laptop advisor. Answer the user request strictly using ONLY the provided database context below.
    Do not invent any specs, prices, or details outside of this context. If the user asks for something not in the context, politely state you don't have that information.
    
    DATABASE CONTEXT:
    {context_str}
    
    USER QUERY:
    {user_query}
    
    INSTRUCTIONS:
    - Create a Markdown comparison table showing Brand, Processor, RAM, and Price.
    - Provide a brief, conversational summary of which laptop offers better value for money based on the provided specs.
    - Keep the tone helpful and professional.
    """
    
    print("[RAG] Sending context to Gemini...")
    
    # 5. Call the Gemini 2.5 Flash API to synthesize the final answer
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=prompt
    )
    
    return response.text

if __name__ == "__main__":
    print("--- TESTING THE FULL RAG PIPELINE ---")
    
    # Simulate a user searching for a heavy-duty laptop on a budget
    test_query = "What is a good Asus or HP laptop for heavy video editing?"
    final_output = generate_comparison(test_query, max_price=75000, top_k=2)
    
    print("\n=== FINAL AI RESPONSE ===\n")
    print(final_output)