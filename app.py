from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')
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
    name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    manager_name = db.Column(db.String(100))
    manager_email = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Links to customer account

class BugReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
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
    # Create admin
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', password='azex2025', role='admin', name='Admin User')
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

@app.route('/api/properties', methods=['GET', 'POST'])
@jwt_required()
def properties():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    if request.method == 'POST':
        data = request.get_json()
        new_property = Property(
            name=data['name'],
            address=data['address'],
            manager_name=data.get('manager_name'),
            manager_email=data.get('manager_email')
        )
        db.session.add(new_property)
        db.session.commit()
        return jsonify({'message': 'Property added', 'id': new_property.id})
    else:
        properties = Property.query.all()
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'address': p.address,
            'manager_name': p.manager_name,
            'manager_email': p.manager_email
        } for p in properties])

@app.route('/api/bugs/<int:property_id>', methods=['GET', 'POST'])
def bugs(property_id):
    if request.method == 'POST':
        description = request.form.get('description')
        photo = request.files.get('photo')
        filename = None
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        report = BugReport(
            property_id=property_id,
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
        reports = BugReport.query.filter_by(property_id=property_id).all()
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
            'date': r.date.isoformat(),
            'status': r.status
        } for r in reports])

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)