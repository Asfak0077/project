import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CTS Hackathon"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_db_connection
from database import init_db

def align_all_schemas():
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    print("--- 1. Aligning search_history ---")
    cur.execute("SHOW COLUMNS FROM search_history")
    sh_cols = [r[0].lower() for r in cur.fetchall()]
    print("Existing search_history cols:", sh_cols)
    if "id" not in sh_cols and "search_id" in sh_cols:
        # Atomic switch to id as PK
        try:
            cur.execute("ALTER TABLE search_history MODIFY search_id INT NOT NULL, DROP PRIMARY KEY, MODIFY id INT AUTO_INCREMENT PRIMARY KEY")
        except Exception:
            try:
                cur.execute("ALTER TABLE search_history ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY")
            except Exception as e:
                print("search_history id add error:", e)
    elif "id" not in sh_cols:
        cur.execute("ALTER TABLE search_history ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY")

    # Ensure search_history other columns
    extra_sh = [
        ("search_id", "INT NULL"),
        ("extracted_requirements", "JSON NULL"),
        ("results_count", "INT DEFAULT 0"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("searched_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ]
    for cname, ctype in extra_sh:
        if cname.lower() not in sh_cols:
            try:
                cur.execute(f"ALTER TABLE search_history ADD COLUMN {cname} {ctype}")
                print(f"Added search_history.{cname}")
            except Exception as e:
                print(f"Notice adding search_history.{cname}: {e}")

    print("\n--- 2. Aligning comparison_history ---")
    cur.execute("SHOW COLUMNS FROM comparison_history")
    ch_cols = [r[0].lower() for r in cur.fetchall()]
    print("Existing comparison_history cols:", ch_cols)
    if "id" not in ch_cols and "comparison_id" in ch_cols:
        try:
            cur.execute("ALTER TABLE comparison_history MODIFY comparison_id INT NOT NULL, DROP PRIMARY KEY, MODIFY id INT AUTO_INCREMENT PRIMARY KEY")
        except Exception:
            try:
                cur.execute("ALTER TABLE comparison_history ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY")
            except Exception as e:
                print("comparison_history id add error:", e)
    elif "id" not in ch_cols:
        cur.execute("ALTER TABLE comparison_history ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY")

    extra_ch = [
        ("comparison_id", "INT NULL"),
        ("summary", "TEXT NULL"),
        ("notes_or_summary", "TEXT NULL"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("compared_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ]
    for cname, ctype in extra_ch:
        if cname.lower() not in ch_cols:
            try:
                cur.execute(f"ALTER TABLE comparison_history ADD COLUMN {cname} {ctype}")
                print(f"Added comparison_history.{cname}")
            except Exception as e:
                print(f"Notice adding comparison_history.{cname}: {e}")

    print("\n--- 3. Aligning recommendation_history ---")
    cur.execute("SHOW COLUMNS FROM recommendation_history")
    rh_cols = [r[0].lower() for r in cur.fetchall()]
    print("Existing recommendation_history cols:", rh_cols)
    if "id" not in rh_cols and "recommendation_id" in rh_cols:
        try:
            cur.execute("ALTER TABLE recommendation_history MODIFY recommendation_id INT NOT NULL, DROP PRIMARY KEY, MODIFY id INT AUTO_INCREMENT PRIMARY KEY")
        except Exception:
            try:
                cur.execute("ALTER TABLE recommendation_history ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY")
            except Exception as e:
                print("recommendation_history id add error:", e)
    elif "id" not in rh_cols:
        cur.execute("ALTER TABLE recommendation_history ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY")

    cur.close()
    conn.close()

    print("\n--- 4. Initializing SQLAlchemy DB tables ---")
    init_db()
    print("Schema alignment complete!")

if __name__ == "__main__":
    align_all_schemas()
