import sqlite3
import os

db_path = r"D:\AI\backend\nexus_core\data\nexus_core.db"
if not os.path.exists(db_path):
    print("Database does not exist")
    exit()

print(f"Database size: {os.path.getsize(db_path) / (1024*1024):.2f} MB")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Table '{table}': {count} rows")
        
        # If the table has rows, let's see average length of columns
        if count > 0:
            cursor.execute(f"SELECT * FROM {table} LIMIT 1")
            cols = [desc[0] for desc in cursor.description]
            cursor.execute(f"SELECT {', '.join([f'AVG(LENGTH(CAST({c} AS TEXT)))' for c in cols])} FROM {table}")
            lengths = cursor.fetchone()
            print("  Average lengths:")
            for col, length in zip(cols, lengths):
                val = length if length is not None else 0
                print(f"    {col}: {val:.1f} chars")
    except Exception as e:
        print(f"Error checking '{table}': {e}")

conn.close()

