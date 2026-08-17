import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CTS Hackathon"))
from db import get_db_connection

def fix_users_primary_key():
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    print("1. Dropping existing foreign key constraints on dependent tables...")
    fk_drops = [
        ("comparison_history", "comparison_history_ibfk_1"),
        ("documents", "documents_ibfk_1"),
        ("favorites", "favorites_ibfk_1"),
        ("feedback", "feedback_ibfk_1"),
        ("recommendation_history", "recommendation_history_ibfk_1"),
        ("recommendations", "recommendations_ibfk_1"),
        ("search_history", "search_history_ibfk_1"),
        ("user_preferences", "user_preferences_ibfk_1"),
    ]

    for table, fk_name in fk_drops:
        try:
            cur.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{fk_name}`")
            print(f"Dropped FK {fk_name} on {table}")
        except Exception as e:
            print(f"Notice dropping FK on {table}: {e}")

    print("\n2. Updating users table primary key to `id INT AUTO_INCREMENT PRIMARY KEY`...")
    try:
        cur.execute("UPDATE users SET id = user_id WHERE id IS NULL OR id = 0")
        cur.execute("ALTER TABLE users DROP INDEX idx_users_id")
    except Exception as e:
        print("Notice on idx_users_id:", e)

    # In MySQL, altering AUTO_INCREMENT column and PRIMARY KEY must happen in a single ALTER TABLE statement
    try:
        cur.execute("ALTER TABLE users MODIFY user_id INT NOT NULL, DROP PRIMARY KEY, MODIFY id INT AUTO_INCREMENT PRIMARY KEY")
        print("Successfully migrated PRIMARY KEY to `id INT AUTO_INCREMENT`.")
    except Exception as e:
        print("Error on single ALTER TABLE:", e)

    print("\n3. Re-creating foreign key constraints pointing to users(id)...")
    fk_recreates = [
        ("user_preferences", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
        ("favorites", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
        ("documents", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
        ("feedback", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
        ("recommendations", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
        ("search_history", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
        ("comparison_history", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
        ("recommendation_history", "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE"),
    ]

    for table, fk_clause in fk_recreates:
        try:
            cur.execute(f"ALTER TABLE `{table}` ADD {fk_clause}")
            print(f"Added FK on {table}")
        except Exception as e:
            print(f"Notice recreating FK on {table}: {e}")

    cur.execute("DESCRIBE users")
    print("\nFinal users table structure:")
    for r in cur.fetchall():
        print(" ", r)

    cur.close()
    conn.close()
    print("\nUsers table primary key migration completed successfully!")

if __name__ == "__main__":
    fix_users_primary_key()
