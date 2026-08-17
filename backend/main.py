import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils.config import settings
from database import init_db, SessionLocal
from models.product import Product
from services.csv_import_service import CSVImportService
from services.rag_service import RAGService
from routes import (
    auth_router,
    users_router,
    products_router,
    compare_router,
    recommendations_router,
    chat_router,
    favorites_router,
    history_router,
    documents_router,
    feedback_router,
    admin_router,
    dashboard_router,
    session_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database Tables & Ingest CSV Dataset if empty
    logger.info("Initializing database tables...")
    init_db()

    # Pre-warm RAG VER2 pipeline
    try:
        rag_health = RAGService.check_health()
        logger.info(f"RAG VER2 Startup Health: {rag_health.get('status')} (version={rag_health.get('rag_version')})")
    except Exception as e:
        logger.warning(f"RAG VER2 pre-warm warning: {e}")

    db = SessionLocal()
    try:
        laptop_count = db.query(Product).filter(Product.category == "Laptop").count()
        phone_count = db.query(Product).filter(Product.category == "Phone").count()
        tablet_count = db.query(Product).filter(Product.category == "Tablet").count()
        logger.info(f"Current database product counts: Laptops={laptop_count}, Phones={phone_count}, Tablets={tablet_count}")

        if laptop_count == 0 or phone_count == 0 or tablet_count == 0:
            logger.info("One or more category datasets missing in MySQL. Running multi-category CSV ingestion...")
            result = CSVImportService.import_all_datasets(db)
            logger.info(f"Multi-category CSV ingestion completed: {result}")
    except Exception as e:
        logger.error(f"Error during startup data initialization: {e}")
    finally:
        db.close()

    yield
    logger.info("Application shutting down...")

# Instantiate FastAPI Application
app = FastAPI(
    title="VersusAI Product Intelligence API",
    description="Backend REST API integrating React Frontend, MySQL Database, CSV Ingestion, NLP Requirement Extraction, Recommendation Engine, and RAG Document Intelligence.",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError

# Global Validation Exception Handler (Clean user-friendly error formatting)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request validation error on {request.method} {request.url.path}: {exc}")
    req_origin = request.headers.get("origin", "http://localhost:3000")
    
    if "chat" in request.url.path:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "error_code": "INVALID_PRODUCT_REQUEST",
                "message": "I couldn't complete the product analysis. Please try again.",
                "answer": "I couldn't complete the product analysis. Please try again.",
                "intent": "UNKNOWN",
                "type": "error",
                "confidence": "Low",
                "context_used": "general",
                "products": [],
                "recommendations": [],
                "sources": [],
                "suggested_followups": [
                    "Tell me about ASUS ROG",
                    "Explain product 1",
                    "Compare ASUS and MSI"
                ]
            },
            headers={
                "Access-Control-Allow-Origin": req_origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "INVALID_REQUEST_PARAMETERS",
            "message": "Product selection is invalid or parameters are missing."
        },
        headers={
            "Access-Control-Allow-Origin": req_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*"
        }
    )

# Global Exception Handler for friendly error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    req_origin = request.headers.get("origin", "http://localhost:3000")
    if "chat" in request.url.path:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "error_code": "INTERNAL_CHAT_ERROR",
                "message": "I couldn't complete the product analysis. Please try again.",
                "answer": "I couldn't complete the product analysis. Please try again.",
                "intent": "UNKNOWN",
                "type": "error",
                "confidence": "Low",
                "context_used": "general",
                "products": [],
                "recommendations": [],
                "sources": [],
                "suggested_followups": [
                    "Tell me about ASUS ROG",
                    "Explain product 1",
                    "Compare ASUS and MSI"
                ]
            },
            headers={
                "Access-Control-Allow-Origin": req_origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*"
            }
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Unable to complete request. Please try again."},
        headers={
            "Access-Control-Allow-Origin": req_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*"
        }
    )

from fastapi.staticfiles import StaticFiles

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_STORAGE_PATH, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_STORAGE_PATH, "avatars"), exist_ok=True)

# Mount Static Files for uploads / avatars
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_STORAGE_PATH), name="uploads")

# Register API Routers under /api
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(compare_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(favorites_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(session_router, prefix="/api")

@app.get("/")
def root():
    return {
        "service": "VersusAI Product Intelligence API",
        "status": "online",
        "version": "2.0.0",
        "docs_url": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected"
    }

@app.get("/api/rag/health")
def rag_health_check():
    """RAG VER2 Health Check Endpoint."""
    return RAGService.check_health()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
