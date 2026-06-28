import sqlite3
conn = sqlite3.connect(r'C:\Users\JADON''S\AppData\Local\hermes\state.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(messages)')
print("Messages columns:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

cursor.execute('PRAGMA table_info(sessions)')
print("\nSessions columns:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")
conn.close()