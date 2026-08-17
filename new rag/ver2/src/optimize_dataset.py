import pandas as pd
import numpy as np
import re

def clean_dataset(input_path, output_path):
    print("Loading raw database...")
    df = pd.read_csv(input_path)
    initial_count = len(df)
    
    # ---------------------------------------------------------
    # 1. Drop Unusable Laptops
    # ---------------------------------------------------------
    # A laptop without a price, RAM, or storage is useless for our RAG.
    df = df.dropna(subset=['price_inr', 'ram_gb', 'storage_gb', 'product_name'])
    
    # ---------------------------------------------------------
    # 2. Extract Trusted Facts from the Product Title
    # ---------------------------------------------------------
    def extract_ram(title):
        match = re.search(r'\b(\d+)\s*(?:gb|g)?\s*ram\b', title, re.IGNORECASE)
        return float(match.group(1)) if match else np.nan

    def extract_storage(title):
        match = re.search(r'\b(\d+)\s*(TB|GB)\s*(HDD|SSD|EMMC|NVME)?\b', title, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            unit = match.group(2).upper()
            if unit == 'TB': val *= 1024
            return val
        return np.nan

    df['title_ram'] = df['product_name'].apply(extract_ram)
    df['title_storage'] = df['product_name'].apply(extract_storage)
    
    # ---------------------------------------------------------
    # 3. Resolve Mismatches (The Title Always Wins)
    # ---------------------------------------------------------
    # If the title explicitly says "4GB RAM", but the column says 16.0, overwrite it.
    ram_mismatches = df['title_ram'].notnull() & (df['title_ram'] != df['ram_gb'])
    df.loc[ram_mismatches, 'ram_gb'] = df.loc[ram_mismatches, 'title_ram']
    
    storage_mismatches = df['title_storage'].notnull() & (df['title_storage'] != df['storage_gb'])
    df.loc[storage_mismatches, 'storage_gb'] = df.loc[storage_mismatches, 'title_storage']
    
    # ---------------------------------------------------------
    # 4. Hardware Sanity Checks (Anomaly Detection)
    # ---------------------------------------------------------
    # If a laptop is less than 25,000 INR, it cannot have a dedicated GPU.
    budget_gpu_mask = (df['price_inr'] < 25000) & (df['dedicated_graphics'] == True)
    df.loc[budget_gpu_mask, 'dedicated_graphics'] = False
    
    # Clean up the temporary tracking columns
    df = df.drop(columns=['title_ram', 'title_storage'])
    
    # ---------------------------------------------------------
    # 5. Regenerate the `text` Document for the LLM
    # ---------------------------------------------------------
    # Because we changed the underlying facts, we MUST rewrite the paragraph
    # that the AI will read to prevent it from hallucinating the old data.
    def generate_text(row):
        parts = []
        if pd.notnull(row.get('brand')): parts.append(f"Brand: {row['brand']}")
        if pd.notnull(row.get('model')): parts.append(f"Model: {row['model']}")
        parts.append(f"Product: {row['product_name']}")
        if pd.notnull(row.get('processor')): parts.append(f"Processor: {row['processor']}")
        if pd.notnull(row.get('ram_gb')): parts.append(f"RAM: {row['ram_gb']} GB")
        if pd.notnull(row.get('storage_gb')): parts.append(f"Storage capacity: {row['storage_gb']} GB")
        if pd.notnull(row.get('storage_type')): parts.append(f"Storage type: {row['storage_type']}")
        if pd.notnull(row.get('graphics_processor')): parts.append(f"Graphics processor: {row['graphics_processor']}")
        if pd.notnull(row.get('dedicated_graphics')):
            dg = "Yes" if row['dedicated_graphics'] else "No"
            parts.append(f"Dedicated graphics: {dg}")
        if pd.notnull(row.get('screen_size_inch')): parts.append(f"Screen size: {row['screen_size_inch']} inches")
        if pd.notnull(row.get('weight_kg')): parts.append(f"Weight: {row['weight_kg']} kg")
        if pd.notnull(row.get('price_inr')): parts.append(f"Price: ₹{row['price_inr']}")
        if pd.notnull(row.get('rating_score')): parts.append(f"Rating: {row['rating_score']} out of 5")
        return ". ".join(parts) + "."
        
    df['text'] = df.apply(generate_text, axis=1)
    
    final_count = len(df)
    print(f"Cleaning complete. Dropped {initial_count - final_count} invalid rows.")
    print(f"Successfully optimized {final_count} laptops.")
    
    df.to_csv(output_path, index=False)
    print(f"Saved optimized dataset to {output_path}")

if __name__ == "__main__":
    clean_dataset("data/processed/cleaned_laptops.csv", "data/processed/cleaned_laptops_optimized.csv")