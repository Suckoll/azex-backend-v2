from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
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
app.config['EMPLOYEE_PHOTO_FOLDER'] = 'uploads/employees'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

db = SQLAlchemy(app)
jwt = JWTManager(app)
mail = Mail(app)

# Global preflight handler - fixes ALL CORS preflight errors
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response, 200

# Headers on every response
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Folders
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['EMPLOYEE_PHOTO_FOLDER']):
    os.makedirs(app.config['EMPLOYEE_PHOTO_FOLDER'])

# MODELS
class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200))
    manager_name = db.Column(db.String(100))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default='customer')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    firstName = db.Column(db.String(100))
    lastName = db.Column(db.String(100))
    phone1 = db.Column(db.String(20))
    company = db.Column(db.String(100))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(10))
    zip = db.Column(db.String(20))
    billName = db.Column(db.String(100))
    billEmail = db.Column(db.String(120))
    billPhone = db.Column(db.String(20))
    billAddress = db.Column(db.String(200))
    billCity = db.Column(db.String(100))
    billState = db.Column(db.String(10))
    billZip = db.Column(db.String(20))
    multiUnit = db.Column(db.Boolean, default=False)
    preferred_day = db.Column(db.String(20), default='Any')
    preferred_time_window = db.Column(db.String(100), default='Anytime')
    recurrence = db.Column(db.String(20), default='None')
    last_service_date = db.Column(db.DateTime)
    next_service_date = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    photo = db.Column(db.String(200))

    @property
    def name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or 'Unnamed Employee'

# Other models (EmployeeDocument, Job, Product, Stock, Invoice, InvoiceItem, Payment, LogbookReport) unchanged

# DATABASE SEEDING (full from previous)

@app.route('/')
def home():
    return "AZEX Customer Management System Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
        return jsonify({'access_token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

# Add all other routes (branches, employees, technicians, products, customers, jobs, stock, invoices, deals, photo upload, etc.) from previous versions

if __name__ == '__main__':
    app.run(debug=True)