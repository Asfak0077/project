import os
from google import genai

client = genai.Client()

print("--- FETCHING AVAILABLE MODELS FROM GOOGLE ---")
try:
    # Retrieve all models available to your API key
    available_models = client.models.list()
    
    print("\nYou can use these exact model names in your rag_chain.py:\n")
    for model in available_models:
        # Filter for models that support text generation
        if 'generateContent' in model.supported_actions:
            # Remove the 'models/' prefix to get the clean name
            clean_name = model.name.replace('models/', '')
            print(f"- '{clean_name}'")
            
except Exception as e:
    print(f"[FAIL] Error communicating with Gemini: {e}")