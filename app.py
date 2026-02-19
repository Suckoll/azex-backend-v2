from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# CORS Configuration - This is critical
CORS(app, 
     origins=['https://azex-portal.vercel.app', 'http://localhost:3000'],
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
     supports_credentials=True)

# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='admin')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200))
    manager_name = db.Column(db.String(100))

# Initialize database and seed data
with app.app_context():
    db.create_all()

    # Seed test user
    if not User.query.first():
        admin = User(email='admin@azex.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # Seed branches
    if not Branch.query.first():
        b1 = Branch(name='AZEX Prescott', city='Prescott', state='AZ', address='123 Main St')
        b2 = Branch(name='AZEX Phoenix', city='Phoenix', state='AZ', address='456 Central Ave')
        db.session.add_all([b1, b2])
        db.session.commit()

# Routes
@app.route('/')
def home():
    return "AZEX Customer Management System Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 204
    
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    user = User.query.filter_by(email=data.get('email')).first()
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
        return jsonify({'access_token': token}), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/branches', methods=['GET', 'OPTIONS'])
@jwt_required(optional=False)
def get_branches():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        branches = Branch.query.all()
        return jsonify([{
            'id': b.id,
            'name': b.name,
            'city': b.city,
            'state': b.state,
            'address': b.address or ''
        } for b in branches]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized - Invalid or missing token'}), 401

if __name__ == '__main__':
    app.run(debug=True)