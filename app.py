from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change-me-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='customer')  # admin or customer

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='unpaid')
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(200))

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(500))
    tech_notes = db.Column(db.String(500))

class BugReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.String(500))
    photo = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='new')

with app.app_context():
    db.create_all()
    # Create admin
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', password='azex2025', role='admin')
        db.session.add(admin)
        db.session.commit()
    # Create test customer
    if not User.query.filter_by(email='customer@azex.com').first():
        customer = User(email='customer@azex.com', password='azex2025', role='customer')
        db.session.add(customer)
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

@app.route('/api/invoices')
@jwt_required()
def get_invoices():
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    if user.role == 'admin':
        invoices = Invoice.query.all()
    else:
        invoices = Invoice.query.filter_by(user_id=user.id).all()
    return jsonify([{
        'id': i.id,
        'amount': i.amount,
        'status': i.status,
        'date': i.date.isoformat(),
        'description': i.description
    } for i in invoices])

@app.route('/api/services')
@jwt_required()
def get_services():
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    if user.role == 'admin':
        services = Service.query.all()
    else:
        services = Service.query.filter_by(user_id=user.id).all()
    return jsonify([{
        'id': s.id,
        'date': s.date.isoformat(),
        'description': s.description,
        'tech_notes': s.tech_notes
    } for s in services])

@app.route('/api/bugs', methods=['GET', 'POST'])
@jwt_required()
def bugs():
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    if request.method == 'POST':
        description = request.form.get('description')
        photo = request.files.get('photo')
        filename = None
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        report = BugReport(user_id=user.id, description=description, photo=filename)
        db.session.add(report)
        db.session.commit()
        return jsonify({'message': 'Bug reported!'})
    else:
        if user.role == 'admin':
            reports = BugReport.query.all()
        else:
            reports = BugReport.query.filter_by(user_id=user.id).all()
        return jsonify([{
            'id': r.id,
            'description': r.description,
            'photo': r.photo,
            'date': r.date.isoformat(),
            'status': r.status
        } for r in reports])

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)