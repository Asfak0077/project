"""
Comparison API Route
Generates side-by-side spec comparison matrix and automated winner calculation
adapted for Laptops, Phones, and Tablets with MySQL persistence for logged-in users.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.product import Product
from models.history import ComparisonHistory
from models.user import User
from schemas.compare import CompareRequest, CompareResponse, SpecComparisonRow
from routes.products import format_product_response
from utils.security import get_optional_user, get_current_user
from services.product_data_validator import normalize_product_name
from services.user_storage_service import UserStorageService

router = APIRouter(prefix="/compare", tags=["Compare"])


class SaveComparisonRequest(BaseModel):
    comparison_id: str
    product_ids: List[Any]
    comparison_result: Optional[Dict[str, Any]] = None


@router.post("", response_model=CompareResponse)
def compare_products(
    data: CompareRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Retrieve side-by-side spec comparison matrix and winner calculations."""
    if not data.product_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one product ID must be provided for comparison."
        )

    # Fetch products
    products: List[Product] = []
    for pid in data.product_ids:
        if str(pid).isdigit():
            p = db.query(Product).filter(Product.id == int(pid)).first()
        else:
            p = db.query(Product).filter(Product.product_code == str(pid)).first()
        if p and p not in products:
            products.append(p)

    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="None of the specified products were found."
        )

    formatted_prods = [format_product_response(p) for p in products]

    # Detect category mix
    categories = [p.category for p in formatted_prods]
    has_phones = any("phone" in c.lower() for c in categories)
    has_tablets = any("tablet" in c.lower() for c in categories)

    # Build comparison rows
    spec_rows: List[SpecComparisonRow] = []

    # 1. Category row
    cat_vals = {p.id: p.category for p in formatted_prods}
    spec_rows.append(SpecComparisonRow(
        label="Category",
        key="category",
        values=cat_vals,
        winner_product_id=None,
        is_different=len(set(cat_vals.values())) > 1
    ))

    # 2. Price row
    price_vals = {p.id: p.price for p in formatted_prods}
    min_price = min(price_vals.values()) if price_vals else None
    price_winner = next((p.id for p in formatted_prods if p.price == min_price), None)
    spec_rows.append(SpecComparisonRow(
        label="Price (INR)",
        key="price",
        values={p.id: f"₹{int(p.price):,}" for p in formatted_prods},
        winner_product_id=price_winner,
        is_different=len(set(price_vals.values())) > 1
    ))

    # 3. CPU row
    cpu_vals = {p.id: p.cpu for p in formatted_prods}
    spec_rows.append(SpecComparisonRow(
        label="Processor",
        key="cpu",
        values=cpu_vals,
        winner_product_id=None,
        is_different=len(set(cpu_vals.values())) > 1
    ))

    # 4. RAM row
    ram_vals = {p.id: p.ram for p in formatted_prods}
    max_ram = max(ram_vals.values()) if ram_vals else None
    ram_winner = next((p.id for p in formatted_prods if p.ram == max_ram), None)
    spec_rows.append(SpecComparisonRow(
        label="RAM Memory",
        key="ram",
        values={p.id: f"{int(p.ram) if p.ram.is_integer() else p.ram} GB" for p in formatted_prods},
        winner_product_id=ram_winner,
        is_different=len(set(ram_vals.values())) > 1
    ))

    # 5. Storage row
    storage_vals = {p.id: p.storage for p in formatted_prods}
    spec_rows.append(SpecComparisonRow(
        label="Storage",
        key="storage",
        values=storage_vals,
        winner_product_id=None,
        is_different=len(set(storage_vals.values())) > 1
    ))

    # 6. GPU row (Laptops)
    if not (has_phones or has_tablets):
        gpu_vals = {p.id: p.gpu or "Integrated" for p in formatted_prods}
        spec_rows.append(SpecComparisonRow(
            label="Graphics (GPU)",
            key="gpu",
            values=gpu_vals,
            winner_product_id=None,
            is_different=len(set(gpu_vals.values())) > 1
        ))

    # 7. Display row
    display_vals = {}
    for p in formatted_prods:
        disp = getattr(p, "display", None)
        if not disp and getattr(p, "specs", None):
            spec_disp = getattr(p.specs, "display_size_inch", None)
            spec_res = getattr(p.specs, "resolution", None)
            if spec_disp and spec_res:
                disp = f'{spec_disp}" {spec_res}'
            elif spec_disp:
                disp = f'{spec_disp}"'
            elif spec_res:
                disp = spec_res
        display_vals[p.id] = disp or "Standard Display"

    spec_rows.append(SpecComparisonRow(
        label="Display Screen",
        key="display",
        values=display_vals,
        winner_product_id=None,
        is_different=len(set(display_vals.values())) > 1
    ))

    # 8. Battery row
    battery_vals = {}
    for p in formatted_prods:
        bat = getattr(p, "battery", None)
        if not bat and getattr(p, "specs", None):
            bat = getattr(p.specs, "battery", None)
        battery_vals[p.id] = bat or "Standard Battery"

    spec_rows.append(SpecComparisonRow(
        label="Battery Configuration",
        key="battery",
        values=battery_vals,
        winner_product_id=None,
        is_different=len(set(battery_vals.values())) > 1
    ))

    # 9. Camera row (if Phone or Tablet)
    if has_phones or has_tablets:
        cam_vals = {}
        for p in formatted_prods:
            cam = getattr(p, "rear_camera", None) or getattr(p, "camera", None)
            if not cam and getattr(p, "specs", None) and getattr(p.specs, "raw_specs", None):
                cam = p.specs.raw_specs.get("camera") or p.specs.raw_specs.get("rear_camera")
            cam_vals[p.id] = cam or "Standard Camera"

        spec_rows.append(SpecComparisonRow(
            label="Camera System",
            key="camera",
            values=cam_vals,
            winner_product_id=None,
            is_different=len(set(cam_vals.values())) > 1
        ))

    # 10. AI Score Benchmark
    score_vals = {p.id: p.score for p in formatted_prods}
    max_score = max(score_vals.values()) if score_vals else None
    score_winner = next((p.id for p in formatted_prods if p.score == max_score), None)
    spec_rows.append(SpecComparisonRow(
        label="AI Benchmark Score",
        key="score",
        values={p.id: f"{p.score:.0f} / 100" for p in formatted_prods},
        winner_product_id=score_winner,
        is_different=len(set(score_vals.values())) > 1
    ))

    # Calculate overall winner
    overall_winner = max(formatted_prods, key=lambda p: p.score)
    clean_winner_name = normalize_product_name(overall_winner.brand, overall_winner.name)

    if "phone" in overall_winner.category.lower():
        summary_text = (
            f"{clean_winner_name} ranks highest overall (Score: {overall_winner.score:.0f}/100) "
            f"with balanced camera performance and {int(overall_winner.ram)}GB RAM."
        )
    elif "tablet" in overall_winner.category.lower():
        summary_text = (
            f"{clean_winner_name} delivers the best composite rating "
            f"(Score: {overall_winner.score:.0f}/100) with high-efficiency display and {int(overall_winner.ram)}GB RAM."
        )
    else:
        gpu_str = str(overall_winner.gpu or "").strip()
        if not gpu_str or gpu_str.lower() in ["none", "unknown", "nan", "0", "0.0"] or "integrated" in gpu_str.lower():
            gpu_phrase = "integrated graphics"
        else:
            gpu_phrase = f"{gpu_str} dedicated graphics"
        summary_text = (
            f"{clean_winner_name} achieves the top overall performance rating "
            f"(Score: {overall_winner.score:.0f}/100) with {gpu_phrase} and {int(overall_winner.ram)}GB RAM."
        )

    # Persist to product_comparisons and comparison_history for logged-in user
    if current_user:
        try:
            cid = f"comp_{'_'.join([str(p.id) for p in formatted_prods])}"
            res_dict = {
                "products": [p.dict() if hasattr(p, "dict") else p for p in formatted_prods],
                "winner_id": overall_winner.id,
                "winner_name": clean_winner_name,
                "winner_summary": summary_text,
                "spec_rows": [r.dict() if hasattr(r, "dict") else r for r in spec_rows],
            }
            UserStorageService.save_product_comparison(
                db=db,
                user_id=current_user.id,
                comparison_id=cid,
                product_ids=[p.id for p in formatted_prods],
                comparison_result=res_dict
            )
        except Exception as e:
            db.rollback()

    return CompareResponse(
        products=formatted_prods,
        spec_rows=spec_rows,
        overall_winner_id=overall_winner.id,
        winner_summary=summary_text
    )


# =========================================================================
# SAVED COMPARISONS ENDPOINTS (STRICT USER ISOLATION)
# =========================================================================

@router.get("/saved")
def get_saved_comparisons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all saved product comparisons for the logged-in user."""
    return UserStorageService.get_user_comparisons(db=db, user_id=current_user.id)


@router.post("/save")
def save_comparison(
    req: SaveComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explicitly save or update a comparison matrix for the logged-in user."""
    saved = UserStorageService.save_product_comparison(
        db=db,
        user_id=current_user.id,
        comparison_id=req.comparison_id,
        product_ids=req.product_ids,
        comparison_result=req.comparison_result
    )
    return {"status": "saved", "id": saved.id, "comparison_id": saved.comparison_id}


@router.delete("/saved/{comparison_id}")
def delete_saved_comparison(
    comparison_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a saved comparison for the logged-in user."""
    UserStorageService.delete_product_comparison(
        db=db,
        user_id=current_user.id,
        comparison_id=comparison_id
    )
    return {"status": "deleted", "comparison_id": comparison_id}
