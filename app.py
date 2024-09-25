from flask import Flask, request, jsonify, abort, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

app = Flask(__name__)

# Configure SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# Student Model
class Student(db.Model):
    REGNO = db.Column(db.String(10), primary_key=True)
    StudentName = db.Column(db.String(100), nullable=False)
    Gender = db.Column(db.String(10), nullable=False)

    def to_dict(self):
        return {
            'REGNO': self.REGNO,
            'StudentName': self.StudentName,
            'Gender': self.Gender
        }

# Attendance Model
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_regno = db.Column(db.String(10), db.ForeignKey('student.REGNO'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)

    def to_dict(self):
        return {
            'student_regno': self.student_regno,
            'date': self.date,
            'status': self.status
        }

# Create the database and tables
with app.app_context():
    db.create_all()

# Home Page
@app.route('/')
def home():
    students = Student.query.all()
    return render_template('home.html', students=students)

# Add Students
@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.form
    if not data or not all(key in data for key in ("REGNO", "StudentName", "Gender")):
        abort(400, 'Invalid input')

    # Check for duplicate REGNO
    if Student.query.filter_by(REGNO=data['REGNO']).first():
        abort(400, 'Student with this REGNO already exists')

    new_student = Student(REGNO=data['REGNO'], StudentName=data['StudentName'], Gender=data['Gender'])
    db.session.add(new_student)
    db.session.commit()
    return redirect('/')

# Roll Call Page
ATTENDANCE_FOLDER = 'attendance_records'

# Create the folder if it doesn't exist
if not os.path.exists(ATTENDANCE_FOLDER):
    os.makedirs(ATTENDANCE_FOLDER)

@app.route('/rollcall', methods=['GET', 'POST'])
def rollcall():
    students = Student.query.all()
    if request.method == 'POST':
        # Get the submitted date and parse it
        attendance_date_str = request.form['date']
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()

        # Get attendance data (JSON) from the form
        attendance_data = json.loads(request.form['attendance'])

        # Debug: Print attendance data to check the submission
        print("Attendance Data Received:", attendance_data)

        # Save attendance to the database
        for regno, status in attendance_data.items():
            attendance_record = Attendance(student_regno=regno, date=attendance_date, status=status)
            db.session.add(attendance_record)
        db.session.commit()

        return redirect('/check')

    return render_template('rollcall.html', students=students)

# Check Attendance Page
@app.route('/check', methods=['GET'])
def check():
    status_filter = request.args.get('status', None)
    
    # Join Attendance and Student models to get student names along with attendance records
    if status_filter == 'present':
        attendance_records = db.session.query(Attendance, Student).join(Student).filter(Attendance.status == 'Present').all()
    elif status_filter == 'absent':
        attendance_records = db.session.query(Attendance, Student).join(Student).filter(Attendance.status == 'Absent').all()
    else:
        attendance_records = db.session.query(Attendance, Student).join(Student).all()

    # Debug: Print attendance records to check retrieval
    print("Retrieved Attendance Records:", attendance_records)

    return render_template('check.html', attendance_records=attendance_records)

# Delete Student
@app.route('/delete_student/<string:regno>', methods=['POST'])
def delete_student(regno):
    student = Student.query.filter_by(REGNO=regno).first()
    if student is None:
        abort(404, 'Student not found')

    db.session.delete(student)
    db.session.commit()
    return redirect('/')

# List Attendance Files
@app.route('/files')
def list_files():
    files = os.listdir(ATTENDANCE_FOLDER)  # List all files in the folder
    return render_template('file_list.html', files=files)

# View Attendance File
@app.route('/view_file/<filename>')
def view_file(filename):
    filepath = os.path.join(ATTENDANCE_FOLDER, filename)
    
    if not os.path.exists(filepath):
        abort(404, description="File not found")

    records = []
    with open(filepath, 'r') as file:
        lines = file.readlines()
        if not lines or len(lines) < 2:  # No data beyond header
            return render_template('view_file.html', filename=filename, date='N/A', records=[], error="The file is empty or contains no records.")
        
        # Skip the first two lines (title and separator)
        for line in lines[2:]:
            # Extract data from each line
            parts = line.strip().split(' - ')
            if len(parts) == 2:
                student_info = parts[0].split('(')
                name = student_info[0].split(': ')[1].strip()
                regno = student_info[1].replace(')', '').strip()
                status = parts[1].strip()
                record = {
                    'StudentName': name,
                    'REGNO': regno,
                    'Status': status
                }
                records.append(record)

    date_str = filename.split('_')[0]  # Get the date from the filename

    return render_template('view_file.html', filename=filename, date=date_str, records=records)

if __name__ == '__main__':
    app.run(debug=True)
