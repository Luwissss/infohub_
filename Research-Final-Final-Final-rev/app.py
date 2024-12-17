import pytesseract
from PIL import Image
from flask import Flask, request, render_template, redirect, url_for, session, Response, flash, jsonify, make_response, send_file
import re
import io 
import datetime
import requests
import os
import base64
import sqlite3
import csv
import cv2
from urllib.parse import quote
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.secret_key = "super secret key"
def connect():
    conn = sqlite3.connect('hub.db')
    conn.row_factory = sqlite3.Row
    return conn 

def log_to_database(query_type, details, query_value, status="Success"):
    conn = connect()
    cursor = conn.cursor() # Ensure this connects to your database
    timestamp = datetime.datetime.now()
    log_query = """
    INSERT INTO report (query_type, details, query_value, status, timestamp)
    VALUES (?, ?, ?, ?, ?)
    """
    cursor.execute(log_query, (query_type, details, query_value, status, timestamp))
    conn.commit()
    conn.close()

def is_valid_string(value):
    """Validate that the input contains only alphabets, spaces, and hyphens."""
    return bool(re.fullmatch(r"[A-Za-z0-9\s\-]+", value))

def get_image_from_db(image_name):
    connection = connect()
    cursor = connection.cursor()
    cursor.execute("SELECT image FROM student WHERE name = ?", (image_name ,))
    result = cursor.fetchone()
    connection.close()
    if result:
        image_data = result[0]
        print(type(image_data))
        output_path = "static/student/test.jpg"
        with open(output_path, 'wb') as file:
            file.write(image_data)
        return (image_data)
    return None

@app.route('/')
def home():
    return render_template("add.html")

@app.route('/set_role', methods=['POST'])
def set_role():
    role = request.form.get('role')
    if role in ['student', 'employee', 'office']:
        session['role'] = role
        return redirect(url_for('camera'))
    return "Invalid role selected", 400

@app.route('/camera')
def camera():
    role = session.get('role')
    if not role:
        return redirect(url_for('set_role'))
    return render_template("index.html", role=role)

@app.route('/scanner', methods=['POST', 'GET'])
def scanner():
    if request.method == 'POST':
        value = request.form.get("text")
        role = session.get('role')
        if not role:
            return redirect(url_for('select_role'))
        
        txtdata = value.split('data:image/jpeg;base64,')[-1].strip()
        test = Image.open(io.BytesIO(base64.b64decode(txtdata)))
        test.save('test1.png', dpi=(300, 300))
        image = cv2.imread('test1.png', 0)
        thresh = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        close = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        result = 255 - close

        scanned_text = pytesseract.image_to_string(result).strip()
        if not scanned_text:
            flash('OCR failed. Please try again.', 'danger')
            return render_template("index.html")

        cursor = connect()
        try:
            if role == 'student':
                table = 'student'
                query = f"SELECT * FROM {table} WHERE name LIKE ? or stud_num LIKE ?"
                query_value = f"('%{scanned_text}%', '%{scanned_text}%')"
                check = cursor.execute(query, ('%' + scanned_text + '%', '%' + scanned_text + '%')).fetchone()
                get_image_from_db(check['name'])
                if check:
                    log_to_database("SELECT", f"Successful search in {table}", query_value)
                    return render_template("ar.html", check=check)
                else:
                    flash('No data in Database.', 'danger')
                    return render_template("index.html", val=scanned_text)

            elif role == 'employee':
                table = 'employee'
                query = f"SELECT * FROM {table} WHERE name LIKE ?"
                query_value = f"('%{scanned_text}%')"
                check = cursor.execute(query, ('%' + scanned_text + '%',)).fetchone()
                if check:
                    log_to_database("SELECT", f"Successful search in {table}", query_value)
                    return render_template("ar3.html", check=check)
                else:
                    flash('No data in Database.', 'danger')
                    return render_template("index.html", val=scanned_text)

            elif role == 'office':
                table = 'employee'
                query = f"SELECT * FROM {table} WHERE office LIKE ?"
                query_value = f"('%{scanned_text}%')"
                check = cursor.execute(query, ('%' + scanned_text + '%',)).fetchall()
                if check:
                    log_to_database("SELECT", f"Successful search in {table}", query_value)
                    return render_template("ar5.html", check=check)
                else:
                    flash('No data in Database.', 'danger')
                    return render_template("index.html", val=scanned_text)

            else:
                flash('Wrong Role', 'danger')
                return render_template("index.html", val=scanned_text)
        finally:
            cursor.close()


@app.route('/get-user-data', methods=['POST'])
def get_user_data():
    name = request.json.get('name')
    cursor = connect()
    result = cursor.execute("SELECT * FROM employee WHERE name LIKE ?", (name,)).fetchone()
    cursor.close()
    if result:
        return jsonify({'name': result[1], 'position': result[2], 'office': result[3], 'sched': result[4]})
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    response = make_response(render_template('dashboard.html', username=session['user']))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        
        username = request.form.get('username')
        password = request.form.get('password')

        conn = connect()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        # Example of a simple username/password check
        if user and user['password'] == password:
            session['user'] = username  # Set session
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password or not confirm_password:
            flash('Please fill out all fields')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))

        try:
            conn = connect()
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, password))
            conn.commit()
            conn.close()
            flash('Registration successful, please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists')
            return redirect(url_for('register'))

    response = make_response(render_template('register.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.clear  # Remove user from session
    flash('You have been logged out.', 'info')
    response = make_response(redirect(url_for('login')))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.delete_cookie('session')
    return response

@app.route('/student', methods=['GET' , 'POST'])
def student():
    if request.method == 'POST':
        if 'file' in request.files and request.files['file']:
                file = request.files['file']
                if file.filename.endswith('.csv'):
                    file_stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                    reader = csv.DictReader(file_stream)
                    
                    # Validate CSV header
                    required_fields = {'name', 'section', 'course', 'year_graduated', 'awards'}
                    if not required_fields.issubset(reader.fieldnames):
                        flash("Invalid CSV format. Missing required fields.", "danger")
                        return redirect(url_for('student'))
                    
                    conn = connect()
                    for row in reader:
                        # Validate each row
                        if not is_valid_string(row['name']) or not is_valid_string(row['section']) or not is_valid_string(row['course']):
                            flash("Invalid characters in CSV file. Only alphabets, spaces, and hyphens are allowed.", "error")
                            return redirect(url_for('student'))
                        if not row['year_graduated'].isdigit():
                            flash("Year graduated must be a number in CSV file.", "error")
                            return redirect(url_for('student'))
                        
                        # Insert into database
                        conn.execute('''
                            INSERT INTO student (name, section, course, year_graduated, awards)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (row['name'], row['section'], row['course'], row['year_graduated'], row['awards']))
                    conn.commit()
                    conn.close()
                    flash("CSV file uploaded successfully!", "success")
                else:
                    flash("Invalid file type. Please upload a CSV file.", "danger")
        else:
            try:
                # Retrieve form data
                name = request.form['name']
                section = request.form['section']
                course = request.form['course']
                year_graduated = request.form['year_graduated']
                awards = request.form['awards']
                stud_num = request.form['stud_num']
                image = request.files['image']
                img = image.read()
                
                # Ensure all fields are present
                if name and section and course and year_graduated and awards and stud_num and img:
                    conn = connect()
                    conn.execute('''
                        INSERT INTO student (name, section, course, year_graduated, awards, stud_num, image)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (name, section, course, year_graduated, awards, stud_num, img))
                    conn.commit()
                    conn.close()
                    
                    # Flash a success message
                    flash("Data added successfully", "success")
                else:
                    # Flash an error message if any field is missing
                    flash("Please fill out all fields", "danger")
            except Exception as e:
                # Handle unexpected errors
                flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('student'))
    response = make_response(render_template('student.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/studenttbl', methods=['GET' , 'POST'])
def studenttbl():
    conn = connect()
    students = conn.execute('SELECT * FROM student').fetchall()
    conn.close()
    response = make_response(render_template('studenttbl.html', students=students))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/employee', methods=['GET' , 'POST'])
def employee():
    if request.method == 'POST':
        if 'file' in request.files and request.files['file']:
                file = request.files['file']
                if file.filename.endswith('.csv'):
                    file_stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                    reader = csv.DictReader(file_stream)
                    
                    # Validate CSV header
                    required_fields = {'name', 'position', 'office', 'sched'}
                    if not required_fields.issubset(reader.fieldnames):
                        flash("Invalid CSV format. Missing required fields.", "error")
                        return redirect(url_for('student'))
                    
                    conn = connect()
                    for row in reader:
                        # Validate each row
                        if not is_valid_string(row['name']) or not is_valid_string(row['section']) or not is_valid_string(row['course']):
                            flash("Invalid characters in CSV file. Only alphabets, spaces, and hyphens are allowed.", "error")
                            return redirect(url_for('student'))
                        if not row['year_graduated'].isdigit():
                            flash("Year graduated must be a number in CSV file.", "error")
                            return redirect(url_for('student'))
                        
                        # Insert into database
                        conn.execute('''
                            INSERT INTO student (name, section, course, year_graduated, awards)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (row['name'], row['section'], row['course'], row['year_graduated'], row['awards']))
                    conn.commit()
                    conn.close()
                    flash("CSV file uploaded successfully!", "success")
                else:
                    flash("Invalid file type. Please upload a CSV file.", "error")
        else:
            name = request.form['name']
            position = request.form['position']
            office = request.form['office']
            sched = request.form['sched']
            
            conn = connect()
            conn.execute('''
                INSERT INTO student (name, position, office, sched)
                VALUES (?, ?, ?, ?)
            ''', (name, position, office, sched))
            conn.commit()
            conn.close()
            return redirect(url_for('employee'))
    response = make_response(render_template('employee.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/employeetbl', methods=['GET' , 'POST'])
def employeetbl():
    conn = connect()
    employee = conn.execute('SELECT * FROM employee').fetchall()
    conn.close()
    response = make_response(render_template('employeetbl.html', employee=employee))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/reporttbl', methods=['GET' , 'POST'])
def reporttbl():
    conn = connect()
    report = conn.execute('SELECT * FROM report').fetchall()
    conn.close()
    response = make_response(render_template('reporttbl.html', report=report))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/student-template')
def student_template():
    # Replace 'template.csv' with the path to your CSV template file
    return send_file('static/template-student.csv',
                     as_attachment=True,
                     mimetype='text/csv',
                     download_name='template.csv')

@app.route('/employee-template')
def employee_template():
    # Replace 'template.csv' with the path to your CSV template file
    return send_file('static/template-employee.csv',
                     as_attachment=True,
                     mimetype='text/csv',
                     download_name='template.csv')



UPLOAD_FOLDER = 'C:/Users/kate santillan/Downloads/Research-Final-Final-Final-rev/IMAGES_CCA'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/images', methods=['GET', 'POST'])
def images():
    if request.method == 'POST':
        if 'files' not in request.files:
            return jsonify({'error': 'No files part in the request'}), 400

        files = request.files.getlist('files')
        saved_files = []

        # Ensure the upload folder exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        for file in files:
            if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                saved_files.append(filename)

        if not saved_files:
            return jsonify({'error': 'No valid image files were uploaded'}), 400

        # Pass data to the template
        return render_template(
            "images.html",
            message=f'{len(saved_files)} image(s) uploaded successfully',
            files=saved_files
        )

    # GET request handler
    return render_template("images.html", message="Upload your images", files=[])




if __name__ == '__main__':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    app.run(host='0.0.0.0', port=8000, debug=True, ssl_context=("cert.pem", "key.pem"))
