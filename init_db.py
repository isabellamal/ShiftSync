import sqlite3
conn = sqlite3.connect('ShiftSyncDB.db')
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

cur.execute("DROP TABLE IF EXISTS EmployeeAvailability")
cur.execute("DROP TABLE IF EXISTS EmployeeInfo")

cur.execute('''CREATE TABLE IF NOT EXISTS EmployeeInfo(
    EmployeeId TEXT PRIMARY KEY NOT NULL,
    Name TEXT, 
    Password TEXT);
''')

cur.execute('''CREATE TABLE IF NOT EXISTS EmployeeAvailability(
    AvailabilityId INTEGER PRIMARY KEY NOT NULL,
    EmployeeId TEXT NOT NULL,
    DayOfWeek TEXT, 
    StartTime TEXT, 
    EndTime TEXT, 
    IsAvailable INTEGER,
    FOREIGN KEY (EmployeeId) REFERENCES EmployeeInfo(EmployeeId));
''')

conn.commit()
conn.close()