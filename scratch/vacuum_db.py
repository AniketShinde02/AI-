import sqlite3
import os

db_path = r"D:\AI\backend\nexus_core\data\nexus_core.db"
if not os.path.exists(db_path):
    print("Database does not exist")
    exit()

print(f"Original size: {os.path.getsize(db_path) / (1024*1024):.2f} MB")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Clear verification matrix to break the feedback loop and remove the 675MB string
print("Clearing verification_matrix table...")
cursor.execute("DELETE FROM verification_matrix")
conn.commit()

# Vacuum database
print("Vacuuming database...")
cursor.execute("VACUUM")
conn.commit()

conn.close()

print(f"New size: {os.path.getsize(db_path) / (1024*1024):.2f} MB")

