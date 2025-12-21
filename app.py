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

class Technician(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('technician.id'))
    title = db.Column(db.String(200))
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(500))
    recurring = db.Column(db.String(20))  # weekly, monthly, etc.

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', password='azex2025', role='admin')
        db.session.add(admin)
        db.session.commit()
    # Add sample technician
    if not Technician.query.first():
        tech = Technician(name='John Tech', email='john@azex.com')
        db.session.add(tech)
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

@app.route('/api/technicians')
@jwt_required()
def get_technicians():
    techs = Technician.query.all()
    return jsonify([{'id': t.id, 'name': t.name} for t in techs])

@app.route('/api/jobs', methods=['GET', 'POST'])
@jwt_required()
def jobs():
    current_user = get_jwt()
    if current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    if request.method == 'POST':
        data = request.get_json()
        job = Job(
            customer_id=data['customer_id'],
            technician_id=data.get('technician_id'),
            title=data['title'],
            start=datetime.fromisoformat(data['start']),
            end=datetime.fromisoformat(data['end']),
            description=data.get('description'),
            recurring=data.get('recurring')
        )
        db.session.add(job)
        db.session.commit()
        return jsonify({'message': 'Job added'})
    else:
        jobs = Job.query.all()
        return jsonify([{
            'id': j.id,
            'title': j.title,
            'start': j.start.isoformat(),
            'end': j.end.isoformat(),
            'description': j.description,
            'technician_id': j.technician_id,
            'customer_id': j.customer_id
        } for j in jobs])

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)