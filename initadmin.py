import sqlite3
conn = sqlite3.connect('ShiftSyncDB.db')
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

cur.execute("DROP TABLE IF EXISTS AdminInfo")

cur.execute('''
CREATE TABLE IF NOT EXISTS AdminInfo(
    AdminId TEXT PRIMARY KEY NOT NULL,
    AdminPass TEXT);
''')

cur.execute("INSERT OR IGNORE INTO AdminInfo (AdminId, AdminPass) VALUES (?, ?)", ("admin", "admin"))

conn.commit()
conn.close()

