import base64

from flask import Flask, render_template, request, redirect, url_for, session, Response
import sqlite3
import os


app = Flask(__name__)
app.secret_key = 'secret'

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
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            street TEXT NOT NULL,
            country TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            pdf TEXT,
            potrdilo TEXT
        )
    ''')

    conn.commit()
    conn.close()

def create_database():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        conn.close()
        create_table()

def insert_static_accounts():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    for account in static_accounts:
        cursor.execute('SELECT id FROM users WHERE username = ?', (account['username'],))
        existing_user = cursor.fetchone()

        if not existing_user:
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (account['username'], account['password'], account['role']))
            conn.commit()

    conn.close()

# Static user accounts
static_accounts = [
    {'username': 'alen', 'password': 'alen', 'role': 'user'},
    {'username': 'beni', 'password': 'beni', 'role': 'user'},
    {'username': 'admin', 'password': 'admin', 'role': 'admin'}
]

create_database()
insert_static_accounts()


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
        cursor.execute('SELECT status, potrdilo FROM forms WHERE username = ? ORDER BY id DESC LIMIT 1', (session['username'],))
        data = cursor.fetchone()
        conn.close()

        if data and data[0] != 'pending':
            return render_template('user_status.html', username=session['username'], status=data[0], potrdilo=data[1])
        else:
            return render_template('error_template.html',
                                   error_message="Vaša vloga je še v obdelavi, prosim počakajte!")
    else:
        return redirect(url_for('login'))

@app.route('/user_info', methods=['POST'])
def user_info():
    if 'username' in session and session['role'] == 'user':
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM forms WHERE username = ? AND status = "pending"', (session['username'],))
        existing_pending_form = cursor.fetchone()
        conn.close()

        if existing_pending_form:
            return render_template('error_template.html', error_message="Vaša vloga še ni obdelana, prosim počakajte!")
        else:
            if request.method == 'POST':
                name = request.form['name']
                surname = request.form['surname']
                street = request.form['street']
                country = request.form['country']

                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO forms (username, name, surname, street, country)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session['username'], name, surname, street, country))
                conn.commit()
                conn.close()

                return render_template('success_template.html', username=session['username'], name=name,
                                       surname=surname, street=street, country=country)
                #
                # return f'Thank you, {session["username"]}! Form submitted successfully.<br>' \
                #        f'Username: {session["username"]}<br>Name: {name}<br>Surname: {surname}<br>Street: {street}<br>Country: {country}'
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


@app.route('/view_pdf/<string:username>')
def view_pdf(username):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT pdf FROM forms WHERE username = ? AND status = "accepted"', (username,))
    pdf_data = cursor.fetchone()
    conn.close()

    if pdf_data:
        pdf_binary = base64.b64decode(pdf_data[0])

        response = Response(pdf_binary, content_type='application/pdf')
        response.headers["Content-Disposition"] = f"attachment; filename={username}_form.pdf"
        return response
    else:
        return "PDF not found"


# @app.route('/update_status/<int:form_id>/<string:new_status>', methods=['POST'])
# def update_status(form_id, new_status):
#     if 'username' in session and session['role'] == 'admin':
#         conn = sqlite3.connect(DATABASE)
#         cursor = conn.cursor()
#         cursor.execute('UPDATE forms SET status = ? WHERE id = ?', (new_status, form_id))
#         conn.commit()
#         conn.close()
#         return redirect(url_for('admin'))
#     else:
#         return redirect(url_for('login'))

@app.route('/update_status/<string:username>/<string:new_status>', methods=['POST'])
def update_status(username, new_status):
    if 'username' in session and session['role'] == 'admin':
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('UPDATE forms SET status = ? WHERE username = ?', (new_status, username))
        conn.commit()
        conn.close()

        return redirect(url_for('admin'))
    else:
        return redirect(url_for('login'))


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'username' in session and session['role'] == 'user':
        try:
            new_pdf = request.files['new_pdf']
            new_pdf_data = new_pdf.read()

            new_pdf_base64 = base64.b64encode(new_pdf_data).decode('utf-8')

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('UPDATE forms SET pdf = ? WHERE username = ?', (new_pdf_base64, session['username']))
            conn.commit()
            conn.close()

            return redirect(url_for('user'))
        except Exception as e:
            return f"Error handling PDF: {str(e)}"
    else:
        return redirect(url_for('login'))


@app.route('/download_potrdilo', methods=['GET'])
def download_potrdilo():
    if 'username' in session and session['role'] == 'user':
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('SELECT potrdilo FROM forms WHERE username = ?', (session['username'],))
            potrdilo_data = cursor.fetchone()
            conn.close()

            if potrdilo_data and potrdilo_data[0] is not None:
                potrdilo_binary = base64.b64decode(potrdilo_data[0])

                response = Response(potrdilo_binary, content_type='application/pdf')
                response.headers["Content-Disposition"] = f"attachment; filename={session['username']}_potrdilo.pdf"
                return response
            else:
                return "Potrdilo not found for the user or is empty."
        except Exception as e:
            return f"Error handling Potrdilo: {str(e)}"
    else:
        return "Unauthorized access."

@app.route('/upload_pdf_admin/<string:username>', methods=['POST'])
def upload_pdf_admin(username):
    if 'username' in session and session['role'] == 'admin':
        try:
            new_pdf = request.files['new_pdf']
            new_pdf_data = new_pdf.read()

            new_pdf_base64 = base64.b64encode(new_pdf_data).decode('utf-8')

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('UPDATE forms SET potrdilo = ? WHERE username = ?', (new_pdf_base64, username))
            conn.commit()
            conn.close()

            return redirect(url_for('admin'))
        except Exception as e:
            return f"Error handling PDF: {str(e)}"
    else:
        return redirect(url_for('login'))


@app.route('/download_pdf_admin/<string:username>', methods=['GET'])
def download_pdf_admin(username):
    if 'username' in session and session['role'] == 'admin':
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('SELECT potrdilo FROM forms WHERE username = ?', (username,))
            potrdilo_data = cursor.fetchone()
            conn.close()

            if potrdilo_data and potrdilo_data[0] is not None:
                potrdilo_binary = base64.b64decode(potrdilo_data[0])

                response = Response(potrdilo_binary, content_type='application/pdf')
                response.headers["Content-Disposition"] = f"attachment; filename={session['username']}_potrdilo.pdf"
                return response

        except Exception as e:
            return f"Error downloading PDF: {str(e)}"
    else:
        return redirect(url_for('admin'))

@app.route('/izjava_piskotki')
def izjava_piskotki():
    return render_template('izjava_piskotki.html')

@app.route('/izjava_zasebnosti')
def izjava_zasebnosti():
    return render_template('izjava_zasebnosti.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
