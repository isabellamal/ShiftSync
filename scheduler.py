from datetime import datetime

def is_available(employee_id, shift, db):
    shift_date = shift['date']
    shift_start = shift['start']
    shift_end = shift['end']

    day_name = datetime.strptime(shift_date, "%Y-%m-%d").strftime("%A")
    print("CHECK AVAILABILITY:", employee_id, shift_date, day_name, shift_start, shift_end)

    cur = db.cursor()
    cur.execute("""
        SELECT StartTime, EndTime
        FROM EmployeeAvailability
        WHERE EmployeeId=? AND DayOfWeek=? AND IsAvailable=1
    """, (employee_id, day_name))
    availability_rows = cur.fetchall()

    print("AVAILABILITY ROWS:", availability_rows)

    if not availability_rows:
        print("NO AVAILABILITY FOUND")
        return False

    shift_start_time = datetime.strptime(shift_start, "%H:%M").time()
    shift_end_time = datetime.strptime(shift_end, "%H:%M").time()

    for row in availability_rows:
        avail_start = datetime.strptime(row[0], "%H:%M").time()
        avail_end = datetime.strptime(row[1], "%H:%M").time()
        print("COMPARE AGAINST:", avail_start, avail_end)

        if shift_start_time >= avail_start and shift_end_time <= avail_end:
            print("AVAILABLE = TRUE")
            return True

    print("AVAILABLE = FALSE")
    return False


def has_conflict(employee_id, shift, db):
    cur = db.cursor()
    cur.execute("""
        SELECT ShiftDate, StartTime, EndTime
        FROM Shifts
        WHERE EmployeeId=? AND ShiftDate=?
    """, (employee_id, shift['date']))
    existing_shifts = cur.fetchall()

    print("EXISTING SHIFTS:", existing_shifts)

    new_start = datetime.strptime(shift['start'], "%H:%M").time()
    new_end = datetime.strptime(shift['end'], "%H:%M").time()

    for row in existing_shifts:
        existing_start = datetime.strptime(row[1], "%H:%M").time()
        existing_end = datetime.strptime(row[2], "%H:%M").time()
        print("CHECK CONFLICT AGAINST:", existing_start, existing_end)

        if new_start < existing_end and new_end > existing_start:
            print("CONFLICT = TRUE")
            return True

    print("CONFLICT = FALSE")
    return False


def can_assign(employee_id, shift, db):
    available = is_available(employee_id, shift, db)
    conflict = has_conflict(employee_id, shift, db)
    print("FINAL:", {"available": available, "conflict": conflict})
    return available and not conflict

def can_assign_swap(employee_id, shift, db):
    """For swaps: only check availability, not conflicts (the conflict is the shift being replaced)"""
    return is_available(employee_id, shift, db)
