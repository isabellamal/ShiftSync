from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3 as sql
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

@app.route('/dashboard')
def dashboard():
    if 'EmployeeId' not in session: 
        return redirect(url_for('login'))
    
    user_id = session['EmployeeId']

    # additional code goes here 

    return render_template('dashboard.html', user=user_id)

@app.route('/logout') # for any pages that have logout button this runs when logout is pressed 
def logout():
    session.clear()
    return redirect(url_for('login'))

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
