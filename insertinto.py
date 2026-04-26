import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect("ShiftSyncDB.db")
cur = conn.cursor()

# ---- Employees ----
employees = [
    ("00000001", "Jane Doe"),
    ("00000002", "John Smith"),
]

for emp_id, name in employees:
    cur.execute("""
        INSERT OR IGNORE INTO EmployeeInfo (EmployeeId, Name)
        VALUES (?, ?)
    """, (emp_id, name))

# ---- Shifts (must be today or in the future to show in dashboard modal) ----
today = date.today()
shift_rows = [
    # Jane has a shift tomorrow
    ("00000001", (today + timedelta(days=1)).isoformat(), "09:00", "13:00"),
    # Jane has another shift in 3 days
    ("00000001", (today + timedelta(days=3)).isoformat(), "14:00", "18:00"),
    # John has a shift tomorrow too (useful if you want TargetEmployeeId)
    ("00000002", (today + timedelta(days=1)).isoformat(), "10:00", "14:00"),
]

for emp_id, d, start, end in shift_rows:
    cur.execute("""
        INSERT INTO Shifts (EmployeeId, ShiftDate, StartTime, EndTime)
        VALUES (?, ?, ?, ?)
    """, (emp_id, d, start, end))

conn.commit()
conn.close()

print("Seeded test employees and shifts.")