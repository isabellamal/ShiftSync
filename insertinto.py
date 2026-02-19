import sqlite3
conn = sqlite3.connect('ShiftSyncDB.db')
cur = conn.cursor()

# test employee
cur.execute(''' 
    INSERT INTO EmployeeInfo (EmployeeId, Name)
    VALUES (?, ?)
''', ("00000001", "Jane Doe")) 

conn.commit()