from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
    password_hash = db.Column(db.String(200))  # Renamed to make intent clear; customers may not have password
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
    name = db.Column(db.String(100), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))

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

    # Seed admin with hashed password
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', role='admin')
        admin.set_password('azex2025')
        db.session.add(admin)
        db.session.commit()

    # Seed branches if none exist
    if not Branch.query.first():
        prescott = Branch(name='AZEX Prescott', city='Prescott', state='AZ', address='123 Main St')
        phoenix = Branch(name='AZEX Phoenix', city='Phoenix', state='AZ', address='456 Central Ave')
        vegas = Branch(name='AZEX Las Vegas', city='Las Vegas', state='NV', address='789 Strip Blvd')
        db.session.add_all([prescott, phoenix, vegas])
        db.session.commit()

    # Seed some technicians if none exist
    if not Technician.query.first():
        tech1 = Technician(name='John Doe', branch_id=prescott.id)
        tech2 = Technician(name='Jane Smith', branch_id=phoenix.id)
        tech3 = Technician(name='Mike Johnson', branch_id=vegas.id)
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
    techs = Technician.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'branch_id': t.branch_id
    } for t in techs])

@app.route('/api/jobs/<int:tech_id>')
@jwt_required()
def get_jobs_for_tech(tech_id):
    jobs = Job.query.filter_by(technician_id=tech_id).all()
    return jsonify([{
        'id': j.id,
        'title': j.title or 'Service Visit',
        'start': j.start.isoformat() if j.start else None,
        'end': j.end.isoformat() if j.end else None,
        'description': j.description or ''
    } for j in jobs])

@app.route('/api/customers', methods=['GET'])
@jwt_required()
def get_customers():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    branch_id = request.args.get('branch_id')
    query = User.query.filter_by(role='customer')
    if branch_id:
        query = query.filter_by(branch_id=branch_id)

    customers = query.all()
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
        'multiUnit': c.multiUnit or False,
        'branch_id': c.branch_id
    } for c in customers])

@app.route('/api/customers', methods=['POST'])
@jwt_required()
def add_customer():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'error': 'Email required'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400

    new_user = User(
        email=data['email'],
        role='customer',
        branch_id=data.get('branch_id'),  # Now supported
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
    # Customers don't need a password for login (admin portal only)
    # If needed later, you can add a set_password here

    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Customer added successfully!', 'id': new_user.id})

@app.route('/api/customers/<int:cust_id>', methods=['PUT'])
@jwt_required()
def update_customer(cust_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    customer = User.query.get_or_404(cust_id)
    if customer.role != 'customer':
        return jsonify({'error': 'Not a customer'}), 400

    data = request.get_json()

    # Fields that can be updated
    updatable_fields = ['firstName', 'lastName', 'phone1', 'email', 'company', 'address', 'city', 'state', 'zip',
                        'billName', 'billEmail', 'billPhone', 'billAddress', 'billCity', 'billState', 'billZip',
                        'multiUnit', 'branch_id']

    for field in updatable_fields:
        if field in data:
            setattr(customer, field, data[field])

    # Special handling for email uniqueness
    if 'email' in data and data['email'] != customer.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400

    db.session.commit()
    return jsonify({'message': 'Customer updated successfully!'})

@app.route('/api/customers/<int:cust_id>', methods=['DELETE'])
@jwt_required()
def delete_customer(cust_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    customer = User.query.get_or_404(cust_id)
    if customer.role != 'customer':
        return jsonify({'error': 'Not a customer'}), 400

    db.session.delete(customer)
    db.session.commit()
    return jsonify({'message': 'Customer deleted successfully!'})

@app.route('/api/logbook', methods=['POST'])
def logbook_report():
    branch_id = request.form.get('branch_id')  # Renamed for clarity (was property_id)
    if not branch_id:
        return jsonify({'error': 'Missing branch ID'}), 400

    photo = request.files.get('photo')
    filename = None
    if photo:
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    report = LogbookReport(
        branch_id=branch_id,
        unit=request.form.get('unit'),
        pest=request.form.get('pest'),
        area=request.form.get('area'),
        description=request.form.get('description'),
        photo=filename,
        reporter=request.form.get('reporter'),
        permission=request.form.get('permission'),
        occupied=request.form.get('occupied')
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'message': 'Report received!'})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
@jwt_required()
def update_job(job_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    data = request.get_json()
    job = Job.query.get_or_404(job_id)

    if 'technician_id' in data:
        job.technician_id = data['technician_id']
    if 'start' in data:
        job.start = datetime.fromisoformat(data['start'])
    if 'end' in data:
        job.end = datetime.fromisoformat(data['end'])
    if 'title' in data:
        job.title = data['title']
    if 'description' in data:
        job.description = data['description']

    db.session.commit()
    return jsonify({'message': 'Job updated'})

@app.route('/api/test')
def test():
    return jsonify({'status': 'Backend working!'})

if __name__ == '__main__':
    app.run(debug=True)