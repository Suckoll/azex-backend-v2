from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change-me-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='customer')
    firstName = db.Column(db.String(100))
    lastName = db.Column(db.String(100))
    phone = db.Column(db.String(20))
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

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='unpaid')
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(500))

class BugReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    unit = db.Column(db.String(50))
    pest = db.Column(db.String(100))
    area = db.Column(db.String(100))
    description = db.Column(db.String(500))
    photo = db.Column(db.String(200))
    reporter = db.Column(db.String(100))
    permission = db.Column(db.String(50))
    occupied = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='new')

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', password='azex2025', role='admin')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def home():
    return "AZEX PestGuard Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and data.get('password') == 'azex2025':
        token = create_access_token(identity={'id': user.id, 'email': user.email, 'role': user.role})
        return jsonify({'access_token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/customers', methods=['GET', 'POST'])
@jwt_required()
def customers():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    if request.method == 'POST':
        data = request.get_json()
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        new_user = User(
            email=data['email'],
            password='temp123',
            role='customer',
            firstName=data.get('firstName'),
            lastName=data.get('lastName'),
            phone=data.get('phone'),
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
        return jsonify({'message': 'Customer added'})
    else:
        customers = User.query.filter_by(role='customer').all()
        return jsonify([{
            'id': c.id,
            'firstName': c.firstName or '',
            'lastName': c.lastName or '',
            'email': c.email,
            'phone': c.phone or '',
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

@app.route('/api/invoices', methods=['GET', 'POST'])
@jwt_required()
def invoices():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    if request.method == 'POST':
        data = request.get_json()
        invoice = Invoice(
            customer_id=data['customer_id'],
            amount=data['amount'],
            description=data['description']
        )
        db.session.add(invoice)
        db.session.commit()
        return jsonify({'message': 'Invoice added'})
    else:
        invoices = Invoice.query.all()
        return jsonify([{
            'id': i.id,
            'customer_id': i.customer_id,
            'amount': i.amount,
            'description': i.description,
            'status': i.status,
            'date': i.date.isoformat()
        } for i in invoices])

@app.route('/api/services', methods=['GET'])
@jwt_required()
def services():
    current_user = get_jwt_identity()
    user_id = current_user['id']
    if current_user['role'] == 'admin':
        services = Service.query.all()
    else:
        services = Service.query.filter_by(customer_id=user_id).all()
    return jsonify([{
        'id': s.id,
        'date': s.date.isoformat(),
        'description': s.description
    } for s in services])

@app.route('/api/bugs', methods=['GET', 'POST'])
@jwt_required()
def bugs():
    current_user = get_jwt_identity()
    user_id = current_user['id']
    if request.method == 'POST':
        description = request.form.get('description')
        photo = request.files.get('photo')
        filename = None
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        report = BugReport(
            customer_id=user_id,
            unit=request.form.get('unit'),
            pest=request.form.get('pest'),
            area=request.form.get('area'),
            description=description,
            photo=filename,
            reporter=request.form.get('reporter'),
            permission=request.form.get('permission'),
            occupied=request.form.get('occupied')
        )
        db.session.add(report)
        db.session.commit()
        return jsonify({'message': 'Bug reported!'})
    else:
        if current_user['role'] == 'admin':
            reports = BugReport.query.all()
        else:
            reports = BugReport.query.filter_by(customer_id=user_id).all()
        return jsonify([{
            'id': r.id,
            'unit': r.unit,
            'pest': r.pest,
            'area': r.area,
            'description': r.description,
            'photo': r.photo,
            'reporter': r.reporter,
            'permission': r.permission,
            'occupied': r.occupied,
            'date': r.date.isoformat()
        } for r in reports])

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)