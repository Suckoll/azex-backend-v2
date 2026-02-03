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

# Mail
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

# MODELS (full from previous)

# SEEDING (full from previous)

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

# Add the rest of your routes (employees CRUD, jobs, stock, invoices, etc.) from previous full versions

if __name__ == '__main__':
    app.run(debug=True)