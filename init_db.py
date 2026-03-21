import sqlite3
conn = sqlite3.connect('ShiftSyncDB.db')
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

cur.execute("DROP TABLE IF EXISTS ShiftSwapRequests")
cur.execute("DROP TABLE IF EXISTS Shifts")
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
cur.execute('''CREATE TABLE IF NOT EXISTS Shifts(
    ShiftId INTEGER PRIMARY KEY NOT NULL,
    EmployeeId TEXT NOT NULL,
    ShiftDate TEXT NOT NULL, 
    StartTime TEXT NOT NULL, 
    EndTime TEXT NOT NULL, 
    FOREIGN KEY (EmployeeId) REFERENCES EmployeeInfo(EmployeeId));
''')
cur.execute('''CREATE TABLE IF NOT EXISTS ShiftSwapRequests(
    RequestId INTEGER PRIMARY KEY NOT NULL,
    RequesterEmployeeId TEXT NOT NULL,
    ShiftId INTEGER NOT NULL,
    TargetEmployeeId TEXT,
    Reason TEXT,
    Status TEXT DEFAULT "pending",
    CreatedAt TEXT,
    FOREIGN KEY (RequesterEmployeeId) REFERENCES EmployeeInfo(EmployeeId),
    FOREIGN KEY (ShiftId) REFERENCES Shifts(ShiftId),
    FOREIGN KEY (TargetEmployeeId) REFERENCES EmployeeInfo(EmployeeId));
''')


conn.commit()
conn.close()