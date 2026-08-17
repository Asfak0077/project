import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CTS Hackathon"))
from db import get_db_connection

def migrate_users_table():
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    columns = [
        ("phone", "VARCHAR(50) NULL"),
        ("avatar", "VARCHAR(500) NULL"),
        ("title", "VARCHAR(255) NULL"),
        ("location", "VARCHAR(255) NULL"),
        ("bio", "TEXT NULL"),
        ("is_active", "BOOLEAN DEFAULT 1"),
        ("is_admin", "BOOLEAN DEFAULT 0"),
        ("role_id", "INT NULL"),
        ("updated_at", "DATETIME NULL")
    ]

    cur.execute("SHOW COLUMNS FROM users")
    existing_cols = [r[0].lower() for r in cur.fetchall()]
    print("Existing cols:", existing_cols)

    for col_name, col_type in columns:
        if col_name.lower() not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column already exists: {col_name}")

    cur.execute("SHOW COLUMNS FROM users")
    final_cols = [r[0] for r in cur.fetchall()]
    print("\nFinal users table columns on AWS RDS:\n", final_cols)

    cur.close()
    conn.close()

if __name__ == "__main__":
    migrate_users_table()
