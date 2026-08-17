"""
Multi-Category CSV Ingestion & Data Normalization Service (High-Performance Batching)
Supports Laptops, Phones / Smartphones, and Tablets.
Performs data cleaning, validation, deduplication, specification mapping, and high-speed batch MySQL upserts.
"""
from __future__ import annotations

import os
import re
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from models.product import Product, ProductSpec, ProductFeature, Brand, Category

logger = logging.getLogger("backend.csv_import")

# Fallback curated gadget images when dataset image is missing
CATEGORY_FALLBACK_IMAGES = {
    "Laptop": [
        "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544731612-de292439cc67?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80",
    ],
    "Phone": [
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1567581935884-3349723552ca?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600&auto=format&fit=crop&q=80",
    ],
    "Tablet": [
        "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?w=600&auto=format&fit=crop&q=80",
    ]
}


def clean_price(val: Any) -> float:
    """Normalize messy price strings like '₹ 28,990' or '28990.0' to float."""
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).replace("₹", "").replace(",", "").replace("INR", "").replace("Rs.", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", val_str)
    try:
        return float(match.group(1)) if match else 0.0
    except (ValueError, TypeError):
        return 0.0


def clean_ram(val: Any) -> float:
    """Normalize RAM strings ('8GB', '512MB', '4 GB RAM') to numeric GB."""
    if pd.isna(val) or val is None:
        return 4.0
    val_str = str(val).strip().upper()
    if "MB" in val_str:
        num = re.search(r"(\d+)", val_str)
        return round(float(num.group(1)) / 1024.0, 2) if num else 0.5
    match = re.search(r"(\d+(?:\.\d+)?)", val_str)
    try:
        return float(match.group(1)) if match else 4.0
    except (ValueError, TypeError):
        return 4.0


def clean_storage(val: Any) -> str:
    """Normalize storage string."""
    if pd.isna(val) or str(val).lower() in ["nan", "unknown", "none", ""]:
        return "64 GB"
    return str(val).strip()


def clean_rating(stars_5: Any, stars_1: Any, total_ratings: Any) -> Tuple[float, int]:
    """Calculate realistic star rating between 3.5 and 4.9 from star breakdown."""
    try:
        s5 = float(stars_5) if pd.notna(stars_5) else 50.0
        s1 = float(stars_1) if pd.notna(stars_1) else 5.0
        tot = int(float(str(total_ratings).replace(",", ""))) if pd.notna(total_ratings) and str(total_ratings).replace(",", "").replace(".", "").isdigit() else 25
        raw = 3.5 + (s5 / (s5 + s1 + 10.0)) * 1.4
        return float(np.clip(round(raw, 1), 3.5, 4.9)), max(tot, 1)
    except Exception:
        return 4.2, 25


def generate_product_code(category: str, brand: str, model: str, processor: str, ram: float, price: float) -> str:
    """Generate deterministic unique product code hash per category."""
    prefix = "LAP"
    cat_lower = category.lower()
    if "phone" in cat_lower or "mobile" in cat_lower:
        prefix = "MOB"
    elif "tablet" in cat_lower or "tab" in cat_lower:
        prefix = "TAB"

    seed_str = f"{prefix}_{str(brand).strip().lower()}_{str(model).strip().lower()}_{str(processor).strip().lower()}_{ram}_{int(price)}"
    digest = hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}-{digest}"


def compute_laptop_score(ram: float, price: float, rating: float, gpu: str, cpu: str) -> float:
    """Compute laptop AI benchmark score (0-100)."""
    score = 60.0
    if ram >= 32: score += 12.0
    elif ram >= 16: score += 8.0
    elif ram >= 8: score += 4.0

    gpu_l = str(gpu).lower()
    if any(k in gpu_l for k in ["4090", "4080", "4070", "3080"]): score += 18.0
    elif any(k in gpu_l for k in ["4060", "3070", "3060"]): score += 14.0
    elif any(k in gpu_l for k in ["3050", "2050", "1650", "1050"]): score += 10.0
    elif "geforce" in gpu_l or "radeon" in gpu_l or "rtx" in gpu_l or "gtx" in gpu_l: score += 6.0

    cpu_l = str(cpu).lower()
    if any(k in cpu_l for k in ["i9", "ryzen 9", "m3 max", "m3 pro"]): score += 10.0
    elif any(k in cpu_l for k in ["i7", "ryzen 7", "m2", "m3"]): score += 7.0
    elif any(k in cpu_l for k in ["i5", "ryzen 5", "m1"]): score += 4.0

    score += (min(max(rating, 1.0), 5.0) / 5.0) * 8.0
    return float(np.clip(round(score), 45.0, 99.0))


def compute_phone_score(ram: float, price: float, rating: float, camera: str, processor: str, has_5g: bool) -> float:
    """Compute smartphone AI benchmark score (0-100)."""
    score = 60.0
    if ram >= 12: score += 10.0
    elif ram >= 8: score += 8.0
    elif ram >= 6: score += 5.0
    elif ram >= 4: score += 2.0

    if has_5g: score += 6.0

    cam_m = re.search(r"(\d+)\s*(?:mp|megapixel)", str(camera).lower())
    if cam_m:
        mp = int(cam_m.group(1))
        if mp >= 108: score += 12.0
        elif mp >= 64: score += 9.0
        elif mp >= 48: score += 6.0
        elif mp >= 12: score += 3.0

    proc_l = str(processor).lower()
    if any(k in proc_l for k in ["bionic", "snapdragon 8", "dimensity 9000", "tensor"]): score += 10.0
    elif any(k in proc_l for k in ["snapdragon 7", "dimensity 8000", "exynos 2"]): score += 6.0

    score += (min(max(rating, 1.0), 5.0) / 5.0) * 8.0
    return float(np.clip(round(score), 45.0, 99.0))


def compute_tablet_score(ram: float, price: float, rating: float, screen_size: float, processor: str) -> float:
    """Compute tablet AI benchmark score (0-100)."""
    score = 62.0
    if ram >= 8: score += 12.0
    elif ram >= 6: score += 8.0
    elif ram >= 4: score += 4.0

    if screen_size >= 12.0: score += 10.0
    elif screen_size >= 10.5: score += 7.0
    elif screen_size >= 9.0: score += 4.0

    proc_l = str(processor).lower()
    if any(k in proc_l for k in ["m2", "m1", "bionic", "snapdragon 8"]): score += 10.0
    elif any(k in proc_l for k in ["snapdragon 7", "octa-core", "helio"]): score += 5.0

    score += (min(max(rating, 1.0), 5.0) / 5.0) * 8.0
    return float(np.clip(round(score), 45.0, 99.0))


class CSVImportService:
    @staticmethod
    def ensure_categories(db: Session) -> Dict[str, Category]:
        """Ensure standard categories exist in database and return lookup."""
        categories = {}
        for cat_name in ["Laptop", "Phone", "Tablet"]:
            c = db.query(Category).filter(Category.name.ilike(cat_name)).first()
            if not c:
                c = Category(name=cat_name, slug=cat_name.lower())
                db.add(c)
                db.flush()
            categories[cat_name] = c
        db.commit()
        return categories

    @classmethod
    def import_laptops(cls, db: Session, csv_path: str) -> Dict[str, Any]:
        """Ingest Laptop dataset."""
        logger.info(f"Ingesting Laptops from {csv_path}...")
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        categories = cls.ensure_categories(db)
        cat_obj = categories["Laptop"]

        existing_brands = {b.name.lower(): b for b in db.query(Brand).all()}
        existing_codes = set(p[0] for p in db.query(Product.product_code).filter(Product.category == "Laptop").all())

        new_count, dup_count, invalid_count = 0, 0, 0
        batch_size = 200
        new_products = []

        # Pre-ensure brands
        brand_col = next((c for c in df.columns if c.lower() == "brand"), None)
        raw_brands = set(str(b).strip() for b in df[brand_col].dropna().unique() if str(b).strip()) if brand_col else set()
        for b_name in raw_brands:
            b_key = b_name.lower()
            if b_key not in existing_brands:
                b_obj = Brand(name=b_name)
                db.add(b_obj)
                existing_brands[b_key] = b_obj
        db.commit()
        # Refresh brand objects with IDs
        existing_brands = {b.name.lower(): b for b in db.query(Brand).all()}

        for idx, row in df.iterrows():
            brand_name = str(row.get(brand_col or "brand", row.get("Brand", ""))).strip()
            if not brand_name or brand_name.lower() in ["nan", "unknown"]:
                invalid_count += 1
                continue

            brand_obj = existing_brands.get(brand_name.lower())
            product_name = str(row.get("name", "")).strip()
            model_name = str(row.get("model", "")).strip() or product_name
            price = clean_price(row.get("price", 0))
            if price <= 0:
                price = 45000.0

            ram_gb = clean_ram(row.get("ram_gb", row.get("ram", 8.0)))
            storage_str = clean_storage(row.get("storage", "512 GB SSD"))
            processor = str(row.get("processor", row.get("cpu", "Intel Core i5"))).strip()
            gpu = str(row.get("gpu", "Integrated Graphics")).strip()
            display_size = float(row.get("display_size", 15.6)) if pd.notna(row.get("display_size")) else 15.6
            resolution = str(row.get("resolution", "1920x1080")).strip()
            os_name = str(row.get("os", "Windows 11")).strip()
            battery = str(row.get("battery", "3-Cell Lithium-Ion")).strip()
            rating, total_ratings = clean_rating(row.get("5_star", 50), row.get("1_star", 5), row.get("rating_count", 50))

            product_code = generate_product_code("Laptop", brand_name, model_name, processor, ram_gb, price)
            if product_code in existing_codes:
                dup_count += 1
                continue

            score = compute_laptop_score(ram_gb, price, rating, gpu, processor)
            summary = f"{product_name} powered by {processor}, {int(ram_gb)}GB RAM, {storage_str} storage, and {gpu}."

            fb_imgs = CATEGORY_FALLBACK_IMAGES["Laptop"]
            image_url = fb_imgs[idx % len(fb_imgs)]

            prod = Product(
                product_code=product_code,
                name=product_name,
                brand_id=brand_obj.id if brand_obj else None,
                category_id=cat_obj.id,
                brand=brand_name,
                category="Laptop",
                model=model_name,
                price=price,
                original_price=round(price * 1.12, -2),
                rating=rating,
                total_ratings=total_ratings,
                reviews_count=total_ratings,
                image_url=image_url,
                specs_summary=summary,
                score=score,
                is_active=True
            )
            spec = ProductSpec(
                cpu=processor,
                ram_gb=ram_gb,
                storage=storage_str,
                gpu=gpu,
                display_size_inch=display_size,
                resolution=resolution,
                os=os_name,
                weight_kg=1.8,
                battery=battery,
                base_clock_speed_ghz=2.4,
                touch_screen=False,
                ports="USB 3.2, HDMI, Type-C",
            )
            prod.specs = spec
            prod.features = [
                ProductFeature(feature_type="pro", content=f"Processor: {processor}"),
                ProductFeature(feature_type="pro", content=f"Memory: {int(ram_gb)}GB RAM"),
                ProductFeature(feature_type="pro", content=f"Storage: {storage_str}"),
            ]
            new_products.append(prod)
            existing_codes.add(product_code)
            new_count += 1

            if len(new_products) >= batch_size:
                db.add_all(new_products)
                db.commit()
                new_products = []

        if new_products:
            db.add_all(new_products)
            db.commit()

        logger.info(f"Laptops imported: {new_count} new, {dup_count} duplicates.")
        return {
            "category": "Laptop",
            "total_rows": total_rows,
            "new_records": new_count,
            "duplicates": dup_count,
            "invalid_records": invalid_count
        }

    @classmethod
    def import_phones(cls, db: Session, csv_path: str) -> Dict[str, Any]:
        """Ingest Smartphone dataset with high-speed batching."""
        logger.info(f"Ingesting Phones from {csv_path}...")
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        categories = cls.ensure_categories(db)
        cat_obj = categories["Phone"]

        existing_brands = {b.name.lower(): b for b in db.query(Brand).all()}
        existing_codes = set(p[0] for p in db.query(Product.product_code).filter(Product.category == "Phone").all())

        # Pre-ensure brands
        raw_brands = set(str(b).strip() for b in df["Brand"].dropna().unique() if str(b).strip())
        for b_name in raw_brands:
            b_key = b_name.lower()
            if b_key not in existing_brands:
                b_obj = Brand(name=b_name)
                db.add(b_obj)
                existing_brands[b_key] = b_obj
        db.commit()
        existing_brands = {b.name.lower(): b for b in db.query(Brand).all()}

        new_count, dup_count, invalid_count = 0, 0, 0
        batch_size = 200
        new_products = []

        for idx, row in df.iterrows():
            brand_name = str(row.get("Brand", "")).strip()
            if not brand_name or brand_name.lower() in ["nan", "unknown"]:
                invalid_count += 1
                continue

            brand_obj = existing_brands.get(brand_name.lower())
            product_name = str(row.get("Product Name", "")).strip()
            model_name = str(row.get("Model", "")).strip() or product_name
            price = clean_price(row.get("Price in India", row.get("price_inr", 0)))
            if price <= 0:
                price = 15000.0

            ram_gb = clean_ram(row.get("RAM", row.get("ram_gb", 4.0)))
            storage_str = clean_storage(row.get("Internal storage", row.get("internal_storage_gb", "64GB")))
            processor = str(row.get("Processor make", row.get("Processor", "Octa-core"))).strip()
            if processor.lower() in ["nan", "unknown"]:
                processor = str(row.get("Processor", "Octa-core")).strip()

            battery_mah = str(row.get("Battery capacity (mAh)", row.get("battery_capacity_mah", "4000"))).strip()
            screen_size = float(row.get("Screen size (inches)", row.get("screen_size_inch", 6.1))) if pd.notna(row.get("Screen size (inches)")) or pd.notna(row.get("screen_size_inch")) else 6.1
            rear_camera = str(row.get("Rear camera", "12MP + 5MP")).strip()
            front_camera = str(row.get("Front camera", "8MP")).strip()
            resolution = str(row.get("Resolution", "1080x2400 pixels")).strip()
            os_name = str(row.get("Operating system", "Android")).strip()

            has_5g = "5G" in str(row.get("Sim 1 4G/ LTE", "")) or "5g" in product_name.lower() or "5G" in str(row.get("Sim 1 5G", ""))
            rating, total_ratings = clean_rating(row.get("5 Stars", 50), row.get("1 Stars", 5), row.get("Total Ratings", 100))

            product_code = generate_product_code("Phone", brand_name, model_name, processor, ram_gb, price)
            if product_code in existing_codes:
                dup_count += 1
                continue

            score = compute_phone_score(ram_gb, price, rating, rear_camera, processor, has_5g)
            summary = f"{product_name} featuring {processor}, {int(ram_gb)}GB RAM, {storage_str} storage, and {battery_mah}mAh battery."

            badge = None
            if score >= 94: badge = "Flagship"
            elif price < 20000 and score >= 85: badge = "Best Value"
            elif has_5g and score >= 88: badge = "Top 5G"
            elif rating >= 4.6: badge = "Popular"

            raw_img = str(row.get("Picture URL", "")).strip()
            if raw_img and raw_img.startswith("http") and "nan" not in raw_img:
                image_url = raw_img
            else:
                fb_imgs = CATEGORY_FALLBACK_IMAGES["Phone"]
                image_url = fb_imgs[idx % len(fb_imgs)]

            prod = Product(
                product_code=product_code,
                name=product_name,
                brand_id=brand_obj.id if brand_obj else None,
                category_id=cat_obj.id,
                brand=brand_name,
                category="Phone",
                model=model_name,
                price=price,
                original_price=round(price * 1.15, -2),
                rating=rating,
                total_ratings=total_ratings,
                reviews_count=total_ratings,
                image_url=image_url,
                badge=badge,
                specs_summary=summary,
                score=score,
                is_active=True
            )
            spec = ProductSpec(
                cpu=processor,
                ram_gb=ram_gb,
                storage=storage_str,
                gpu="Integrated Adreno / Mali Graphics",
                display_size_inch=screen_size,
                resolution=resolution,
                os=os_name,
                weight_kg=0.18,
                battery=f"{battery_mah} mAh",
                base_clock_speed_ghz=2.2,
                touch_screen=True,
                ports="USB Type-C",
                raw_specs_json={
                    "rear_camera": rear_camera,
                    "front_camera": front_camera,
                    "5g_supported": has_5g,
                    "battery_mah": battery_mah,
                    "fast_charging": str(row.get("Fast charging", "Yes")),
                }
            )
            prod.specs = spec
            prod.features = [
                ProductFeature(feature_type="pro", content=f"Rear Camera: {rear_camera}"),
                ProductFeature(feature_type="pro", content=f"Battery: {battery_mah}mAh with all-day endurance"),
            ]
            if has_5g:
                prod.features.append(ProductFeature(feature_type="pro", content="High-speed 5G network support"))

            new_products.append(prod)
            existing_codes.add(product_code)
            new_count += 1

            if len(new_products) >= batch_size:
                db.add_all(new_products)
                db.commit()
                new_products = []

        if new_products:
            db.add_all(new_products)
            db.commit()

        logger.info(f"Phones imported: {new_count} new, {dup_count} duplicates.")
        return {
            "category": "Phone",
            "total_rows": total_rows,
            "new_records": new_count,
            "duplicates": dup_count,
            "invalid_records": invalid_count
        }

    @classmethod
    def import_tablets(cls, db: Session, csv_path: str) -> Dict[str, Any]:
        """Ingest Tablet dataset with high-speed batching."""
        logger.info(f"Ingesting Tablets from {csv_path}...")
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        categories = cls.ensure_categories(db)
        cat_obj = categories["Tablet"]

        existing_brands = {b.name.lower(): b for b in db.query(Brand).all()}
        existing_codes = set(p[0] for p in db.query(Product.product_code).filter(Product.category == "Tablet").all())

        # Pre-ensure brands
        raw_brands = set(str(b).strip() for b in df["Brand"].dropna().unique() if str(b).strip())
        for b_name in raw_brands:
            b_key = b_name.lower()
            if b_key not in existing_brands:
                b_obj = Brand(name=b_name)
                db.add(b_obj)
                existing_brands[b_key] = b_obj
        db.commit()
        existing_brands = {b.name.lower(): b for b in db.query(Brand).all()}

        new_count, dup_count, invalid_count = 0, 0, 0
        batch_size = 200
        new_products = []

        for idx, row in df.iterrows():
            brand_name = str(row.get("Brand", "")).strip()
            if not brand_name or brand_name.lower() in ["nan", "unknown"]:
                invalid_count += 1
                continue

            brand_obj = existing_brands.get(brand_name.lower())
            product_name = str(row.get("Product Name", "")).strip()
            model_name = str(row.get("Model", "")).strip() or product_name
            price = clean_price(row.get("Price in India", 0))
            if price <= 0:
                price = 18000.0

            ram_gb = clean_ram(row.get("RAM", 2.0))
            storage_str = clean_storage(row.get("Internal storage", "32GB"))
            processor = str(row.get("Processor make", row.get("Processor", "Quad-core"))).strip()
            if processor.lower() in ["nan", "unknown"]:
                processor = str(row.get("Processor", "Quad-core")).strip()

            battery_mah = str(row.get("Battery capacity (mAh)", "5000")).strip()
            screen_size = float(row.get("Screen size (inches)", 8.0)) if pd.notna(row.get("Screen size (inches)")) else 8.0
            rear_camera = str(row.get("Rear camera", "8MP")).strip()
            front_camera = str(row.get("Front camera", "5MP")).strip()
            resolution = str(row.get("Resolution", "1280x800 pixels")).strip()
            os_name = str(row.get("Operating system", "Android / iPadOS")).strip()

            has_cellular = "Yes" in str(row.get("3G", "")) or "Yes" in str(row.get("4G/ LTE", "")) or "4g" in product_name.lower() or "lte" in product_name.lower()
            has_stylus = "pen" in product_name.lower() or "stylus" in product_name.lower() or "apple" in brand_name.lower() or "samsung" in brand_name.lower()
            rating, total_ratings = clean_rating(row.get("5 Stars", 40), row.get("1 Stars", 8), row.get("Total Ratings", 50))

            product_code = generate_product_code("Tablet", brand_name, model_name, processor, ram_gb, price)
            if product_code in existing_codes:
                dup_count += 1
                continue

            score = compute_tablet_score(ram_gb, price, rating, screen_size, processor)
            summary = f"{product_name} featuring a {screen_size}\" display, {processor}, {int(ram_gb)}GB RAM, and {battery_mah}mAh battery."

            badge = None
            if score >= 92: badge = "Flagship Slate"
            elif price < 15000 and score >= 80: badge = "Student Choice"
            elif screen_size >= 10.5: badge = "Large Screen"
            elif rating >= 4.5: badge = "Top Rated"

            raw_img = str(row.get("Picture URL", "")).strip()
            if raw_img and raw_img.startswith("http") and "nan" not in raw_img:
                image_url = raw_img
            else:
                fb_imgs = CATEGORY_FALLBACK_IMAGES["Tablet"]
                image_url = fb_imgs[idx % len(fb_imgs)]

            prod = Product(
                product_code=product_code,
                name=product_name,
                brand_id=brand_obj.id if brand_obj else None,
                category_id=cat_obj.id,
                brand=brand_name,
                category="Tablet",
                model=model_name,
                price=price,
                original_price=round(price * 1.15, -2),
                rating=rating,
                total_ratings=total_ratings,
                reviews_count=total_ratings,
                image_url=image_url,
                badge=badge,
                specs_summary=summary,
                score=score,
                is_active=True
            )
            spec = ProductSpec(
                cpu=processor,
                ram_gb=ram_gb,
                storage=storage_str,
                gpu="Integrated Graphics",
                display_size_inch=screen_size,
                resolution=resolution,
                os=os_name,
                weight_kg=0.45,
                battery=f"{battery_mah} mAh",
                base_clock_speed_ghz=2.0,
                touch_screen=True,
                ports="USB Type-C / Lightning",
                raw_specs_json={
                    "rear_camera": rear_camera,
                    "front_camera": front_camera,
                    "stylus_supported": has_stylus,
                    "cellular_supported": has_cellular,
                    "battery_mah": battery_mah,
                }
            )
            prod.specs = spec
            prod.features = [
                ProductFeature(feature_type="pro", content=f"Vibrant {screen_size}-inch touchscreen display"),
                ProductFeature(feature_type="pro", content=f"{battery_mah}mAh battery for extended media & reading"),
            ]

            new_products.append(prod)
            existing_codes.add(product_code)
            new_count += 1

            if len(new_products) >= batch_size:
                db.add_all(new_products)
                db.commit()
                new_products = []

        if new_products:
            db.add_all(new_products)
            db.commit()

        logger.info(f"Tablets imported: {new_count} new, {dup_count} duplicates.")
        return {
            "category": "Tablet",
            "total_rows": total_rows,
            "new_records": new_count,
            "duplicates": dup_count,
            "invalid_records": invalid_count
        }

    @classmethod
    def import_all_datasets(cls, db: Session, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        """Ingest all available product datasets (Laptops, Phones, Tablets) into AWS RDS MySQL."""
        if workspace_root is None:
            workspace_root = "/Users/asf28146gmail.com/Desktop/cognizant-product-assistant-development copy 2"

        ws = Path(workspace_root)
        laptop_csv = ws / "data" / "optimized_laptops.csv"
        phone_csv = ws / "new rag" / "ver2" / "data" / "raw" / "mobiles.csv"
        tablet_csv = ws / "new rag" / "ver2" / "data" / "raw" / "tablets.csv"

        report = {
            "total_categories": 3,
            "results": {}
        }

        if laptop_csv.exists():
            report["results"]["Laptop"] = cls.import_laptops(db, str(laptop_csv))
        if phone_csv.exists():
            report["results"]["Phone"] = cls.import_phones(db, str(phone_csv))
        if tablet_csv.exists():
            report["results"]["Tablet"] = cls.import_tablets(db, str(tablet_csv))

        return report
