import pandas as pd
import json
import os

def prepare_rag_corpus(input_csv, output_json):
    print(f"Loading laptop dataset from {input_csv}...")
    
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"[ERROR] Could not find {input_csv}.")
        print("Please ensure your optimized_laptops.csv is inside the data/processed/ folder.")
        return

    corpus = []
    
    # Loop through every row in the dataset
    for idx, row in df.iterrows():
        laptop_id = f"LAP_{idx:04d}"
        
        # Use .get() to avoid errors if a column name is slightly different
        brand = str(row.get('Brand', 'Unknown'))
        processor = str(row.get('Processor', 'Standard CPU'))
        ram = float(row.get('RAM_GB', 8))
        price = float(row.get('Price_Clean', 0))
        
        # 1. Verbalize the row into a descriptive paragraph
        text_content = (
            f"A {brand} laptop powered by an {processor} processor with {ram}GB RAM. "
            f"It is suitable for general productivity, coding, and multitasking. "
            f"The official price is {price} INR."
        )
        
        # 2. Store exact numbers for strict SQL-style filtering later
        metadata = {
            "brand": brand,
            "price": price,
            "ram": ram
        }
        
        # 3. Package it together
        corpus.append({
            "id": laptop_id,
            "text": text_content,
            "metadata": metadata
        })
        
    # Save the structured corpus to a JSON file
    with open(output_json, 'w') as f:
        json.dump(corpus, f, indent=4)
        
    print(f"[OK] Successfully verbalized {len(corpus)} laptops.")
    print(f"[OK] Saved corpus to {output_json}")

if __name__ == "__main__":
    # Define paths relative to the root folder where you run the script
    input_path = 'data/processed/optimized_laptops.csv'
    output_path = 'data/processed/vector_laptops_corpus.json'
    
    prepare_rag_corpus(input_path, output_path)