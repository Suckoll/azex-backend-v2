from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-super-secret')

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True)  # e.g., acme.onrender.com
    logo_url = db.Column(db.String(200))
    primary_color = db.Column(db.String(20), default='#1B5E20')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='admin')  # superadmin, company_admin, tech
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    firstName = db.Column(db.String(100))
    lastName = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))

with app.app_context():
    db.create_all()
    # Create super admin company and user
    if not Company.query.first():
        company = Company(name='AZEX Pest Solutions', subdomain='azex', primary_color='#1B5E20')
        db.session.add(company)
        db.session.commit()
        superadmin = User(email='admin@azex.com', password='azex2025', role='superadmin', company_id=company.id)
        db.session.add(superadmin)
        db.session.commit()

@app.route('/')
def home():
    return "AZEX PestGuard Multi-Tenant Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and data.get('password') == 'azex2025':
        token = create_access_token(identity={
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'company_id': user.company_id
        })
        company = Company.query.get(user.company_id)
        return jsonify({
            'access_token': token,
            'company': {
                'name': company.name,
                'logo_url': company.logo_url,
                'primary_color': company.primary_color
            }
        })
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/customers', methods=['GET'])
@jwt_required()
def get_customers():
    current_user = get_jwt_identity()
    customers = Customer.query.filter_by(company_id=current_user['company_id']).all()
    return jsonify([{
        'id': c.id,
        'firstName': c.firstName or '',
        'lastName': c.lastName or '',
        'email': c.email or '',
        'phone': c.phone or '',
        'address': c.address or ''
    } for c in customers])

@app.route('/api/customers', methods=['POST'])
@jwt_required()
def add_customer():
    current_user = get_jwt_identity()
    data = request.get_json()
    new_customer = Customer(
        company_id=current_user['company_id'],
        firstName=data.get('firstName'),
        lastName=data.get('lastName'),
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address')
    )
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({'message': 'Customer added successfully!'})

@app.route('/api/test')
def test():
    return jsonify({'status': 'Multi-tenant backend working!'})

if __name__ == '__main__':
    app.run(debug=True)