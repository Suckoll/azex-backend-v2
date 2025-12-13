from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='customer')
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

@app.route('/api/customers', methods=['GET'])
@jwt_required()
def get_customers():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    customers = User.query.filter_by(role='customer').all()
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
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    new_user = User(
        email=data['email'],
        password='temp123',  # Customer will reset
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

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)