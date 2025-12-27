"""
Migration script to add silence_mode and silence_prefer_source columns to user_configs table.
Run this script after updating the model to add columns to existing database.
"""
import os
import sqlite3

# Path to database - check multiple possible locations
SCRIPT_DIR = os.path.dirname(__file__)
POSSIBLE_PATHS = [
    os.path.join(SCRIPT_DIR, "..", "echotext.db"),
    os.path.join(SCRIPT_DIR, "..", "app.db"),
    os.path.join(SCRIPT_DIR, "..", "data", "echo_text.db"),
]

DB_PATH = None
for path in POSSIBLE_PATHS:
    if os.path.exists(path):
        DB_PATH = path
        break


def migrate():
    print(f"Connecting to database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(user_configs)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "silence_mode" not in columns:
            print("Adding silence_mode column...")
            cursor.execute("ALTER TABLE user_configs ADD COLUMN silence_mode VARCHAR(20) DEFAULT 'manual'")
        else:
            print("silence_mode column already exists.")
            
        if "silence_prefer_source" not in columns:
            print("Adding silence_prefer_source column...")
            cursor.execute("ALTER TABLE user_configs ADD COLUMN silence_prefer_source VARCHAR(20) DEFAULT 'auto'")
        else:
            print("silence_prefer_source column already exists.")
            
        if "silence_threshold_source" not in columns:
            print("Adding silence_threshold_source column...")
            cursor.execute("ALTER TABLE user_configs ADD COLUMN silence_threshold_source VARCHAR(20) DEFAULT 'default'")
        else:
            print("silence_threshold_source column already exists.")
            
        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
