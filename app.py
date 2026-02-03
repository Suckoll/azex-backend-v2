from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
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
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
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

# DATABASE SEEDING
with app.app_context():
    db.create_all()

    # Admin user
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', role='admin')
        admin.set_password('azex2025')
        db.session.add(admin)
        db.session.commit()

    # Sample branches
    if not Branch.query.first():
        prescott = Branch(name='AZEX Prescott', city='Prescott', state='AZ', address='123 Main St')
        phoenix = Branch(name='AZEX Phoenix', city='Phoenix', state='AZ', address='456 Central Ave')
        vegas = Branch(name='AZEX Las Vegas', city='Las Vegas', state='NV', address='789 Strip Blvd')
        db.session.add_all([prescott, phoenix, vegas])
        db.session.commit()

    # Sample employees
    if not Employee.query.first():
        emp1 = Employee(first_name='John', last_name='Doe', role='Technician', branch_id=1, email='john@azex.com', phone='555-1234', hire_date=date(2023, 1, 15), pay_type='Hourly', hourly_rate=28.50, employment_status='Active')
        emp2 = Employee(first_name='Jane', last_name='Smith', role='Technician', branch_id=2, email='jane@azex.com', phone='555-5678', hire_date=date(2022, 6, 20), pay_type='Salary', salary=60000, employment_status='Active')
        emp3 = Employee(first_name='Mike', last_name='Johnson', role='Office Staff', branch_id=3, email='mike@azex.com', phone='555-9012', hire_date=date(2024, 3, 10), pay_type='Salary + Commission', salary=50000, commission_rate=15, employment_status='Active')
        db.session.add_all([emp1, emp2, emp3])
        db.session.commit()

    # Sample products and stock
    if not Product.query.first():
        samples = [
            Product(name='Talstar P Professional Insecticide', category='Pesticide', manufacturer='FMC', epa_number='279-3206', active_ingredients='Bifenthrin 7.9%', unit='gallon'),
            Product(name='Tempo SC Ultra', category='Pesticide', manufacturer='Bayer', epa_number='3125-503', active_ingredients='Beta-cyfluthrin 11.8%', unit='oz'),
            Product(name='Contrac Blox Rodenticide', category='Rodenticide', manufacturer='Bell Labs', epa_number='12455-79', active_ingredients='Bromadiolone 0.005%', unit='lb')
        ]
        db.session.add_all(samples)
        db.session.commit()

        branches = Branch.query.all()
        products = Product.query.all()
        for branch in branches:
            for prod in products:
                stock = Stock(product_id=prod.id, branch_id=branch.id, quantity=20.0, reorder_level=5.0)
                db.session.add(stock)
        db.session.commit()

# ROUTES
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

@app.route('/api/branches')
@jwt_required()
def get_branches():
    branches = Branch.query.all()
    return jsonify([{
        'id': b.id,
        'name': b.name,
        'city': b.city,
        'state': b.state,
        'address': b.address or ''
    } for b in branches])

@app.route('/api/technicians')
@jwt_required()
def get_technicians():
    techs = Employee.query.filter_by(role='Technician').all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'photo': f"/uploads/employees/{t.photo}" if t.photo else None
    } for t in techs])

@app.route('/api/products')
@jwt_required()
def get_products():
    products = Product.query.filter_by(discontinued=False).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category': p.category,
        'manufacturer': p.manufacturer or '',
        'epa_number': p.epa_number or '',
        'active_ingredients': p.active_ingredients or '',
        'unit': p.unit,
        'discontinued': p.discontinued
    } for p in products])

@app.route('/api/customers', methods=['GET'])
@jwt_required()
def get_customers():
    branch_id = request.args.get('branch_id')
    query = User.query.filter_by(role='customer')
    if branch_id:
        query = query.filter_by(branch_id=branch_id)
    customers = query.all()
    return jsonify([{
        'id': c.id,
        'firstName': c.firstName or '',
        'lastName': c.lastName or '',
        'email': c.email,
        'phone1': c.phone1 or '',
        'company': c.company or '',
        'address': c.address or '',
        'city': c.city or '',
        'state': c.state or '',
        'zip': c.zip or '',
        'billName': c.billName or '',
        'billEmail': c.billEmail or '',
        'billPhone': c.billPhone or '',
        'billAddress': c.billAddress or '',
        'billCity': c.billCity or '',
        'billState': c.billState or '',
        'billZip': c.billZip or '',
        'multiUnit': c.multiUnit,
        'preferredDay': c.preferred_day,
        'preferredWindow': c.preferred_time_window,
        'recurrence': c.recurrence
    } for c in customers])

# Employee photo upload and serve
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

@app.route('/uploads/employees/<filename>')
def employee_photo(filename):
    return send_from_directory(app.config['EMPLOYEE_PHOTO_FOLDER'], filename)

# Add the rest of your routes (employees CRUD, jobs, stock, invoices, etc.) from previous versions

if __name__ == '__main__':
    app.run(debug=True)