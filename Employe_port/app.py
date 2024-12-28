from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import base64
from datetime import datetime
from datetime import datetime, timedelta


app = Flask(__name__)
bcrypt = Bcrypt(app)

# Database configuration
app.config['MYSQL_HOST'] = '10.70.73.231'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root123'
app.config['MYSQL_DB'] = 'global_employee_db'

mysql = MySQL(app)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        contact_number = request.form['contact_number']
        home_address = request.form['home_address']
        branch = request.form['branch']
        city = request.form['city']
        designation = request.form['designation']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        photo = request.files['photo'].read()

        conn = mysql.connection
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Employee (name, contact_number, home_address, branch, city, designation, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, contact_number, home_address, branch, city, designation, password))
        conn.commit()

        employee_id = cursor.lastrowid  # Get the newly inserted employee ID

        cursor.execute("""
            INSERT INTO EmployeePhoto (employee_id, photo)
            VALUES (%s, %s)
        """, (employee_id, photo))
        conn.commit()

        return render_template('signup_success.html', employee_id=employee_id)  # Pass employee_id to the template

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        password = request.form['password']

        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("""
            SELECT employee_id, password FROM Employee WHERE employee_id = %s
        """, (employee_id,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user[1], password):
            return redirect(url_for('profile', employee_id=user[0]))
        else:
            return jsonify({"message": "Invalid credentials"}), 401

    return render_template('login.html')

@app.route('/profile/<int:employee_id>')
def profile(employee_id):
    conn = mysql.connection
    cursor = conn.cursor()

    # Fetch employee details
    cursor.execute("""
        SELECT name, contact_number, home_address, branch, city, designation
        FROM Employee WHERE employee_id = %s
    """, (employee_id,))
    profile = cursor.fetchone()

    cursor.execute("""
        SELECT photo FROM EmployeePhoto WHERE employee_id = %s
    """, (employee_id,))
    photo = cursor.fetchone()

    photo_base64 = base64.b64encode(photo[0]).decode('utf-8') if photo else None

    return render_template('profile.html', profile=profile, photo=photo_base64, employee_id=employee_id)

@app.route('/attendance/<int:employee_id>', methods=['GET', 'POST'])
def attendance(employee_id):
    if request.method == 'POST':
        photo = request.form['photo']  # Base64 encoded photo
        latitude = request.form.get('latitude', '').strip()
        longitude = request.form.get('longitude', '').strip()

        if not latitude or not longitude:
            return jsonify({"error": "Geolocation data is required to mark attendance!"}), 400

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            return jsonify({"error": "Invalid geolocation format!"}), 400

        photo_data = base64.b64decode(photo)

        # Get current date and time
        current_date = datetime.now().date()
        current_time = datetime.now().time()

        conn = mysql.connection
        cursor = conn.cursor()

        # Insert attendance into the database (no need for attendance_count)
        cursor.execute("""
            INSERT INTO Attendance (employee_id, date, time, latitude, longitude, photo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (employee_id, current_date, current_time, latitude, longitude, photo_data))
        conn.commit()

        # Render success page with green tick
        return render_template('attendance_success.html', employee_id=employee_id)

    return render_template('attendance.html', employee_id=employee_id)

@app.route('/mark_absent', methods=['POST'])
def mark_absent():
    data = request.get_json()
    employee_id = data['employee_id']
    date = data['date']

    conn = mysql.connection
    cursor = conn.cursor()

    # Check if the user has already marked attendance for the day
    cursor.execute("""SELECT * FROM Attendance WHERE employee_id = %s AND date = %s""", (employee_id, date))
    existing_record = cursor.fetchone()

    if not existing_record:
        # Insert the attendance as "absent"
        cursor.execute("""
            INSERT INTO Attendance (employee_id, date, time, status)
            VALUES (%s, %s, %s, 'absent')
        """, (employee_id, date, datetime.now().time()))
        conn.commit()

    return jsonify({"message": "Attendance marked as absent for today"})

@app.route('/mark_present', methods=['POST'])
def mark_present():
    data = request.get_json()
    employee_id = data['employee_id']
    date = data['date']

    conn = mysql.connection
    cursor = conn.cursor()

    # Check if the user has already marked attendance for the day
    cursor.execute("""SELECT * FROM Attendance WHERE employee_id = %s AND date = %s""", (employee_id, date))
    existing_record = cursor.fetchone()

    if not existing_record:
        # Insert the attendance as "present"
        cursor.execute("""
            INSERT INTO Attendance (employee_id, date, time, status)
            VALUES (%s, %s, %s, 'present')
        """, (employee_id, date, datetime.now().time()))
        conn.commit()

    return jsonify({"message": "Attendance marked as present for today"})

@app.route('/track-attendance/<int:employee_id>')
def track_attendance(employee_id):
    conn = mysql.connection
    cursor = conn.cursor()

    # Fetch employee details
    cursor.execute("""
        SELECT name, contact_number, home_address, branch, city, designation
        FROM Employee WHERE employee_id = %s
    """, (employee_id,))
    profile = cursor.fetchone()

    if not profile:
        return "Employee not found", 404

    # Fetch all attendance records for the given employee
    cursor.execute("""
        SELECT date
        FROM Attendance
        WHERE employee_id = %s
    """, (employee_id,))
    records = cursor.fetchall()

    # Convert attendance dates to a set for quick lookup
    present_days = {record[0].strftime('%Y-%m-%d') for record in records}

    # Define fixed post office holidays
    holidays = [
        "2024-01-26",  # Republic Day
        "2024-08-15",  # Independence Day
        "2024-10-02",  # Gandhi Jayanti
    ]

    # Start and end dates for the current year
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)

    # Generate the full year calendar with statuses
    attendance = []
    for single_date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)):
        date_str = single_date.strftime('%Y-%m-%d')
        status = "absent" if single_date.weekday() >= 5 else "no_data"  # Default status
        if date_str in present_days:
            status = "present"
        elif date_str in holidays:
            status = "holiday"
        attendance.append({"date": date_str, "status": status})

    # Pass profile and attendance data to the template
    return render_template(
        'track_attendance.html',
        employee_id=employee_id,
        profile=profile,
        attendance=attendance
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
