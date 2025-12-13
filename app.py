from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os
from datetime import datetime

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
    role = db.Column(db.String(20), default='customer')  # admin, customer, technician

class Technician(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    technician_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.DateTime)
    address = db.Column(db.String(200))
    description = db.Column(db.String(500))
    status = db.Column(db.String(20), default='scheduled')

with app.app_context():
    db.create_all()
    # Admin
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

@app.route('/api/technicians', methods=['GET'])
@jwt_required()
def get_technicians():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    techs = User.query.filter_by(role='technician').all()
    return jsonify([{'id': t.id, 'name': t.name or t.email} for t in techs])

@app.route('/api/jobs/<int:tech_id>', methods=['GET'])
@jwt_required()
def get_jobs(tech_id):
    current_user = get_jwt_identity()
    if current_user['role'] not in ['admin', 'technician'] or (current_user['role'] == 'technician' and current_user['id'] != tech_id):
        return jsonify({'error': 'Unauthorized'}), 403
    jobs = Job.query.filter_by(technician_id=tech_id).all()
    return jsonify([{
        'id': j.id,
        'date': j.date.isoformat() if j.date else None,
        'address': j.address,
        'description': j.description,
        'status': j.status
    } for j in jobs])

@app.route('/api/jobs', methods=['POST'])
@jwt_required()
def add_job():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    data = request.get_json()
    job = Job(
        customer_id=data['customer_id'],
        technician_id=data['technician_id'],
        date=datetime.fromisoformat(data['date']),
        address=data['address'],
        description=data['description']
    )
    db.session.add(job)
    db.session.commit()
    return jsonify({'message': 'Job added'})

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)