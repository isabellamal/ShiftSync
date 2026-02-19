from flask import Flask, render_template, request, session, redirect, url_for
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

@app.route('/existinguser')
def existinguser():
    if 'EmployeeId' not in session: # makes sure only logged in users can access this page 
        return redirect(url_for('login'))

    user_id = session['EmployeeId']

    # additional code goes here 

    return render_template('existing_user.html', user=user_id)

@app.route('/newuser')
def newuser():
    if 'EmployeeId' not in session: 
        return redirect(url_for('login'))

    user_id = session['EmployeeId']

    # additional code goes here 

    return render_template('newuser.html', user=user_id)

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