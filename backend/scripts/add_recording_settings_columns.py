
import os
import sqlite3

DB_PATH = "echotext.db"

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
        
        if "audio_buffer_duration" not in columns:
            print("Adding audio_buffer_duration column...")
            cursor.execute("ALTER TABLE user_configs ADD COLUMN audio_buffer_duration INTEGER DEFAULT 4")
        else:
            print("audio_buffer_duration column already exists.")
            
        if "silence_threshold" not in columns:
            print("Adding silence_threshold column...")
            cursor.execute("ALTER TABLE user_configs ADD COLUMN silence_threshold INTEGER DEFAULT 30")
        else:
            print("silence_threshold column already exists.")
            
        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
