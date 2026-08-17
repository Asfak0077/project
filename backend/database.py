import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from utils.config import settings

logger = logging.getLogger("backend.database")

def create_db_engine():
    db_url = settings.DATABASE_URL
    try:
        # If using MySQL, attempt to verify / create database if needed
        if "mysql" in db_url:
            # Extract root url without database name to ensure DB exists
            try:
                base_url, db_name = db_url.rsplit("/", 1)
                # Remove query params from db_name if any
                if "?" in db_name:
                    db_name, query_params = db_name.split("?", 1)
                    temp_url = f"{base_url}?{query_params}"
                else:
                    temp_url = base_url
                
                temp_engine = create_engine(
                    temp_url,
                    pool_pre_ping=True,
                    connect_args={"connect_timeout": 10}
                )
                with temp_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    conn.commit()
                temp_engine.dispose()
                logger.info(f"Verified / created MySQL database `{db_name}`.")
            except Exception as e:
                logger.warning(f"Could not auto-create database using base URL: {e}. Trying direct connection...")
        
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=1800,  # Recycle connections every 30 minutes to prevent AWS RDS drops
            pool_size=10,
            max_overflow=20,
            connect_args={"connect_timeout": 10} if "mysql" in db_url else {}
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected successfully to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        return engine
    except Exception as e:
        logger.error(f"Failed to connect to primary database ({db_url}): {e}")
        # Fallback to local SQLite for development resilience if RDS is unreachable
        sqlite_path = os.path.join(os.path.dirname(__file__), "product_assistant.db")
        fallback_url = f"sqlite:///{sqlite_path}"
        logger.warning(f"Falling back to local SQLite database at: {fallback_url}")
        fallback_engine = create_engine(
            fallback_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
        return fallback_engine

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import models  # Ensure all models are registered
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
