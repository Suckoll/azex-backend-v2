from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Flask-CORS - Recommended by Copilot
CORS(app, origins=['https://azex-portal.vercel.app', 'http://localhost:3000'])

# MODELS
class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default='admin')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# SEEDING - Force admin creation every startup
with app.app_context():
    db.create_all()

    # Force-create / reset admin user
    admin = User.query.filter_by(email='admin@azex.com').first()
    if not admin:
        admin = User(email='admin@azex.com', role='admin')
        admin.set_password('azex2025')
        db.session.add(admin)
    else:
        admin.set_password('azex2025')  # Reset password every deploy
    db.session.commit()

    # Sample branches
    if not Branch.query.first():
        b1 = Branch(name='AZEX Prescott', city='Prescott', state='AZ', address='123 Main St')
        b2 = Branch(name='AZEX Phoenix', city='Phoenix', state='AZ', address='456 Central Ave')
        db.session.add_all([b1, b2])
        db.session.commit()

@app.route('/')
def home():
    return "AZEX Customer Management System Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
        return jsonify({'access_token': token}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/branches', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_branches():
    if request.method == 'OPTIONS':
        return '', 204

    branches = Branch.query.all()
    return jsonify([{
        'id': b.id,
        'name': b.name,
        'city': b.city,
        'state': b.state,
        'address': b.address or ''
    } for b in branches]), 200

if __name__ == '__main__':
    app.run(debug=True)