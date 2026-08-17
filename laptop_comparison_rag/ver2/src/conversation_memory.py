from __future__ import annotations

import argparse
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "conversation_memory.db"
)


# ============================================================
# DATABASE VERSION
# ============================================================

SCHEMA_VERSION = 1


# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class Conversation:
    session_id: str
    created_at: str
    updated_at: str


@dataclass
class Message:
    message_id: int
    session_id: str
    role: str
    content: str
    created_at: str
    turn_id: Optional[int]


@dataclass
class Turn:
    turn_id: int
    session_id: str
    user_message_id: Optional[int]
    assistant_message_id: Optional[int]
    created_at: str


@dataclass
class PresentedProduct:
    session_id: str
    turn_id: int
    product_id: str
    position: int
    product_name: Optional[str]
    brand: Optional[str]
    price_inr: Optional[float]
    metadata: Dict[str, Any]


@dataclass
class ConversationState:
    """
    Persistent state that can be consumed by chatbot/query
    orchestration.

    This is intentionally structured rather than a free-form
    LLM-generated summary.
    """

    filters: Dict[str, Any]
    preferences: List[str]
    semantic_query: Optional[str]
    last_user_query: Optional[str]
    last_retrieved_product_ids: List[str]
    last_presented_product_ids: List[str]


# ============================================================
# VALIDATION
# ============================================================

VALID_ROLES = {
    "system",
    "user",
    "assistant",
    "tool",
}


def validate_role(role: str) -> str:
    role = str(role).strip().lower()

    if role not in VALID_ROLES:
        raise ValueError(
            "Invalid message role: "
            + role
        )

    return role


def validate_session_id(
    session_id: str,
) -> str:
    session_id = str(session_id).strip()

    if not session_id:
        raise ValueError(
            "session_id cannot be empty."
        )

    return session_id


def validate_content(
    content: str,
) -> str:
    if content is None:
        raise ValueError(
            "Message content cannot be None."
        )

    content = str(content)

    if not content.strip():
        raise ValueError(
            "Message content cannot be empty."
        )

    return content


# ============================================================
# DATETIME
# ============================================================

def utc_now() -> str:
    """
    Store timestamps in ISO-8601 UTC format.
    """
    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# JSON HELPERS
# ============================================================

def serialize_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def deserialize_json(
    value: Optional[str],
    default: Any,
) -> Any:
    if value is None:
        return default

    try:
        return json.loads(value)
    except (
        json.JSONDecodeError,
        TypeError,
    ):
        return default


# ============================================================
# DATABASE MANAGER
# ============================================================

class ConversationMemory:
    """
    Persistent SQLite-backed conversation state manager.

    Responsibilities:
        - Session lifecycle
        - Message persistence
        - Turn persistence
        - Product presentation history
        - Structured conversation state
        - Deterministic product-reference resolution

    This class deliberately does NOT:
        - call an LLM
        - call ChromaDB
        - perform retrieval
        - rank products
        - generate answers
    """

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
    ):
        self.db_path = Path(
            db_path
        )

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

        self._initialize_database()

    # ========================================================
    # CONNECTION
    # ========================================================

    @contextmanager
    def _connection(self):
        """
        Open a fresh SQLite connection for each operation.

        This avoids sharing SQLite connection objects between
        threads and keeps transaction boundaries explicit.
        """
        connection = sqlite3.connect(
            str(self.db_path),
            timeout=30,
            isolation_level=None,
        )

        connection.row_factory = sqlite3.Row

        try:
            connection.execute(
                "PRAGMA foreign_keys = ON"
            )

            connection.execute(
                "PRAGMA journal_mode = WAL"
            )

            connection.execute(
                "PRAGMA synchronous = NORMAL"
            )

            connection.execute(
                "PRAGMA busy_timeout = 30000"
            )

            yield connection

        finally:
            connection.close()

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def _initialize_database(self) -> None:
        with self._lock:
            with self._connection() as connection:

                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS schema_info (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        version INTEGER NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS conversations (
                        session_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS messages (
                        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        turn_id INTEGER,
                        FOREIGN KEY (
                            session_id
                        )
                        REFERENCES conversations (
                            session_id
                        )
                        ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS turns (
                        turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        user_message_id INTEGER,
                        assistant_message_id INTEGER,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (
                            session_id
                        )
                        REFERENCES conversations (
                            session_id
                        )
                        ON DELETE CASCADE,
                        FOREIGN KEY (
                            user_message_id
                        )
                        REFERENCES messages (
                            message_id
                        )
                        ON DELETE SET NULL,
                        FOREIGN KEY (
                            assistant_message_id
                        )
                        REFERENCES messages (
                            message_id
                        )
                        ON DELETE SET NULL
                    );

                    CREATE TABLE IF NOT EXISTS presented_products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        turn_id INTEGER NOT NULL,
                        product_id TEXT NOT NULL,
                        position INTEGER NOT NULL,
                        product_name TEXT,
                        brand TEXT,
                        price_inr REAL,
                        metadata_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,

                        UNIQUE (
                            session_id,
                            turn_id,
                            position
                        ),

                        FOREIGN KEY (
                            session_id
                        )
                        REFERENCES conversations (
                            session_id
                        )
                        ON DELETE CASCADE,

                        FOREIGN KEY (
                            turn_id
                        )
                        REFERENCES turns (
                            turn_id
                        )
                        ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS conversation_state (
                        session_id TEXT PRIMARY KEY,
                        state_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL,

                        FOREIGN KEY (
                            session_id
                        )
                        REFERENCES conversations (
                            session_id
                        )
                        ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, message_id);

                    CREATE INDEX IF NOT EXISTS idx_turns_session
                    ON turns(session_id, turn_id);

                    CREATE INDEX IF NOT EXISTS idx_products_session_turn
                    ON presented_products(
                        session_id,
                        turn_id,
                        position
                    );
                    """
                )

                existing = connection.execute(
                    """
                    SELECT version
                    FROM schema_info
                    WHERE id = 1
                    """
                ).fetchone()

                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO schema_info (
                            id,
                            version
                        )
                        VALUES (1, ?)
                        """,
                        (SCHEMA_VERSION,),
                    )

                elif int(existing["version"]) != SCHEMA_VERSION:
                    raise RuntimeError(
                        "Unsupported conversation-memory "
                        "schema version: "
                        + str(existing["version"])
                    )

    # ========================================================
    # SESSION LIFECYCLE
    # ========================================================

    def create_session(
        self,
        session_id: Optional[str] = None,
    ) -> str:

        if session_id is None:
            session_id = uuid.uuid4().hex

        session_id = validate_session_id(
            session_id
        )

        now = utc_now()

        with self._lock:
            with self._connection() as connection:

                existing = connection.execute(
                    """
                    SELECT session_id
                    FROM conversations
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()

                if existing is not None:
                    raise ValueError(
                        "Session already exists: "
                        + session_id
                    )

                connection.execute(
                    """
                    INSERT INTO conversations (
                        session_id,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        session_id,
                        now,
                        now,
                    ),
                )

                connection.execute(
                    """
                    INSERT INTO conversation_state (
                        session_id,
                        state_json,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        session_id,
                        serialize_json(
                            self._default_state()
                        ),
                        now,
                    ),
                )

        return session_id

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
    ) -> str:

        if session_id is None:
            return self.create_session()

        session_id = validate_session_id(
            session_id
        )

        if not self.session_exists(
            session_id
        ):
            self.create_session(
                session_id
            )

        return session_id

    def session_exists(
        self,
        session_id: str,
    ) -> bool:

        session_id = validate_session_id(
            session_id
        )

        with self._connection() as connection:

            row = connection.execute(
                """
                SELECT 1
                FROM conversations
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        return row is not None

    def delete_session(
        self,
        session_id: str,
    ) -> None:

        session_id = validate_session_id(
            session_id
        )

        with self._lock:
            with self._connection() as connection:

                connection.execute(
                    """
                    DELETE FROM conversations
                    WHERE session_id = ?
                    """,
                    (session_id,),
                )

    def get_conversation(
        self,
        session_id: str,
    ) -> Optional[Conversation]:

        session_id = validate_session_id(
            session_id
        )

        with self._connection() as connection:

            row = connection.execute(
                """
                SELECT
                    session_id,
                    created_at,
                    updated_at
                FROM conversations
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        return Conversation(
            session_id=row["session_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ========================================================
    # INTERNAL STATE
    # ========================================================

    @staticmethod
    def _default_state() -> Dict[str, Any]:
        return {
            "filters": {},
            "preferences": [],
            "semantic_query": None,
            "last_user_query": None,
            "last_retrieved_product_ids": [],
            "last_presented_product_ids": [],
        }

    def get_state(
        self,
        session_id: str,
    ) -> ConversationState:

        session_id = validate_session_id(
            session_id
        )

        with self._connection() as connection:

            row = connection.execute(
                """
                SELECT state_json
                FROM conversation_state
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            if not self.session_exists(
                session_id
            ):
                raise ValueError(
                    "Session does not exist: "
                    + session_id
                )

            return ConversationState(
                filters={},
                preferences=[],
                semantic_query=None,
                last_user_query=None,
                last_retrieved_product_ids=[],
                last_presented_product_ids=[],
            )

        raw = deserialize_json(
            row["state_json"],
            {},
        )

        return ConversationState(
            filters=raw.get(
                "filters",
                {},
            ),
            preferences=list(
                raw.get(
                    "preferences",
                    [],
                )
            ),
            semantic_query=raw.get(
                "semantic_query"
            ),
            last_user_query=raw.get(
                "last_user_query"
            ),
            last_retrieved_product_ids=list(
                raw.get(
                    "last_retrieved_product_ids",
                    [],
                )
            ),
            last_presented_product_ids=list(
                raw.get(
                    "last_presented_product_ids",
                    [],
                )
            ),
        )

    def update_state(
        self,
        session_id: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        preferences: Optional[Sequence[str]] = None,
        semantic_query: Optional[str] = None,
        last_user_query: Optional[str] = None,
        last_retrieved_product_ids: Optional[
            Sequence[str]
        ] = None,
        last_presented_product_ids: Optional[
            Sequence[str]
        ] = None,
        merge: bool = True,
    ) -> ConversationState:

        session_id = validate_session_id(
            session_id
        )

        if not self.session_exists(
            session_id
        ):
            raise ValueError(
                "Session does not exist: "
                + session_id
            )

        current = self.get_state(
            session_id
        )

        if merge:
            new_state = {
                "filters": dict(
                    current.filters
                ),
                "preferences": list(
                    current.preferences
                ),
                "semantic_query": (
                    current.semantic_query
                ),
                "last_user_query": (
                    current.last_user_query
                ),
                "last_retrieved_product_ids": list(
                    current.last_retrieved_product_ids
                ),
                "last_presented_product_ids": list(
                    current.last_presented_product_ids
                ),
            }

        else:
            new_state = self._default_state()

        if filters is not None:
            new_state["filters"] = dict(
                filters
            )

        if preferences is not None:
            new_state["preferences"] = list(
                preferences
            )

        if semantic_query is not None:
            new_state["semantic_query"] = (
                semantic_query
            )

        if last_user_query is not None:
            new_state["last_user_query"] = (
                last_user_query
            )

        if last_retrieved_product_ids is not None:
            new_state[
                "last_retrieved_product_ids"
            ] = [
                str(product_id)
                for product_id
                in last_retrieved_product_ids
            ]

        if last_presented_product_ids is not None:
            new_state[
                "last_presented_product_ids"
            ] = [
                str(product_id)
                for product_id
                in last_presented_product_ids
            ]

        now = utc_now()

        with self._lock:
            with self._connection() as connection:

                connection.execute(
                    """
                    UPDATE conversation_state
                    SET
                        state_json = ?,
                        updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        serialize_json(
                            new_state
                        ),
                        now,
                        session_id,
                    ),
                )

                connection.execute(
                    """
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        now,
                        session_id,
                    ),
                )

        return ConversationState(
            filters=new_state["filters"],
            preferences=new_state[
                "preferences"
            ],
            semantic_query=new_state[
                "semantic_query"
            ],
            last_user_query=new_state[
                "last_user_query"
            ],
            last_retrieved_product_ids=new_state[
                "last_retrieved_product_ids"
            ],
            last_presented_product_ids=new_state[
                "last_presented_product_ids"
            ],
        )

    # ========================================================
    # MESSAGES
    # ========================================================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        turn_id: Optional[int] = None,
    ) -> int:

        session_id = validate_session_id(
            session_id
        )

        role = validate_role(
            role
        )

        content = validate_content(
            content
        )

        if not self.session_exists(
            session_id
        ):
            raise ValueError(
                "Session does not exist: "
                + session_id
            )

        now = utc_now()

        with self._lock:
            with self._connection() as connection:

                cursor = connection.execute(
                    """
                    INSERT INTO messages (
                        session_id,
                        role,
                        content,
                        created_at,
                        turn_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        role,
                        content,
                        now,
                        turn_id,
                    ),
                )

                message_id = int(
                    cursor.lastrowid
                )

                connection.execute(
                    """
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        now,
                        session_id,
                    ),
                )

        return message_id

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        before_message_id: Optional[int] = None,
    ) -> List[Message]:

        session_id = validate_session_id(
            session_id
        )

        if limit is not None and limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        query = """
            SELECT
                message_id,
                session_id,
                role,
                content,
                created_at,
                turn_id
            FROM messages
            WHERE session_id = ?
        """

        parameters: List[Any] = [
            session_id
        ]

        if before_message_id is not None:
            query += """
                AND message_id < ?
            """

            parameters.append(
                int(before_message_id)
            )

        query += """
            ORDER BY message_id DESC
        """

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(
                int(limit)
            )

        with self._connection() as connection:

            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        # Return chronological order.
        rows = list(
            reversed(rows)
        )

        return [
            Message(
                message_id=int(
                    row["message_id"]
                ),
                session_id=row[
                    "session_id"
                ],
                role=row["role"],
                content=row["content"],
                created_at=row[
                    "created_at"
                ],
                turn_id=(
                    int(row["turn_id"])
                    if row["turn_id"] is not None
                    else None
                ),
            )
            for row in rows
        ]

    # ========================================================
    # TURNS
    # ========================================================

    def create_turn(
        self,
        session_id: str,
        user_content: str,
    ) -> Turn:

        session_id = validate_session_id(
            session_id
        )

        user_content = validate_content(
            user_content
        )

        if not self.session_exists(
            session_id
        ):
            raise ValueError(
                "Session does not exist: "
                + session_id
            )

        now = utc_now()

        with self._lock:
            with self._connection() as connection:

                cursor = connection.execute(
                    """
                    INSERT INTO turns (
                        session_id,
                        created_at
                    )
                    VALUES (?, ?)
                    """,
                    (
                        session_id,
                        now,
                    ),
                )

                turn_id = int(
                    cursor.lastrowid
                )

                cursor = connection.execute(
                    """
                    INSERT INTO messages (
                        session_id,
                        role,
                        content,
                        created_at,
                        turn_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        "user",
                        user_content,
                        now,
                        turn_id,
                    ),
                )

                user_message_id = int(
                    cursor.lastrowid
                )

                connection.execute(
                    """
                    UPDATE turns
                    SET user_message_id = ?
                    WHERE turn_id = ?
                    """,
                    (
                        user_message_id,
                        turn_id,
                    ),
                )

                connection.execute(
                    """
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        now,
                        session_id,
                    ),
                )

        return Turn(
            turn_id=turn_id,
            session_id=session_id,
            user_message_id=user_message_id,
            assistant_message_id=None,
            created_at=now,
        )

    def complete_turn(
        self,
        turn_id: int,
        assistant_content: str,
    ) -> Turn:

        assistant_content = validate_content(
            assistant_content
        )

        now = utc_now()

        with self._lock:
            with self._connection() as connection:

                turn = connection.execute(
                    """
                    SELECT
                        turn_id,
                        session_id,
                        user_message_id,
                        assistant_message_id,
                        created_at
                    FROM turns
                    WHERE turn_id = ?
                    """,
                    (int(turn_id),),
                ).fetchone()

                if turn is None:
                    raise ValueError(
                        "Turn does not exist: "
                        + str(turn_id)
                    )

                if turn["assistant_message_id"] is not None:
                    raise ValueError(
                        "Turn is already completed: "
                        + str(turn_id)
                    )

                cursor = connection.execute(
                    """
                    INSERT INTO messages (
                        session_id,
                        role,
                        content,
                        created_at,
                        turn_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        turn["session_id"],
                        "assistant",
                        assistant_content,
                        now,
                        int(turn_id),
                    ),
                )

                assistant_message_id = int(
                    cursor.lastrowid
                )

                connection.execute(
                    """
                    UPDATE turns
                    SET assistant_message_id = ?
                    WHERE turn_id = ?
                    """,
                    (
                        assistant_message_id,
                        int(turn_id),
                    ),
                )

                connection.execute(
                    """
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        now,
                        turn["session_id"],
                    ),
                )

        return Turn(
            turn_id=int(
                turn["turn_id"]
            ),
            session_id=turn[
                "session_id"
            ],
            user_message_id=(
                int(turn["user_message_id"])
                if turn["user_message_id"] is not None
                else None
            ),
            assistant_message_id=assistant_message_id,
            created_at=turn[
                "created_at"
            ],
        )

    def get_turn(
        self,
        turn_id: int,
    ) -> Optional[Turn]:

        with self._connection() as connection:

            row = connection.execute(
                """
                SELECT
                    turn_id,
                    session_id,
                    user_message_id,
                    assistant_message_id,
                    created_at
                FROM turns
                WHERE turn_id = ?
                """,
                (int(turn_id),),
            ).fetchone()

        if row is None:
            return None

        return Turn(
            turn_id=int(
                row["turn_id"]
            ),
            session_id=row[
                "session_id"
            ],
            user_message_id=(
                int(row["user_message_id"])
                if row["user_message_id"] is not None
                else None
            ),
            assistant_message_id=(
                int(row["assistant_message_id"])
                if row["assistant_message_id"] is not None
                else None
            ),
            created_at=row[
                "created_at"
            ],
        )

    def get_recent_turns(
        self,
        session_id: str,
        limit: int = 5,
    ) -> List[Turn]:

        session_id = validate_session_id(
            session_id
        )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        with self._connection() as connection:

            rows = connection.execute(
                """
                SELECT
                    turn_id,
                    session_id,
                    user_message_id,
                    assistant_message_id,
                    created_at
                FROM turns
                WHERE session_id = ?
                ORDER BY turn_id DESC
                LIMIT ?
                """,
                (
                    session_id,
                    int(limit),
                ),
            ).fetchall()

        rows = list(
            reversed(rows)
        )

        return [
            Turn(
                turn_id=int(
                    row["turn_id"]
                ),
                session_id=row[
                    "session_id"
                ],
                user_message_id=(
                    int(row["user_message_id"])
                    if row["user_message_id"] is not None
                    else None
                ),
                assistant_message_id=(
                    int(
                        row[
                            "assistant_message_id"
                        ]
                    )
                    if row[
                        "assistant_message_id"
                    ] is not None
                    else None
                ),
                created_at=row[
                    "created_at"
                ],
            )
            for row in rows
        ]

    # ========================================================
    # PRESENTED PRODUCTS
    # ========================================================

    def save_presented_products(
        self,
        session_id: str,
        turn_id: int,
        products: Sequence[Dict[str, Any]],
    ) -> List[PresentedProduct]:

        session_id = validate_session_id(
            session_id
        )

        if not products:
            return []

        turn = self.get_turn(
            int(turn_id)
        )

        if turn is None:
            raise ValueError(
                "Turn does not exist: "
                + str(turn_id)
            )

        if turn.session_id != session_id:
            raise ValueError(
                "Turn does not belong to the session."
            )

        normalized_products = []

        for index, product in enumerate(
            products,
            start=1,
        ):

            if not isinstance(
                product,
                dict,
            ):
                raise ValueError(
                    "Each product must be a dictionary."
                )

            product_id = (
                product.get("product_id")
                or product.get("id")
            )

            if product_id is None:
                raise ValueError(
                    "Presented product is missing product_id."
                )

            product_id = str(
                product_id
            ).strip()

            if not product_id:
                raise ValueError(
                    "Presented product has empty product_id."
                )

            metadata = product.get(
                "metadata",
                {},
            )

            if not isinstance(
                metadata,
                dict,
            ):
                metadata = {}

            product_name = (
                product.get(
                    "product_name"
                )
                or metadata.get(
                    "product_name"
                )
            )

            brand = (
                product.get(
                    "brand"
                )
                or metadata.get(
                    "brand"
                )
            )

            price = (
                product.get(
                    "price_inr"
                )
            )

            if price is None:
                price = metadata.get(
                    "price_inr"
                )

            try:
                price = (
                    float(price)
                    if price is not None
                    else None
                )
            except (
                TypeError,
                ValueError,
            ):
                price = None

            normalized_products.append(
                PresentedProduct(
                    session_id=session_id,
                    turn_id=int(turn_id),
                    product_id=product_id,
                    position=index,
                    product_name=(
                        str(product_name)
                        if product_name is not None
                        else None
                    ),
                    brand=(
                        str(brand)
                        if brand is not None
                        else None
                    ),
                    price_inr=price,
                    metadata=dict(metadata),
                )
            )

        now = utc_now()

        with self._lock:
            with self._connection() as connection:

                # One turn represents one recommendation/display
                # state. Re-saving products replaces that turn's
                # previous positions deterministically.
                connection.execute(
                    """
                    DELETE FROM presented_products
                    WHERE session_id = ?
                      AND turn_id = ?
                    """,
                    (
                        session_id,
                        int(turn_id),
                    ),
                )

                for product in normalized_products:

                    connection.execute(
                        """
                        INSERT INTO presented_products (
                            session_id,
                            turn_id,
                            product_id,
                            position,
                            product_name,
                            brand,
                            price_inr,
                            metadata_json,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            product.session_id,
                            product.turn_id,
                            product.product_id,
                            product.position,
                            product.product_name,
                            product.brand,
                            product.price_inr,
                            serialize_json(
                                product.metadata
                            ),
                            now,
                        ),
                    )

                connection.execute(
                    """
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        now,
                        session_id,
                    ),
                )

        self.update_state(
            session_id,
            last_presented_product_ids=[
                product.product_id
                for product
                in normalized_products
            ],
        )

        return normalized_products

    def get_products_for_turn(
        self,
        turn_id: int,
    ) -> List[PresentedProduct]:

        with self._connection() as connection:

            rows = connection.execute(
                """
                SELECT
                    session_id,
                    turn_id,
                    product_id,
                    position,
                    product_name,
                    brand,
                    price_inr,
                    metadata_json
                FROM presented_products
                WHERE turn_id = ?
                ORDER BY position ASC
                """,
                (int(turn_id),),
            ).fetchall()

        return [
            PresentedProduct(
                session_id=row[
                    "session_id"
                ],
                turn_id=int(
                    row["turn_id"]
                ),
                product_id=row[
                    "product_id"
                ],
                position=int(
                    row["position"]
                ),
                product_name=row[
                    "product_name"
                ],
                brand=row["brand"],
                price_inr=row[
                    "price_inr"
                ],
                metadata=deserialize_json(
                    row["metadata_json"],
                    {},
                ),
            )
            for row in rows
        ]

    def get_latest_presented_products(
        self,
        session_id: str,
    ) -> List[PresentedProduct]:

        session_id = validate_session_id(
            session_id
        )

        with self._connection() as connection:

            # FIX: Query the presented_products table directly to find the 
            # latest turn that actually contained products.
            latest_turn = connection.execute(
                """
                SELECT turn_id
                FROM presented_products
                WHERE session_id = ?
                ORDER BY turn_id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()

            if latest_turn is None:
                return []

            turn_id = int(
                latest_turn["turn_id"]
            )

        return self.get_products_for_turn(
            turn_id
        )
    # ========================================================
    # PRODUCT REFERENCE RESOLUTION
    # ========================================================

    def resolve_position(
        self,
        session_id: str,
        position: int,
    ) -> Optional[PresentedProduct]:
        """
        Resolve:
            first  -> position 1
            second -> position 2
            ...
        against the most recent presented product set.
        """
        if position <= 0:
            raise ValueError(
                "position must be >= 1."
            )

        products = (
            self.get_latest_presented_products(
                session_id
            )
        )

        for product in products:
            if product.position == position:
                return product

        return None

    def resolve_product_id(
        self,
        session_id: str,
        product_id: str,
    ) -> Optional[PresentedProduct]:

        session_id = validate_session_id(
            session_id
        )

        product_id = str(
            product_id
        ).strip()

        if not product_id:
            return None

        products = (
            self.get_latest_presented_products(
                session_id
            )
        )

        for product in products:
            if product.product_id == product_id:
                return product

        return None

    # ========================================================
    # NATURAL ORDINAL RESOLUTION
    # ========================================================

    ORDINALS = {
        "first": 1,
        "1st": 1,

        "second": 2,
        "2nd": 2,

        "third": 3,
        "3rd": 3,

        "fourth": 4,
        "4th": 4,

        "fifth": 5,
        "5th": 5,

        "sixth": 6,
        "6th": 6,

        "seventh": 7,
        "7th": 7,

        "eighth": 8,
        "8th": 8,

        "ninth": 9,
        "9th": 9,

        "tenth": 10,
        "10th": 10,
    }

    def extract_ordinal(
        self,
        text: str,
    ) -> Optional[int]:

        normalized = (
            str(text)
            .lower()
            .strip()
        )

        # Exact ordinal token.
        pattern = (
            r"(?<![a-z0-9])("
            + "|".join(
                sorted(
                    self.ORDINALS,
                    key=len,
                    reverse=True,
                )
            )
            + r")(?![a-z0-9])"
        )

        match = __import__(
            "re"
        ).search(
            pattern,
            normalized,
        )

        if match is None:
            return None

        return self.ORDINALS[
            match.group(1)
        ]

    def resolve_ordinal_reference(
        self,
        session_id: str,
        text: str,
    ) -> Optional[PresentedProduct]:

        position = self.extract_ordinal(
            text
        )

        if position is None:
            return None

        return self.resolve_position(
            session_id,
            position,
        )

    # ========================================================
    # LAST PRODUCT SET
    # ========================================================

    def get_last_product_ids(
        self,
        session_id: str,
    ) -> List[str]:

        return [
            product.product_id
            for product
            in self.get_latest_presented_products(
                session_id
            )
        ]

    # ========================================================
    # CONTEXT
    # ========================================================

    def build_context(
        self,
        session_id: str,
        message_limit: int = 10,
        turn_limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Return structured application context.

        This is the object that chatbot.py can use when deciding
        whether a query is new, a follow-up, or a product reference.
        """
        state = self.get_state(
            session_id
        )

        messages = self.get_messages(
            session_id,
            limit=message_limit,
        )

        turns = self.get_recent_turns(
            session_id,
            limit=turn_limit,
        )

        latest_products = (
            self.get_latest_presented_products(
                session_id
            )
        )

        return {
            "session_id": session_id,

            "state": asdict(state),

            "messages": [
                {
                    "message_id": message.message_id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at,
                    "turn_id": message.turn_id,
                }
                for message in messages
            ],

            "turns": [
                asdict(turn)
                for turn in turns
            ],

            "latest_products": [
                {
                    "product_id": product.product_id,
                    "position": product.position,
                    "product_name": product.product_name,
                    "brand": product.brand,
                    "price_inr": product.price_inr,
                    "metadata": product.metadata,
                }
                for product
                in latest_products
            ],
        }

    # ========================================================
    # TURN + STATE ATOMIC OPERATION
    # ========================================================

    def record_completed_turn(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        *,
        filters: Optional[
            Dict[str, Any]
        ] = None,
        preferences: Optional[
            Sequence[str]
        ] = None,
        semantic_query: Optional[
            str
        ] = None,
        retrieved_product_ids: Optional[
            Sequence[str]
        ] = None,
        presented_products: Optional[
            Sequence[Dict[str, Any]]
        ] = None,
    ) -> Turn:
        """
        Convenience method for chatbot.py.

        Records:
            user message
            assistant response
            retrieved IDs
            displayed products
            structured conversation state

        The entire operation is performed in one SQLite
        transaction.
        """
        session_id = validate_session_id(
            session_id
        )

        user_query = validate_content(
            user_query
        )

        assistant_response = validate_content(
            assistant_response
        )

        if not self.session_exists(
            session_id
        ):
            raise ValueError(
                "Session does not exist: "
                + session_id
            )

        now = utc_now()

        with self._lock:
            with self._connection() as connection:

                # --------------------------------------------
                # Create turn
                # --------------------------------------------

                cursor = connection.execute(
                    """
                    INSERT INTO turns (
                        session_id,
                        created_at
                    )
                    VALUES (?, ?)
                    """,
                    (
                        session_id,
                        now,
                    ),
                )

                turn_id = int(
                    cursor.lastrowid
                )

                # --------------------------------------------
                # User message
                # --------------------------------------------

                cursor = connection.execute(
                    """
                    INSERT INTO messages (
                        session_id,
                        role,
                        content,
                        created_at,
                        turn_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        "user",
                        user_query,
                        now,
                        turn_id,
                    ),
                )

                user_message_id = int(
                    cursor.lastrowid
                )

                # --------------------------------------------
                # Assistant message
                # --------------------------------------------

                cursor = connection.execute(
                    """
                    INSERT INTO messages (
                        session_id,
                        role,
                        content,
                        created_at,
                        turn_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        "assistant",
                        assistant_response,
                        now,
                        turn_id,
                    ),
                )

                assistant_message_id = int(
                    cursor.lastrowid
                )

                # --------------------------------------------
                # Turn references
                # --------------------------------------------

                connection.execute(
                    """
                    UPDATE turns
                    SET
                        user_message_id = ?,
                        assistant_message_id = ?
                    WHERE turn_id = ?
                    """,
                    (
                        user_message_id,
                        assistant_message_id,
                        turn_id,
                    ),
                )

                # --------------------------------------------
                # Conversation state
                # --------------------------------------------

                current_state = self.get_state(
                    session_id
                )

                state = {
                    "filters": (
                        dict(filters)
                        if filters is not None
                        else current_state.filters
                    ),
                    "preferences": (
                        list(preferences)
                        if preferences is not None
                        else current_state.preferences
                    ),
                    "semantic_query": (
                        semantic_query
                        if semantic_query is not None
                        else current_state.semantic_query
                    ),
                    "last_user_query": user_query,
                    "last_retrieved_product_ids": (
                        [
                            str(product_id)
                            for product_id
                            in retrieved_product_ids
                        ]
                        if retrieved_product_ids
                        is not None
                        else (
                            current_state
                            .last_retrieved_product_ids
                        )
                    ),
                    "last_presented_product_ids": (
                        [
                            str(
                                product.get(
                                    "product_id"
                                )
                                or product.get(
                                    "id"
                                )
                            )
                            for product
                            in presented_products
                        ]
                        if presented_products
                        else (
                            current_state
                            .last_presented_product_ids
                        )
                    ),
                }

                connection.execute(
                    """
                    UPDATE conversation_state
                    SET
                        state_json = ?,
                        updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        serialize_json(
                            state
                        ),
                        now,
                        session_id,
                    ),
                )

                # --------------------------------------------
                # Presented products
                # --------------------------------------------

                if presented_products:
                    for position, product in enumerate(
                        presented_products,
                        start=1,
                    ):

                        product_id = (
                            product.get(
                                "product_id"
                            )
                            or product.get(
                                "id"
                            )
                        )

                        if product_id is None:
                            raise ValueError(
                                "Presented product "
                                "is missing product_id."
                            )

                        metadata = product.get(
                            "metadata",
                            {},
                        )

                        if not isinstance(
                            metadata,
                            dict,
                        ):
                            metadata = {}

                        product_name = (
                            product.get(
                                "product_name"
                            )
                            or metadata.get(
                                "product_name"
                            )
                        )

                        brand = (
                            product.get(
                                "brand"
                            )
                            or metadata.get(
                                "brand"
                            )
                        )

                        price = (
                            product.get(
                                "price_inr"
                            )
                        )

                        if price is None:
                            price = metadata.get(
                                "price_inr"
                            )

                        try:
                            price = (
                                float(price)
                                if price is not None
                                else None
                            )
                        except (
                            TypeError,
                            ValueError,
                        ):
                            price = None

                        connection.execute(
                            """
                            INSERT INTO presented_products (
                                session_id,
                                turn_id,
                                product_id,
                                position,
                                product_name,
                                brand,
                                price_inr,
                                metadata_json,
                                created_at
                            )
                            VALUES (
                                ?, ?, ?, ?, ?, ?, ?, ?, ?
                            )
                            """,
                            (
                                session_id,
                                turn_id,
                                str(product_id),
                                position,
                                (
                                    str(product_name)
                                    if product_name
                                    is not None
                                    else None
                                ),
                                (
                                    str(brand)
                                    if brand
                                    is not None
                                    else None
                                ),
                                price,
                                serialize_json(
                                    metadata
                                ),
                                now,
                            ),
                        )

                # --------------------------------------------
                # Conversation timestamp
                # --------------------------------------------

                connection.execute(
                    """
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        now,
                        session_id,
                    ),
                )

        return Turn(
            turn_id=turn_id,
            session_id=session_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            created_at=now,
        )


# ============================================================
# SIMPLE COMMAND-LINE TESTS
# ============================================================

def run_smoke_test(
    db_path: Path,
) -> None:

    print("=" * 72)
    print("VER2 - CONVERSATION MEMORY SMOKE TEST")
    print("=" * 72)

    memory = ConversationMemory(
        db_path=db_path
    )

    session_id = memory.create_session()

    print(
        "\nCreated session:",
        session_id,
    )

    # --------------------------------------------------------
    # Turn 1
    # --------------------------------------------------------

    turn_1 = memory.record_completed_turn(
        session_id=session_id,
        user_query=(
            "I need an ASUS laptop under 70000 "
            "for coding."
        ),
        assistant_response=(
            "Here are three laptops that match "
            "your requirements."
        ),
        filters={
            "brands": ["ASUS"],
            "max_price": 70000,
        },
        preferences=[
            "coding"
        ],
        semantic_query=(
            "ASUS laptop coding"
        ),
        retrieved_product_ids=[
            "LAP_TEST_001",
            "LAP_TEST_002",
            "LAP_TEST_003",
        ],
        presented_products=[
            {
                "product_id": "LAP_TEST_001",
                "product_name": "ASUS Test Laptop A",
                "brand": "ASUS",
                "price_inr": 64990,
                "metadata": {
                    "ram_gb": 16,
                    "price_inr": 64990,
                },
            },
            {
                "product_id": "LAP_TEST_002",
                "product_name": "ASUS Test Laptop B",
                "brand": "ASUS",
                "price_inr": 67990,
                "metadata": {
                    "ram_gb": 16,
                    "price_inr": 67990,
                },
            },
            {
                "product_id": "LAP_TEST_003",
                "product_name": "ASUS Test Laptop C",
                "brand": "ASUS",
                "price_inr": 69990,
                "metadata": {
                    "ram_gb": 8,
                    "price_inr": 69990,
                },
            },
        ],
    )

    print(
        "\nCompleted turn:",
        turn_1.turn_id,
    )

    # --------------------------------------------------------
    # Resolve first product
    # --------------------------------------------------------

    first = memory.resolve_position(
        session_id,
        1,
    )

    print(
        "\nFirst product:",
        first.product_id
        if first
        else None,
    )

    # --------------------------------------------------------
    # Resolve "second"
    # --------------------------------------------------------

    second = (
        memory.resolve_ordinal_reference(
            session_id,
            "Which is the second one?",
        )
    )

    print(
        "Second product:",
        second.product_id
        if second
        else None,
    )

    # --------------------------------------------------------
    # Add follow-up
    # --------------------------------------------------------

    turn_2 = memory.record_completed_turn(
        session_id=session_id,
        user_query=(
            "Which is the second one?"
        ),
        assistant_response=(
            "The second ASUS laptop is "
            "the stronger choice."
        ),
        filters={
            "brands": ["ASUS"],
            "max_price": 70000,
        },
        preferences=[
            "coding"
        ],
        semantic_query=(
            "second ASUS laptop"
        ),
    )

    print(
        "\nFollow-up turn:",
        turn_2.turn_id,
    )

    # --------------------------------------------------------
    # Retrieve complete context
    # --------------------------------------------------------

    context = memory.build_context(
        session_id=session_id
    )

    print(
        "\nState:"
    )

    print(
        json.dumps(
            context["state"],
            indent=2,
            ensure_ascii=False,
        )
    )

    print(
        "\nLatest products:"
    )

    for product in context[
        "latest_products"
    ]:
        print(
            "  ",
            product["position"],
            product["product_id"],
        )

    # --------------------------------------------------------
    # Clean up the test session
    # --------------------------------------------------------

    memory.delete_session(
        session_id
    )

    print(
        "\nSmoke test completed successfully."
    )


# ============================================================
# CLI
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Manage/test ver2 conversation memory."
        )
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
    )

    parser.add_argument(
        "--smoke-test",
        action="store_true",
    )

    args = parser.parse_args()

    if args.smoke_test:
        run_smoke_test(
            args.db
        )

    else:
        memory = ConversationMemory(
            db_path=args.db
        )

        session_id = memory.create_session()

        print(
            "Created session:",
            session_id,
        )

        print(
            "Database:",
            args.db,
        )


if __name__ == "__main__":
    main()