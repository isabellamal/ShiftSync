from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3 as sql
app = Flask(__name__)
app.secret_key = "secret_key" # needed for session

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