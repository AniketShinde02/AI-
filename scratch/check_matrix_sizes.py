import sqlite3
db_path = r"D:\AI\backend\nexus_core\data\nexus_core.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT feature, LENGTH(result), status FROM verification_matrix ORDER BY LENGTH(result) DESC")
for row in cursor.fetchall():
    print(f"Feature: {row[0]:30} | Length: {row[1]:12} | Status: {row[2]}")
conn.close()

