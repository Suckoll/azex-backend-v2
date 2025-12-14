from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-super-secret-key')

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# Multi-Tenant Models
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True)  # e.g., acme for acme.yourdomain.com
    logo_url = db.Column(db.String(200))
    primary_color = db.Column(db.String(20), default='#1B5E20')
    subscription_active = db.Column(db.Boolean, default=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='admin')  # superadmin, company_admin, tech
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    name = db.Column(db.String(100))

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    firstName = db.Column(db.String(100))
    lastName = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
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
    # Create super admin company and user
    if not Company.query.first():
        azex_company = Company(name='AZEX Pest Solutions', subdomain='azex', primary_color='#1B5E20')
        db.session.add(azex_company)
        db.session.commit()
        superadmin = User(
            email='admin@azex.com',
            password='azex2025',
            role='superadmin',
            company_id=azex_company.id,
            name='AZEX Admin'
        )
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
        company = Company.query.get(user.company_id)
        token = create_access_token(identity={
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'company_id': user.company_id
        })
        return jsonify({
            'access_token': token,
            'company': {
                'name': company.name,
                'logo_url': company.logo_url,
                'primary_color': company.primary_color
            }
        })
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/companies', methods=['GET', 'POST'])
@jwt_required()
def companies():
    current_user = get_jwt_identity()
    if current_user['role'] != 'superadmin':
        return jsonify({'error': 'Superadmin only'}), 403
    if request.method == 'POST':
        data = request.get_json()
        new_company = Company(
            name=data['name'],
            subdomain=data['subdomain'],
            logo_url=data.get('logo_url'),
            primary_color=data.get('primary_color', '#1B5E20')
        )
        db.session.add(new_company)
        db.session.commit()
        # Create company admin
        admin_user = User(
            email=data['admin_email'],
            password='temp123',  # They reset later
            role='company_admin',
            company_id=new_company.id,
            name=data.get('admin_name')
        )
        db.session.add(admin_user)
        db.session.commit()
        return jsonify({'message': 'Company created', 'company_id': new_company.id})
    else:
        companies = Company.query.all()
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'subdomain': c.subdomain,
            'logo_url': c.logo_url,
            'primary_color': c.primary_color,
            'subscription_active': c.subscription_active
        } for c in companies])

@app.route('/api/customers', methods=['GET', 'POST'])
@jwt_required()
def customers():
    current_user = get_jwt_identity()
    company_id = current_user['company_id']
    if current_user['role'] not in ['admin', 'company_admin', 'superadmin']:
        return jsonify({'error': 'Unauthorized'}), 403
    if request.method == 'POST':
        data = request.get_json()
        new_customer = Customer(
            company_id=company_id,
            firstName=data.get('firstName'),
            lastName=data.get('lastName'),
            email=data.get('email'),
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
        db.session.add(new_customer)
        db.session.commit()
        return jsonify({'message': 'Customer added'})
    else:
        customers = Customer.query.filter_by(company_id=company_id).all()
        return jsonify([{
            'id': c.id,
            'firstName': c.firstName or '',
            'lastName': c.lastName or '',
            'email': c.email or '',
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

@app.route('/api/test')
def test():
    return jsonify({'status': 'Multi-tenant backend working!'})

if __name__ == '__main__':
    app.run(debug=True)