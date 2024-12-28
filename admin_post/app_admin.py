from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import base64

app = Flask(__name__)

# Database configuration
app.config['MYSQL_HOST'] = '10.70.73.231'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root123'
app.config['MYSQL_DB'] = 'global_employee_db'

mysql = MySQL(app)

# Secret key for session management
app.secret_key = 'your_secret_key'

# Admin login route
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the admin exists in the database
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Admin WHERE username = %s", (username,))
        admin = cursor.fetchone()

        if admin and admin[2] == password:  # admin[2] is the plain text password
            session['admin_id'] = admin[0]  # Store the admin ID in the session
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('admin_login.html')

# Admin dashboard route
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = mysql.connection
    cursor = conn.cursor()

    # Fetch all employees and their details
    cursor.execute("""
        SELECT employee_id, name, contact_number, home_address, branch, city, designation
        FROM Employee
    """)
    employees = cursor.fetchall()

    # Fetch employee photos and convert them to base64
    employee_photos = {}
    for employee in employees:
        cursor.execute("""
            SELECT photo FROM EmployeePhoto WHERE employee_id = %s
        """, (employee[0],))
        photo = cursor.fetchone()
        if photo:
            # Convert image data to base64
            photo_base64 = base64.b64encode(photo[0]).decode('utf-8')
            employee_photos[employee[0]] = photo_base64

    # Fetch attendance for all employees
    attendance_data = {}
    for employee in employees:
        cursor.execute("""
            SELECT date, time, latitude, longitude
            FROM Attendance WHERE employee_id = %s
        """, (employee[0],))
        attendance_data[employee[0]] = cursor.fetchall()

    # Calculate the attendance count for each employee
    attendance_count = {}
    for employee in employees:
        cursor.execute("""
            SELECT COUNT(*) FROM Attendance WHERE employee_id = %s
        """, (employee[0],))
        count = cursor.fetchone()[0]  # Get the count of attendance records
        attendance_count[employee[0]] = count

    return render_template('admin_dashboard.html', employees=employees, attendance_data=attendance_data, employee_photos=employee_photos, attendance_count=attendance_count)

# Logout route
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)


