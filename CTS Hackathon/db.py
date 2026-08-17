"""
AWS RDS MySQL Database Connection and CRUD Module
Project: CTS Hackathon Product Assistant
Features:
- Connection pooling via mysql.connector.pooling.MySQLConnectionPool
- Environment-based configuration via python-dotenv
- Resilient connection error handling, timeouts, and reconnection logic
- Context managers for safe cursor and connection lifecycle management
- CRUD operations for Users, Search History, Comparison History, and Recommendation History
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any, Union, cast
from contextlib import contextmanager
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None, override=False):
        if not dotenv_path or not os.path.isfile(dotenv_path):
            return False
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if override or key not in os.environ:
                        os.environ[key] = val
            return True
        except Exception:
            return False

import mysql.connector
from mysql.connector import errorcode
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cts_hackathon.db")

# Load environment variables
# Check local .env first, then parent/workspace .env
env_paths = [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent / "backend" / ".env"
]
for env_path in env_paths:
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)

# Database Configuration from Environment Variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "my_project")
DB_POOL_NAME = os.getenv("DB_POOL_NAME", "aws_rds_pool")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_SSL_CA = os.getenv("DB_SSL_CA", None)  # Optional path to AWS RDS SSL CA bundle (global-bundle.pem)
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

# Global connection pool instance
_connection_pool: Optional[MySQLConnectionPool] = None


def get_db_config() -> Dict[str, Any]:
    """Retrieve active database configuration dictionary."""
    config: Dict[str, Any] = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "connect_timeout": DB_CONNECT_TIMEOUT,
        "autocommit": False,
        "use_pure": False,
    }
    if DB_SSL_CA and os.path.isfile(DB_SSL_CA):
        config["ssl_ca"] = DB_SSL_CA
        config["ssl_verify_cert"] = True
    return config


def init_connection_pool(pool_size: Optional[int] = None, force_recreate: bool = False) -> MySQLConnectionPool:
    """
    Initialize or return the global MySQL Connection Pool.
    Supports AWS RDS MySQL endpoints with resilient connection pooling.
    """
    global _connection_pool
    if _connection_pool is not None and not force_recreate:
        return _connection_pool

    config = get_db_config()
    actual_pool_size = pool_size or DB_POOL_SIZE

    try:
        # Bootstrap: Ensure target database exists on AWS RDS
        try:
            base_config = config.copy()
            target_db = base_config.pop("database", None)
            temp_conn = mysql.connector.connect(**base_config)
            temp_cur = temp_conn.cursor()
            if target_db:
                temp_cur.execute(f"CREATE DATABASE IF NOT EXISTS `{target_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                temp_conn.commit()
            temp_cur.close()
            temp_conn.close()
            logger.info(f"Verified/Created database '{target_db}' on AWS RDS.")
        except Exception as bootstrap_err:
            logger.debug(f"Database bootstrap check: {bootstrap_err}")

        _connection_pool = MySQLConnectionPool(
            pool_name=DB_POOL_NAME,
            pool_size=actual_pool_size,
            pool_reset_session=True,
            **config
        )
        logger.info(
            f"Successfully initialized MySQL Connection Pool '{DB_POOL_NAME}' "
            f"(size={actual_pool_size}) for host '{DB_HOST}:{DB_PORT}', database '{DB_NAME}'"
        )
        return _connection_pool
    except mysql.connector.Error as err:
        logger.error(f"Failed to initialize MySQL connection pool: {err}")
        raise


def get_db_connection() -> Any:
    """
    Acquire a database connection from the connection pool.
    Falls back to direct connection if the pool is exhausted or uninitialized.
    """
    global _connection_pool
    try:
        if _connection_pool is None:
            init_connection_pool()
        if _connection_pool is not None:
            return _connection_pool.get_connection()
        config = get_db_config()
        return mysql.connector.connect(**config)
    except Exception as pool_err:
        logger.warning(f"Could not get connection from pool ({pool_err}). Attempting direct connection...")
        try:
            config = get_db_config()
            return mysql.connector.connect(**config)
        except mysql.connector.Error as direct_err:
            logger.error(f"Direct connection to AWS RDS MySQL failed: {direct_err}")
            raise direct_err


@contextmanager
def get_db_cursor(dictionary: bool = False, commit: bool = False):
    """
    Context manager for safe database operations.
    Handles acquiring connection, creating cursor, committing transactions,
    and reliably returning connection to the pool.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor
        if commit:
            conn.commit()
    except mysql.connector.Error as err:
        if conn and commit:
            conn.rollback()
        logger.error(f"Database error during cursor operation: {err}")
        raise
    except Exception as e:
        if conn and commit:
            conn.rollback()
        logger.error(f"Unexpected error during database operation: {e}")
        raise
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()  # Returns connection back to pool
            except Exception:
                pass


# ============================================================================
# 1. USER TABLE CRUD OPERATIONS
# ============================================================================

def _normalize_user_dict(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    d = dict(row)
    uid = d.get("user_id") or d.get("id") or 0
    d["user_id"] = int(uid)
    d["id"] = int(uid)
    return d


def create_user(
    name: str,
    email: str,
    password_hash: Optional[str] = None,
    username: Optional[str] = None,
    auth_provider: str = "local",
    google_id: Optional[str] = None
) -> int:
    """Create a new user record and return user_id."""
    clean_email = email.lower().strip()
    clean_name = name.strip() if name else (username or clean_email.split("@")[0])
    clean_username = username or clean_name

    with get_db_cursor(commit=True) as cursor:
        # Detect table columns for schema resilience
        cursor.execute("SHOW COLUMNS FROM users")
        cols = [str(c[0]).lower() for c in cursor.fetchall()]

        insert_cols = ["email", "password_hash", "auth_provider", "google_id"]
        values = [clean_email, password_hash, auth_provider, google_id]

        if "name" in cols:
            insert_cols.insert(0, "name")
            values.insert(0, clean_name)
        if "username" in cols:
            insert_cols.insert(0, "username")
            values.insert(0, clean_username)

        placeholders = ", ".join(["%s"] * len(values))
        col_names = ", ".join([f"`{c}`" for c in insert_cols])
        sql = f"INSERT INTO users ({col_names}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(values))
        new_id = int(cursor.lastrowid or 0)

        # Synchronize user_id column if present
        if "user_id" in cols and new_id > 0:
            cursor.execute("UPDATE users SET user_id = id WHERE id = %s AND (user_id IS NULL OR user_id = 0)", (new_id,))

        return new_id


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user details by email address."""
    clean_email = email.lower().strip()
    with get_db_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE email = %s", (clean_email,))
        row = cursor.fetchone()
        return _normalize_user_dict(dict(row) if row and isinstance(row, dict) else None)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user details by numeric user_id."""
    with get_db_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE user_id = %s OR id = %s LIMIT 1", (user_id, user_id))
        row = cursor.fetchone()
        return _normalize_user_dict(dict(row) if row and isinstance(row, dict) else None)


def get_all_users() -> List[Dict[str, Any]]:
    """Retrieve list of all users."""
    with get_db_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for r in rows:
            if isinstance(r, dict):
                item = _normalize_user_dict(dict(r))
                if item:
                    item.pop("password_hash", None)
                    result.append(item)
        return result


def update_user(user_id: int, update_fields: Dict[str, Any]) -> bool:
    """Update specific fields for a user."""
    if not update_fields:
        return False

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SHOW COLUMNS FROM users")
        available_cols = {str(c[0]).lower(): str(c[0]) for c in cursor.fetchall()}

        filtered = {}
        for k, v in update_fields.items():
            if str(k).lower() in available_cols:
                filtered[available_cols[str(k).lower()]] = v

        if not filtered:
            return False

        set_clauses = [f"`{k}` = %s" for k in filtered.keys()]
        values = list(filtered.values())
        values.extend([user_id, user_id])

        sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = %s OR id = %s"
        cursor.execute(sql, tuple(values))
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    """Delete a user by user_id (cascades to all user history)."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM users WHERE user_id = %s OR id = %s", (user_id, user_id))
        return cursor.rowcount > 0


# ============================================================================
# 2. SEARCH HISTORY CRUD OPERATIONS
# ============================================================================

def log_user_search(user_id: int, query_text: str, filters: Optional[Dict[str, Any]] = None) -> int:
    """Log a user search query with optional filter parameters."""
    filters_json = json.dumps(filters) if filters else None
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO search_history (user_id, query_text, filters_applied) VALUES (%s, %s, %s)",
            (user_id, query_text.strip(), filters_json)
        )
        logger.info(f"Logged search query for user {user_id}: '{query_text}'")
        return int(cursor.lastrowid or 0)


def get_user_search_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve search history for a user, ordered by most recent."""
    with get_db_cursor(dictionary=True) as cursor:
        cursor.execute(
            """SELECT search_id, user_id, query_text, filters_applied, searched_at 
               FROM search_history 
               WHERE user_id = %s 
               ORDER BY searched_at DESC 
               LIMIT %s""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                r = dict(row)
                if isinstance(r.get("filters_applied"), str):
                    try:
                        r["filters_applied"] = json.loads(r["filters_applied"])
                    except Exception:
                        pass
                result.append(r)
        return result


def delete_user_search_history_item(search_id: int, user_id: int) -> bool:
    """Delete a single search history entry for a user."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM search_history WHERE search_id = %s AND user_id = %s",
            (search_id, user_id)
        )
        return cursor.rowcount > 0


def clear_user_search_history(user_id: int) -> int:
    """Clear all search history entries for a user."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM search_history WHERE user_id = %s", (user_id,))
        return cursor.rowcount


# ============================================================================
# 3. COMPARISON HISTORY CRUD OPERATIONS
# ============================================================================

def log_user_comparison(user_id: int, product_list: List[Any], summary: Optional[str] = None) -> int:
    """Log a side-by-side product comparison."""
    products_json = json.dumps(product_list)
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """INSERT INTO comparison_history (user_id, compared_products, notes_or_summary) 
               VALUES (%s, %s, %s)""",
            (user_id, products_json, summary)
        )
        logger.info(f"Logged comparison for user {user_id} ({len(product_list)} products)")
        return int(cursor.lastrowid or 0)


def get_user_comparison_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve comparison history for a user, ordered by most recent."""
    with get_db_cursor(dictionary=True) as cursor:
        cursor.execute(
            """SELECT comparison_id, user_id, compared_products, notes_or_summary, compared_at 
               FROM comparison_history 
               WHERE user_id = %s 
               ORDER BY compared_at DESC 
               LIMIT %s""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                r = dict(row)
                if isinstance(r.get("compared_products"), str):
                    try:
                        r["compared_products"] = json.loads(r["compared_products"])
                    except Exception:
                        pass
                result.append(r)
        return result


def delete_user_comparison_history_item(comparison_id: int, user_id: int) -> bool:
    """Delete a single comparison history entry for a user."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM comparison_history WHERE comparison_id = %s AND user_id = %s",
            (comparison_id, user_id)
        )
        return cursor.rowcount > 0


def clear_user_comparison_history(user_id: int) -> int:
    """Clear all comparison history for a user."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM comparison_history WHERE user_id = %s", (user_id,))
        return cursor.rowcount


# ============================================================================
# 4. RECOMMENDATION HISTORY CRUD OPERATIONS
# ============================================================================

def log_user_recommendation(
    user_id: int,
    user_requirements: Optional[str],
    product_list: List[Any],
    summary: Optional[str] = None
) -> int:
    """Log an AI product recommendation request and response."""
    products_json = json.dumps(product_list)
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """INSERT INTO recommendation_history 
               (user_id, user_requirements, recommended_products, reasoning_summary) 
               VALUES (%s, %s, %s, %s)""",
            (user_id, user_requirements, products_json, summary)
        )
        logger.info(f"Logged recommendation for user {user_id}")
        return int(cursor.lastrowid or 0)


def get_user_recommendation_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recommendation history for a user, ordered by most recent."""
    with get_db_cursor(dictionary=True) as cursor:
        cursor.execute(
            """SELECT recommendation_id, user_id, user_requirements, recommended_products, reasoning_summary, recommended_at 
               FROM recommendation_history 
               WHERE user_id = %s 
               ORDER BY recommended_at DESC 
               LIMIT %s""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                r = dict(row)
                if isinstance(r.get("recommended_products"), str):
                    try:
                        r["recommended_products"] = json.loads(r["recommended_products"])
                    except Exception:
                        pass
                result.append(r)
        return result


def delete_user_recommendation_history_item(recommendation_id: int, user_id: int) -> bool:
    """Delete a single recommendation history entry for a user."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM recommendation_history WHERE recommendation_id = %s AND user_id = %s",
            (recommendation_id, user_id)
        )
        return cursor.rowcount > 0


def clear_user_recommendation_history(user_id: int) -> int:
    """Clear all recommendation history for a user."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM recommendation_history WHERE user_id = %s", (user_id,))
        return cursor.rowcount


# ============================================================================
# 5. SCHEMA INITIALIZATION / MIGRATION
# ============================================================================

def init_schema(schema_file_path: Optional[str] = None) -> bool:
    """
    Execute schema.sql to ensure all database tables and indexes exist on AWS RDS.
    """
    if not schema_file_path:
        schema_file_path = str(Path(__file__).parent / "schema.sql")

    if not os.path.isfile(schema_file_path):
        logger.warning(f"Schema file not found at {schema_file_path}")
        return False

    with open(schema_file_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # Split SQL by statement delimiter
    statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for stmt in statements:
            if stmt.upper().startswith("USE ") or stmt.upper().startswith("CREATE DATABASE"):
                try:
                    cursor.execute(stmt)
                except mysql.connector.Error as err:
                    logger.debug(f"Statement notice ({stmt[:30]}...): {err}")
                continue
            try:
                cursor.execute(stmt)
            except mysql.connector.Error as stmt_err:
                logger.debug(f"Schema execution notice: {stmt_err}")
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database schema initialized successfully on AWS RDS.")
        return True
    except mysql.connector.Error as err:
        logger.error(f"Failed to execute schema initialization: {err}")
        return False
