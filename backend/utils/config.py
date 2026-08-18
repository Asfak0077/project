import os
import json
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # AWS RDS MySQL & Database Connection Settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "admin")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "my_project")
    
    # Base DATABASE_URL (constructed dynamically or overridden by env)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"mysql+pymysql://{os.getenv('DB_USER', 'admin')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'my_project')}?charset=utf8mb4"
    )
    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "versus_ai_super_secret_jwt_key_2026_change_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", os.getenv("VITE_GOOGLE_CLIENT_ID", ""))
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]
    CSV_DATASET_PATH: str = os.path.join(os.path.dirname(__file__), "../../data/optimized_laptops.csv")
    DOCUMENTS_STORAGE_PATH: str = os.path.join(os.path.dirname(__file__), "../../documents")
    UPLOAD_STORAGE_PATH: str = os.path.join(os.path.dirname(__file__), "../uploads")
    
    # RAG VER2 Configuration Settings
    RAG_VERSION: str = "ver2"
    RAG_VER2_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../services/rag"))
    RAG_VECTOR_DB_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../services/rag/vector_db"))
    RAG_EMBEDDING_MODEL: str = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))

    @field_validator("CSV_DATASET_PATH", mode="before")
    @classmethod
    def resolve_csv_dataset_path(cls, v: str) -> str:
        if v and os.path.exists(v):
            return os.path.abspath(v)
        candidates = [
            v,
            os.path.join(os.path.dirname(__file__), "../../data/optimized_laptops.csv"),
            os.path.join(os.path.dirname(__file__), "../data/optimized_laptops.csv"),
            os.path.abspath("data/optimized_laptops.csv"),
            os.path.abspath("../data/optimized_laptops.csv"),
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return os.path.abspath(c)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [str(parsed)]
            except Exception:
                return [v]
        return v

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "../.env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
