from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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
    password = db.Column(db.String(200), nullable=False)
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

class Technician(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    technician_id = db.Column(db.Integer, db.ForeignKey('technician.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    title = db.Column(db.String(200))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    description = db.Column(db.String(500))

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
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', password='azex2025', role='admin')
        db.session.add(admin)
        db.session.commit()
    if not Branch.query.first():
        prescott = Branch(name='AZEX Prescott', city='Prescott', state='AZ', address='123 Main St')
        phoenix = Branch(name='AZEX Phoenix', city='Phoenix', state='AZ', address='456 Central Ave')
        vegas = Branch(name='AZEX Las Vegas', city='Las Vegas', state='NV', address='789 Strip Blvd')
        db.session.add_all([prescott, phoenix, vegas])
        db.session.commit()

@app.route('/')
def home():
    return "AZEX PestGuard Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and data.get('password') == 'azex2025':
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
        'address': b.address
    } for b in branches])

@app.route('/api/customers', methods=['GET'])
@jwt_required()
def get_customers():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
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
        'multiUnit': c.multiUnit
    } for c in customers])

@app.route('/api/customers', methods=['POST'])
@jwt_required()
def add_customer():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'error': 'Email required'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    new_user = User(
        email=data['email'],
        password='temp123',
        role='customer',
        firstName=data.get('firstName'),
        lastName=data.get('lastName'),
        phone1=data.get('phone1'),
        company=data.get('company'),
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        zip=data.get('zip'),
        billName=data.get('billName'),
        billEmail=data.get('billEmail'),
        billPhone=data.get('billPhone'),
        billAddress=data.get('billAddress'),
        billCity=data.get('billCity'),
        billState=data.get('billState'),
        billZip=data.get('billZip'),
        multiUnit=data.get('multiUnit', False)
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Customer added successfully!'})

@app.route('/api/logbook', methods=['POST'])
def logbook_report():
    property_id = request.form.get('property_id')
    if not property_id:
        return jsonify({'error': 'Missing property ID'}), 400

    photo = request.files.get('photo')
    filename = None
    if photo:
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    report = LogbookReport(
        branch_id=property_id,
        unit=request.form.get('unit'),
        pest=request.form.get('pest'),
        area=request.form.get('area'),
        description=request.form.get('description'),
        photo=filename,
        reporter=request.form.get('reporter'),
        permission=request.form.get('permission'),
        occupied=request.form.get('occupied')
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'message': 'Report received!'})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)