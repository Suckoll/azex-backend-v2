from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_cors import CORS
from flask_mail import Mail, Message
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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

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

# Correct CORS configuration - placed AFTER app is defined
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type"]
    }
})

# Create upload folders
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['EMPLOYEE_PHOTO_FOLDER']):
    os.makedirs(app.config['EMPLOYEE_PHOTO_FOLDER'])

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
    photo = db.Column(db.String(200))  # filename

    @property
    def name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or 'Unnamed Employee'

class EmployeeDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    category = db.Column(db.String(100), default='Other')
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))  # technician
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    title = db.Column(db.String(200))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    description = db.Column(db.String(500))
    status = db.Column(db.String(20), default='Scheduled')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=False)
    manufacturer = db.Column(db.String(100))
    epa_number = db.Column(db.String(50))
    active_ingredients = db.Column(db.Text)
    unit = db.Column(db.String(20), default='each')
    discontinued = db.Column(db.Boolean, default=False)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    reorder_level = db.Column(db.Float, default=0.0)

    __table_args__ = (UniqueConstraint('product_id', 'branch_id', name='unique_product_branch'),)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    subtotal = db.Column(db.Float, default=0.0)
    tax_rate = db.Column(db.Float, default=0.086)
    tax_amount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Draft')
    notes = db.Column(db.Text)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    service_address = db.Column(db.String(200))
    unit = db.Column(db.String(50))
    quantity = db.Column(db.Float, default=1.0)
    unit_price = db.Column(db.Float, default=0.0)
    line_total = db.Column(db.Float, default=0.0)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), default='Check')

class LogbookReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    unit = db.Column(db.String(50))
    pest = db.Column(db.String(100))
    area = db.Column(db.String(100))
    description = db.Column(db.String(500))
    photo = db.Column(db.String(200))
    reporter = db.Column(db.String(100))
    permission = db.Column(db.String(50))
    occupied = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

    # Admin user
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', role='admin')
        admin.set_password('azex2025')
        db.session.add(admin)
        db.session.commit()

    # Branches seeding (unchanged)

    # Employees, Products, Stock seeding (as in previous versions)

@app.route('/')
def home():
    return "AZEX PestGuard Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
        return jsonify({'access_token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

# All other routes (branches, employees CRUD + photo + documents, jobs, customers, products, stock, invoices CRUD + email + payments, logbook)

# Example employee photo upload
@app.route('/api/employees/<int:emp_id>/photo', methods=['POST'])
@jwt_required()
def upload_employee_photo(emp_id):
    # ... as in previous version ...

# Serve photos
@app.route('/uploads/employees/<filename>')
def employee_photo(filename):
    return send_from_directory(app.config['EMPLOYEE_PHOTO_FOLDER'], filename)

# Invoice email (as in previous)

if __name__ == '__main__':
    app.run(debug=True)