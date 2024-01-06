from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret'

# SQLite Database Configuration
DATABASE = 'users.db'

def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            role TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            name TEXT,
            surname TEXT,
            street TEXT,
            country TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()
def create_database():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        conn.close()
        create_table()

# Create the database and tables when the app starts
create_database()

# Static user accounts
static_accounts = [
    {'username': 'user', 'password': 'user', 'role': 'user'},
    {'username': 'admin', 'password': 'admin', 'role': 'admin'}
]

# Insert static accounts into the database
for account in static_accounts:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (account['username'], account['password'], account['role']))
    conn.commit()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for(session['role']))
        else:
            return 'Invalid login credentials'

    return render_template('login.html')

@app.route('/user')
def user():
    if 'username' in session and session['role'] == 'user':
        return render_template('user.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/check_status')
def check_status():
    if 'username' in session and session['role'] == 'user':
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM forms WHERE username = ? ORDER BY id DESC LIMIT 1', (session['username'],))
        status = cursor.fetchone()
        conn.close()

        if status and status[0] != 'pending':
            return render_template('user_status.html', username=session['username'], status=status[0])
        else:
            return "Form status is still pending. Check again later."
    else:
        return redirect(url_for('login'))

@app.route('/user_info', methods=['POST'])
def user_info():
    if 'username' in session and session['role'] == 'user':
        # Check if the user already has a pending form
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM forms WHERE username = ? AND status = "pending"', (session['username'],))
        existing_pending_form = cursor.fetchone()
        conn.close()

        if existing_pending_form:
            return "You already have a pending form. Please wait for it to be processed."
        else:
            if request.method == 'POST':
                name = request.form['name']
                surname = request.form['surname']
                street = request.form['street']
                country = request.form['country']

                # Save the form data to the database
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO forms (username, name, surname, street, country)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session['username'], name, surname, street, country))
                conn.commit()
                conn.close()

                return f'Thank you, {session["username"]}! Form submitted successfully.<br>' \
                       f'Username: {session["username"]}<br>Name: {name}<br>Surname: {surname}<br>Street: {street}<br>Country: {country}'
            else:
                return redirect(url_for('user'))
    else:
        return redirect(url_for('login'))


@app.route('/admin')
def admin():
    if 'username' in session and session['role'] == 'admin':
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM forms')
        forms = cursor.fetchall()
        conn.close()

        return render_template('admin.html', username=session['username'], forms=forms)
    else:
        return redirect(url_for('login'))

@app.route('/update_status/<int:form_id>/<string:new_status>', methods=['POST'])
def update_status(form_id, new_status):
    if 'username' in session and session['role'] == 'admin':
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('UPDATE forms SET status = ? WHERE id = ?', (new_status, form_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
