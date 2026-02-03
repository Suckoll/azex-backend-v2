from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_cors import CORS CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type"]
    }
})
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy.orm import joinedload
from sqlalchemy import UniqueConstraint

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EMPLOYEE_PHOTO_FOLDER'] = 'uploads/employees'  # New subfolder
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# Create folders
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['EMPLOYEE_PHOTO_FOLDER']):
    os.makedirs(app.config['EMPLOYEE_PHOTO_FOLDER'])

# ... all models unchanged except Employee ...

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(10))
    zip = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    hire_date = db.Column(db.Date)
    pay_type = db.Column(db.String(30), default='Hourly')
    hourly_rate = db.Column(db.Float)
    salary = db.Column(db.Float)
    commission_rate = db.Column(db.Float)
    role = db.Column(db.String(50), default='Technician')
    employment_status = db.Column(db.String(20), default='Active')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    photo = db.Column(db.String(200))  # New: filename of profile photo

    @property
    def name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or 'Unnamed Employee'

# EmployeeDocument unchanged (or rename if preferred)

# In get_employees route, add photo url
@app.route('/api/employees')
@jwt_required()
def get_employees():
    emps = Employee.query.all()
    return jsonify([{
        'id': e.id,
        'name': e.name,
        'firstName': e.first_name or '',
        'lastName': e.last_name or '',
        'email': e.email or '',
        'phone': e.phone or '',
        'role': e.role,
        'payType': e.pay_type,
        'hourlyRate': e.hourly_rate,
        'salary': e.salary,
        'commissionRate': e.commission_rate,
        'photo': f"/uploads/employees/{e.photo}" if e.photo else None,  # URL for frontend
        # ... other fields ...
        'branch_id': e.branch_id
    } for e in emps])

# New photo upload endpoint
@app.route('/api/employees/<int:emp_id>/photo', methods=['POST'])
@jwt_required()
def upload_employee_photo(emp_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    employee = Employee.query.get_or_404(emp_id)

    if 'photo' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        filename = secure_filename(f"emp_{emp_id}_{file.filename}")
        file_path = os.path.join(app.config['EMPLOYEE_PHOTO_FOLDER'], filename)
        file.save(file_path)
        employee.photo = filename
        db.session.commit()
        return jsonify({'message': 'Photo uploaded', 'photo_url': f"/uploads/employees/{filename}"})
    return jsonify({'error': 'Invalid file type'}), 400

# Serve employee photos
@app.route('/uploads/employees/<filename>')
def employee_photo(filename):
    return send_from_directory(app.config['EMPLOYEE_PHOTO_FOLDER'], filename)

# ... rest of file unchanged ...