from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200))
    manager_name = db.Column(db.String(100))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default='customer')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Technician(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(10))
    zip = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    hire_date = db.Column(db.Date)
    pay_rate = db.Column(db.Float)
    employment_status = db.Column(db.String(20), default='Active')  # Active, On Leave, Terminated
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)

    @property
    def name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or 'Unnamed Technician'

class TechnicianDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('technician.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    category = db.Column(db.String(100), default='Other')
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    technician_id = db.Column(db.Integer, db.ForeignKey('technician.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    title = db.Column(db.String(200))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    description = db.Column(db.String(500))

class LogbookReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    unit = db.Column(db.String(50))
    pest = db.Column(db.String(100))
    area = db.Column(db.String(100))
    description = db.Column(db.String(500))
    photo = db.Column(db.String(200))
    reporter = db.Column(db.String(100))
    permission = db.Column(db.String(50))
    occupied = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', role='admin')
        admin.set_password('azex2025')
        db.session.add(admin)
        db.session.commit()

    if not Branch.query.first():
        prescott = Branch(name='AZEX Prescott', city='Prescott', state='AZ', address='123 Main St')
        phoenix = Branch(name='AZEX Phoenix', city='Phoenix', state='AZ', address='456 Central Ave')
        vegas = Branch(name='AZEX Las Vegas', city='Las Vegas', state='NV', address='789 Strip Blvd')
        db.session.add_all([prescott, phoenix, vegas])
        db.session.commit()

    if not Technician.query.first():
        tech1 = Technician(first_name='John', last_name='Doe', branch_id=prescott.id, email='john@azex.com', phone='555-1234', hire_date=date(2023, 1, 15), pay_rate=28.50, employment_status='Active')
        tech2 = Technician(first_name='Jane', last_name='Smith', branch_id=phoenix.id, email='jane@azex.com', phone='555-5678', hire_date=date(2022, 6, 20), pay_rate=30.00, employment_status='Active')
        tech3 = Technician(first_name='Mike', last_name='Johnson', branch_id=vegas.id, email='mike@azex.com', phone='555-9012', hire_date=date(2024, 3, 10), pay_rate=27.00, employment_status='Active')
        db.session.add_all([tech1, tech2, tech3])
        db.session.commit()

@app.route('/')
def home():
    return "AZEX PestGuard Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
        return jsonify({'access_token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/branches')
@jwt_required()
def get_branches():
    branches = Branch.query.all()
    return jsonify([{
        'id': b.id,
        'name': b.name,
        'city': b.city,
        'state': b.state,
        'address': b.address or ''
    } for b in branches])

@app.route('/api/technicians')
@jwt_required()
def get_technicians():
    techs = Technician.query.options(joinedload(Technician.branch_id)).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'firstName': t.first_name or '',
        'lastName': t.last_name or '',
        'email': t.email or '',
        'phone': t.phone or '',
        'address': t.address or '',
        'city': t.city or '',
        'state': t.state or '',
        'zip': t.zip or '',
        'dateOfBirth': t.date_of_birth.isoformat() if t.date_of_birth else None,
        'emergencyContactName': t.emergency_contact_name or '',
        'emergencyContactPhone': t.emergency_contact_phone or '',
        'hireDate': t.hire_date.isoformat() if t.hire_date else None,
        'payRate': t.pay_rate,
        'employmentStatus': t.employment_status or 'Active',
        'branch_id': t.branch_id
    } for t in techs])

@app.route('/api/technicians', methods=['POST'])
@jwt_required()
def add_technician():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    data = request.get_json()
    if not data.get('branch_id'):
        return jsonify({'error': 'Branch required'}), 400

    new_tech = Technician(
        first_name=data.get('firstName', ''),
        last_name=data.get('lastName', ''),
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        zip=data.get('zip'),
        date_of_birth=datetime.strptime(data.get('dateOfBirth'), '%Y-%M-%d').date() if data.get('dateOfBirth') else None,
        emergency_contact_name=data.get('emergencyContactName'),
        emergency_contact_phone=data.get('emergencyContactPhone'),
        hire_date=datetime.strptime(data.get('hireDate'), '%Y-%M-%d').date() if data.get('hireDate') else None,
        pay_rate=data.get('payRate'),
        employment_status=data.get('employmentStatus', 'Active'),
        branch_id=data['branch_id']
    )
    db.session.add(new_tech)
    db.session.commit()
    return jsonify({'message': 'Technician added successfully!', 'id': new_tech.id})

@app.route('/api/technicians/<int:tech_id>', methods=['PUT'])
@jwt_required()
def update_technician(tech_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    tech = Technician.query.get_or_404(tech_id)
    data = request.get_json()

    updatable = ['firstName', 'lastName', 'email', 'phone', 'address', 'city', 'state', 'zip',
                 'dateOfBirth', 'emergencyContactName', 'emergencyContactPhone', 'hireDate',
                 'payRate', 'employmentStatus', 'branch_id']

    for field in updatable:
        if field in data:
            value = data[field]
            if field in ['dateOfBirth', 'hireDate'] and value:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            elif field == 'payRate' and value is not None:
                value = float(value)
            elif field == 'branch_id':
                value = int(value)
            setattr(tech, field.replace('Name', '_name').replace('Date', '_date').lower().replace('ofbirth', '_of_birth'), value)

    db.session.commit()
    return jsonify({'message': 'Technician updated successfully!'})

@app.route('/api/technicians/<int:tech_id>', methods=['DELETE'])
@jwt_required()
def delete_technician(tech_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    tech = Technician.query.get_or_404(tech_id)
    db.session.delete(tech)
    db.session.commit()
    return jsonify({'message': 'Technician deleted successfully!'})

@app.route('/api/technicians/<int:tech_id>/documents', methods=['POST'])
@jwt_required()
def upload_tech_document(tech_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    Technician.query.get_or_404(tech_id)

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    description = request.form.get('description', '')
    category = request.form.get('category', 'Other')

    doc = TechnicianDocument(
        technician_id=tech_id,
        filename=filename,
        description=description,
        category=category
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify({'message': 'Document uploaded successfully!'})

@app.route('/api/technicians/<int:tech_id>/documents')
@jwt_required()
def get_tech_documents(tech_id):
    Technician.query.get_or_404(tech_id)
    docs = TechnicianDocument.query.filter_by(technician_id=tech_id).order_by(TechnicianDocument.upload_date.desc()).all()
    return jsonify([{
        'id': d.id,
        'filename': d.filename,
        'url': f"/uploads/{d.filename}",
        'description': d.description or '',
        'category': d.category,
        'uploadDate': d.upload_date.isoformat()
    } for d in docs])

@app.route('/api/technicians/<int:tech_id>/documents/<int:doc_id>', methods=['DELETE'])
@jwt_required()
def delete_tech_document(tech_id, doc_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    doc = TechnicianDocument.query.get_or_404(doc_id)
    if doc.technician_id != tech_id:
        return jsonify({'error': 'Not found'}), 404

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted successfully!'})

@app.route('/api/jobs/<int:tech_id>')
@jwt_required()
def get_jobs_for_tech(tech_id):
    jobs = Job.query.options(joinedload(Job.customer)).filter_by(technician_id=tech_id).all()
    return jsonify([{
        'id': j.id,
        'title': j.title or (f"{j.customer.firstName} {j.customer.lastName}" if j.customer else 'Service Visit'),
        'start': j.start.isoformat() if j.start else None,
        'end': j.end.isoformat() if j.end else None,
        'description': j.description or '',
        'customer': {
            'name': f"{j.customer.firstName or ''} {j.customer.lastName or ''}".strip() or j.customer.company or 'Unknown Customer' if j.customer else None,
            'address': j.customer.address or '' if j.customer else '',
            'city': j.customer.city or '' if j.customer else '',
            'state': j.customer.state or '' if j.customer else '',
            'zip': j.customer.zip or '' if j.customer else '',
            'phone': j.customer.phone1 or '' if j.customer else ''
        } if j.customer else None
    } for j in jobs])

# (other routes unchanged: customers, logbook, update_job, etc.)

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)