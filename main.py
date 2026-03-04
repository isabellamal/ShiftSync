from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3 as sql
from datetime import datetime, timedelta, date
app = Flask(__name__)
app.secret_key = "secret_key" # needed for session

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def time_choices(step_minutes=30):
    # Returns list like ["08:00", "08:30", ...]
    times = []
    for h in range(0, 24):
        for m in range(0, 60, step_minutes):
            times.append(f"{h:02d}:{m:02d}")
    return times

TIME_CHOICES = time_choices(30)

@app.route('/', methods = ['POST', 'GET'])
def login():
    msg = ""
    if request.method == 'POST':
        EmployeeId = request.form['EmployeeId'].strip()

        try:
            with sql.connect("ShiftSyncDB.db") as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM EmployeeInfo WHERE EmployeeId=?", (EmployeeId,))
                found = cur.fetchone() # returns a tuple if a row matching the query exists

        except Exception as e:
            msg = "Database error!"
            return render_template('login.html', msg=msg)
        
        if found:
            if found[2]: # if password exists
                session['EmployeeId'] = found[0]
                return redirect(url_for('existinguser'))
            else: # if password does not exist
                session['EmployeeId'] = found[0]
                return redirect(url_for('newuser'))

        else:
            msg = "Employee ID not found. Please check and try again."
    
    return render_template('login.html', msg=msg)

@app.route('/existinguser', methods=['GET', 'POST'])
def existinguser():
    if 'EmployeeId' not in session: # makes sure only logged in users can access this page 
        return redirect(url_for('login'))

    user_id = session['EmployeeId']
    msg = ""

    # user pressed the "Log in" button
    if request.method == 'POST':
        entered_pw = request.form.get('password', '').strip()

        # get saved password hash from database
        try:
            with sql.connect("ShiftSyncDB.db") as con:
                cur = con.cursor()
                cur.execute("SELECT Password FROM EmployeeInfo WHERE EmployeeId=?", (user_id,))
                row = cur.fetchone()
        except Exception:
            msg = "Database error!"
            return render_template('existinguser.html', user=user_id, msg=msg)

        # if password is missing something or wrong
        if (row is None) or (row[0] is None) or (row[0] == ""):
            msg = "No password found. Please create one."
            return redirect(url_for('newuser'))

        saved_hash = row[0]

        # check typed password against saved hash
        if check_password_hash(saved_hash, entered_pw):
            return redirect(url_for('dashboard'))
        else:
            msg = "Incorrect password."

    return render_template('existinguser.html', user=user_id,  msg=msg)

@app.route('/newuser', methods=['GET', 'POST'])
def newuser():
    if 'EmployeeId' not in session: # makes sure only logged in users can access this page 
        return redirect(url_for('login'))

    user_id = session['EmployeeId']
    msg = ""

    # user pressed the Create Password button
    if request.method == 'POST':
        pw1 = request.form.get('password', '').strip()
        pw2 = request.form.get('confirm_password', '').strip()

        # check passwords match
        if pw1 != pw2:
            msg = "Passwords do not match."
            return render_template('newuser.html', user=user_id, msg=msg)

        # don't allow an empty password
        if pw1 == "":
            msg = "Password cannot be empty."
            return render_template('newuser.html', user=user_id, msg=msg)

        # hash password so we do not store the real password in the database
        hashed_pw = generate_password_hash(pw1)

        # save hashed password into database
        try:
            with sql.connect("ShiftSyncDB.db") as con:
                cur = con.cursor()
                cur.execute("UPDATE EmployeeInfo SET Password=? WHERE EmployeeId=?", (hashed_pw, user_id))
                con.commit()
        except Exception:
            msg = "Database error!"
            return render_template('newuser.html', user=user_id, msg=msg)

        # logout so they must login with new password
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('newuser.html', user=user_id,  msg=msg)

@app.route('/logout') # for any pages that have logout button this runs when logout is pressed 
def logout():
    session.clear()
    return redirect(url_for('login'))

#dashboard 
@app.route('/dashboard')
def dashboard():
    if 'EmployeeId' not in session: 
        return redirect(url_for('login'))
    
    user_id = session['EmployeeId']
    today = date.today()

    #upcoming shifts (next 7 days)
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT ShiftId, ShiftDate, StartTime, EndTime
                FROM Shifts
                WHERE EmployeeId=? AND ShiftDate >= ?
                ORDER BY ShiftDate, StartTime
                LIMIT 5
            """, (user_id, today.isoformat()))
            upcoming_shifts = cur.fetchall()
    except Exception:
        upcoming_shifts = []
    
    #availability summary (1 row per day, latest block per day)
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT DayOfWeek, StartTime, EndTime
                FROM EmployeeAvailability
                WHERE EmployeeId=? AND IsAvailable=1
                ORDER BY
                    CASE DayOfWeek
                        WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2
                        WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4
                        WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
                        WHEN 'Sunday' THEN 7 ELSE 8
                    END, StartTime
            """, (user_id,))
            avail_rows = cur.fetchall()
    except Exception:
        avail_rows = []

    #build dict, day -> list of time blocks 
    avail_by_day = {}
    for row in avail_rows:
        avail_by_day.setdefault(row[0], []).append((row[1], row[2]))

    #swap requests submitted
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT r.RequestId, s.ShiftDate, s.StartTime, s.EndTime,
                       r.TargetEmployeeId, r.Reason, r.Status, r.CreatedAt
                FROM ShiftSwapRequests r
                JOIN Shifts s ON r.ShiftId = s.ShiftId
                WHERE r.RequesterEmployeeId=?
                ORDER BY r.CreatedAt DESC
                LIMIT 10
            """, (user_id,))
            my_swap_requests = cur.fetchall()
    except Exception:
        my_swap_requests = []

    #employee name
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("SELECT Name FROM EmployeeInfo WHERE EmployeeId=?", (user_id,))
            row = cur.fetchone()
            name = row[0] if row and row[0] else user_id
    except Exception:
        name = user_id

    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
            SELECT r.RequestId, r.RequesterEmployeeId, s.ShiftDate, s.StartTime, s.EndTime, r.Status
            FROM ShiftSwapRequests r
            JOIN Shifts s ON r.ShiftId = s.ShiftId
            WHERE r.TargetEmployeeId=? AND r.Status='pending'
        """, (user_id,))
        incoming_requests = cur.fetchall()
    except Exception:
        incoming_requests = []


    return render_template('dashboard.html',
                            user=user_id,
                            name = name,
                            upcoming_shifts=upcoming_shifts,
                            avail_by_day=avail_by_day,
                            days=DAYS,
                            my_swap_requests=my_swap_requests,
                            incoming_requests=incoming_requests)



@app.route('/availability', methods=['GET', 'POST'])
def availability():
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))

    user_id = session['EmployeeId']
    msg = ""

    # Handle form submit (add new availability)
    if request.method == 'POST':
        day = request.form.get('day', '').strip()
        start = request.form.get('start', '').strip()
        end = request.form.get('end', '').strip()

        # Basic validation
        if day not in DAYS:
            msg = "Invalid day selected."
        elif start not in TIME_CHOICES or end not in TIME_CHOICES:
            msg = "Invalid time selected."
        elif end <= start:
            msg = "End time must be after start time."
        else:
            try:
                with sql.connect("ShiftSyncDB.db") as con:
                    cur = con.cursor()
                    cur.execute("""
                        INSERT INTO EmployeeAvailability (EmployeeId, DayOfWeek, StartTime, EndTime, IsAvailable)
                        VALUES (?, ?, ?, ?, 1)
                    """, (user_id, day, start, end))
                    con.commit()
                return redirect(url_for('availability'))
            except Exception:
                msg = "Database error while saving availability."

    # Always load existing blocks
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT AvailabilityId, DayOfWeek, StartTime, EndTime
                FROM EmployeeAvailability
                WHERE EmployeeId=? AND IsAvailable=1
                ORDER BY 
                    CASE DayOfWeek
                        WHEN 'Monday' THEN 1
                        WHEN 'Tuesday' THEN 2
                        WHEN 'Wednesday' THEN 3
                        WHEN 'Thursday' THEN 4
                        WHEN 'Friday' THEN 5
                        WHEN 'Saturday' THEN 6
                        WHEN 'Sunday' THEN 7
                        ELSE 8
                    END,
                    StartTime
            """, (user_id,))
            rows = cur.fetchall()
    except Exception:
        rows = []
        msg = msg or "Database error while loading availability."

    return render_template(
        'availability.html',
        user=user_id,
        msg=msg,
        days=DAYS,
        times=TIME_CHOICES,
        availability=rows
    )


@app.route('/availability/edit/<int:availability_id>', methods=['GET', 'POST'])
def edit_availability(availability_id):
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))

    user_id = session['EmployeeId']
    msg = ""

    # Load the record and verify ownership
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT AvailabilityId, DayOfWeek, StartTime, EndTime
                FROM EmployeeAvailability
                WHERE AvailabilityId=? AND EmployeeId=?
            """, (availability_id, user_id))
            record = cur.fetchone()
    except Exception:
        record = None

    if not record:
        return redirect(url_for('availability'))

    #update on POST
    if request.method == 'POST':
        day = request.form.get('day', '').strip()
        start = request.form.get('start', '').strip()
        end = request.form.get('end', '').strip()

        if day not in DAYS:
            msg = "Invalid day selected."
        elif start not in TIME_CHOICES or end not in TIME_CHOICES:
            msg = "Invalid time selected."
        elif end <= start:
            msg = "End time must be after start time."
        else:
            try:
                with sql.connect("ShiftSyncDB.db") as con:
                    cur = con.cursor()
                    cur.execute("""
                        UPDATE EmployeeAvailability
                        SET DayOfWeek=?, StartTime=?, EndTime=?, IsAvailable=1
                        WHERE AvailabilityId=? AND EmployeeId=?
                    """, (day, start, end, availability_id, user_id))
                    con.commit()
                return redirect(url_for('availability'))
            except Exception:
                msg = "Database error while updating availability."

    return render_template(
        'availability_edit.html',
        user=user_id,
        msg=msg,
        days=DAYS,
        times=TIME_CHOICES,
        record=record
    )


@app.route('/availability/delete/<int:availability_id>', methods=['POST'])
def delete_availability(availability_id):
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))

    user_id = session['EmployeeId']

    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                DELETE FROM EmployeeAvailability
                WHERE AvailabilityId=? AND EmployeeId=?
            """, (availability_id, user_id))
            con.commit()
    except Exception:
        pass

    return redirect(url_for('availability'))

#shift swap requests routing
@app.route('/swap-request', methods=['GET', 'POST'])
def swap_request():
    """Submit a shift swap request from the dashboard"""
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))
    
    user_id = session['EmployeeId']
    shift_id = request.form.get('shift_id', '').strip()
    target_id = request.form.get('target_employee_id', '').strip() or None
    reason = request.form.get('reason', '').strip() or None

    if request.method == 'GET':
        return redirect(url_for('dashboard'))

    if not shift_id:
        return redirect(url_for('dashboard'))
    
    #verify that shift belongs to the requesting employee
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT RequestId FROM ShiftSwapRequests
                WHERE RequesterEmployeeId=? AND ShiftId=? AND Status='pending'
            """, (user_id, shift_id))
            existing = cur.fetchone()
    except Exception:
        existing = None

    if not existing:
        try:
            with sql.connect("ShiftSyncDB.db") as con:
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO ShiftSwapRequests
                        (RequesterEmployeeId, ShiftId, TargetEmployeeId, Reason, Status, CreatedAt)
                    VALUES (?, ?, ?, ?, 'pending', datetime('now'))
                """, (user_id, shift_id, target_id, reason))
                con.commit()
        except Exception:
            pass
    return redirect(url_for('dashboard'))

@app.route('/swap-request/cancel/<int:request_id>', methods=['POST'])
def cancel_swap_request(request_id):
    """Cancel a pending swap request"""
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))
    
    user_id = session['EmployeeId']
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                DELETE FROM ShiftSwapRequests
                WHERE RequestId=? AND RequesterEmployeeId=? AND Status='pending'
            """, (request_id, user_id))
            con.commit()
    except Exception:
        pass

    return redirect(url_for('dashboard'))

@app.route('/swap-request/approve/<int:request_id>', methods=['POST'])
def approve_swap_request(request_id):
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))

    approver_id = session['EmployeeId']

    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()

            # 1) Load request (must be pending + assigned to me)
            cur.execute("""
                SELECT RequesterEmployeeId, ShiftId, TargetEmployeeId, Status
                FROM ShiftSwapRequests
                WHERE RequestId=?
            """, (request_id,))
            row = cur.fetchone()

            if not row:
                return redirect(url_for('dashboard'))

            requester_id, shift_id, target_id, status = row

            # must be pending and I must be the target
            if status != 'pending' or target_id != approver_id:
                return redirect(url_for('dashboard'))

            # 2) Double-check the shift still belongs to requester
            cur.execute("""
                SELECT EmployeeId
                FROM Shifts
                WHERE ShiftId=?
            """, (shift_id,))
            shift_row = cur.fetchone()

            if not shift_row or shift_row[0] != requester_id:
                return redirect(url_for('dashboard'))

            # 3) Move the shift to the approver (target employee)
            cur.execute("""
                UPDATE Shifts
                SET EmployeeId=?
                WHERE ShiftId=?
            """, (approver_id, shift_id))

            # 4) Mark request approved
            cur.execute("""
                UPDATE ShiftSwapRequests
                SET Status='approved'
                WHERE RequestId=?
            """, (request_id,))

            con.commit()

    except Exception:
        pass

    return redirect(url_for('dashboard'))

@app.route('/swap-request/deny/<int:request_id>', methods=['POST'])
def deny_swap_request(request_id):
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))

    user_id = session['EmployeeId']
    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                UPDATE ShiftSwapRequests
                SET Status='denied'
                WHERE RequestId=? AND TargetEmployeeId=? AND Status='pending'
            """, (request_id, user_id))
            con.commit()
    except Exception:
        pass

    return redirect(url_for('dashboard'))

@app.route('/swap-requests')
def swap_requests():
    if 'EmployeeId' not in session:
        return redirect(url_for('login'))

    user_id = session['EmployeeId']

    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT r.RequestId, s.ShiftDate, s.StartTime, s.EndTime,
                       r.TargetEmployeeId, r.Status
                FROM ShiftSwapRequests r
                JOIN Shifts s ON r.ShiftId = s.ShiftId
                WHERE r.RequesterEmployeeId=?
                ORDER BY r.CreatedAt DESC
            """, (user_id,))
            requests = cur.fetchall()
    except Exception:
        requests = []

    return render_template("swap_requests.html", requests=requests)

#API calendar data for the dashboard JS
@app.route('/api/shifts')
def api_shifts():
    """Return shifts for current employee as JSON for calendar rendering"""
    if 'EmployeeId' not in session:
        return jsonify([]), 403
    user_id = session['EmployeeId']
    week_offset = int(request.args.get('week', 0))
    today = date.today()
    #find sunday of current week
    days_since_sunday = today.weekday() + 1 #weekday(): Mon=0...Sun=6
    if today.weekday() == 6:
        days_since_sunday = 0
    week_start = today - timedelta(days=days_since_sunday) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    try:
        with sql.connect("ShiftSyncDB.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT ShiftId, ShiftDate, StartTime, EndTime
                FROM Shifts
                WHERE EmployeeId=? AND ShiftDate BETWEEN ? AND ?
                ORDER BY ShiftDate, StartTime
            """, (user_id, week_start.isoformat(), week_end.isoformat()))
            rows = cur.fetchall()
    except Exception:
        rows = []
    
    shifts = []
    for row in rows:
        shifts.append({
            'shift_id': row[0],
            'date': row[1],
            'start': row[2],
            'end': row[3],
        })
    
    return jsonify(shifts)

if __name__ == "__main__":
    app.run(debug=True)