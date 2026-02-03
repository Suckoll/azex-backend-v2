from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy.orm import joinedload
from sqlalchemy import UniqueConstraint

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

# Existing models unchanged (Branch, User, Technician, TechnicianDocument, Job, LogbookReport)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=False)  # Pesticide, Rodenticide, Termiticide, Bait, Trap, Equipment, Other
    manufacturer = db.Column(db.String(100))
    epa_number = db.Column(db.String(50))
    active_ingredients = db.Column(db.Text)
    unit = db.Column(db.String(20), default='each')  # gallon, oz, lb, box, etc.
    discontinued = db.Column(db.Boolean, default=False)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    reorder_level = db.Column(db.Float, default=0.0)

    __table_args__ = (UniqueConstraint('product_id', 'branch_id', name='unique_product_branch'),)

    product = db.relationship('Product', backref='stocks')

with app.app_context():
    db.create_all()

    # Existing seeding unchanged...

    # Seed sample products
    if not Product.query.first():
        samples = [
            Product(name='Talstar P Professional Insecticide', category='Pesticide', manufacturer='FMC', epa_number='279-3206', active_ingredients='Bifenthrin 7.9%', unit='gallon'),
            Product(name='Tempo SC Ultra', category='Pesticide', manufacturer='Bayer', epa_number='3125-503', active_ingredients='Beta-cyfluthrin 11.8%', unit='oz'),
            Product(name='Alpine Flea & Bed Bug', category='Pesticide', manufacturer='BASF', epa_number='499-540', active_ingredients='Dinotefuran', unit='oz'),
            Product(name='Trelona ATBS Bait', category='Termiticide', manufacturer='BASF', epa_number='499-556', active_ingredients='Novaluron', unit='box'),
            Product(name='Contrac Blox Rodenticide', category='Rodenticide', manufacturer='Bell Labs', epa_number='12455-79', active_ingredients='Bromadiolone 0.005%', unit='lb'),
            Product(name='Victor Snap Traps', category='Trap', manufacturer='Woodstream', unit='each'),
            Product(name='B&G Sprayer 1 Gallon', category='Equipment', manufacturer='B&G', unit='each')
        ]
        db.session.add_all(samples)
        db.session.commit()

        # Seed some initial stock for branches (assuming branch IDs 1,2,3 from seeding)
        branches = Branch.query.all()
        products = Product.query.all()
        for branch in branches:
            for prod in products:
                stock = Stock(product_id=prod.id, branch_id=branch.id, quantity=10.0 if prod.unit != 'each' else 20, reorder_level=5.0 if prod.unit != 'each' else 10)
                db.session.add(stock)
        db.session.commit()

# Existing routes unchanged...

@app.route('/api/products')
@jwt_required()
def get_products():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    discontinued = request.args.get('discontinued', 'false').lower() == 'true'
    query = Product.query
    if not discontinued:
        query = query.filter_by(discontinued=False)

    products = query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category': p.category,
        'manufacturer': p.manufacturer or '',
        'epa_number': p.epa_number or '',
        'active_ingredients': p.active_ingredients or '',
        'unit': p.unit,
        'discontinued': p.discontinued
    } for p in products])

@app.route('/api/products', methods=['POST'])
@jwt_required()
def add_product():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    data = request.get_json()
    required = ['name', 'category']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    if Product.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Product name already exists'}), 400

    new_prod = Product(
        name=data['name'],
        category=data['category'],
        manufacturer=data.get('manufacturer'),
        epa_number=data.get('epa_number'),
        active_ingredients=data.get('active_ingredients'),
        unit=data.get('unit', 'each'),
        discontinued=False
    )
    db.session.add(new_prod)
    db.session.commit()

    # Auto-create zero stock for all branches
    branches = Branch.query.all()
    for b in branches:
        stock = Stock(product_id=new_prod.id, branch_id=b.id, quantity=0.0, reorder_level=0.0)
        db.session.add(stock)
    db.session.commit()

    return jsonify({'message': 'Product added successfully!', 'id': new_prod.id})

@app.route('/api/products/<int:prod_id>', methods=['PUT'])
@jwt_required()
def update_product(prod_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    prod = Product.query.get_or_404(prod_id)
    data = request.get_json()

    if 'name' in data and data['name'] != prod.name:
        if Product.query.filter_by(name=data['name']).first():
            return jsonify({'error': 'Product name already exists'}), 400
        prod.name = data['name']

    if 'category' in data: prod.category = data['category']
    if 'manufacturer' in data: prod.manufacturer = data['manufacturer']
    if 'epa_number' in data: prod.epa_number = data['epa_number']
    if 'active_ingredients' in data: prod.active_ingredients = data['active_ingredients']
    if 'unit' in data: prod.unit = data['unit']
    if 'discontinued' in data: prod.discontinued = data['discontinued']

    db.session.commit()
    return jsonify({'message': 'Product updated successfully!'})

@app.route('/api/stock')
@jwt_required()
def get_stock():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    branch_id = request.args.get('branch_id')
    if not branch_id:
        return jsonify({'error': 'branch_id required'}), 400

    stocks = Stock.query.options(joinedload(Stock.product)).filter_by(branch_id=branch_id).all()
    return jsonify([{
        'id': s.id,
        'product_id': s.product_id,
        'product_name': s.product.name,
        'category': s.product.category,
        'manufacturer': s.product.manufacturer or '',
        'epa_number': s.product.epa_number or '',
        'unit': s.product.unit,
        'discontinued': s.product.discontinued,
        'quantity': s.quantity,
        'reorder_level': s.reorder_level,
        'low_stock': s.quantity <= s.reorder_level
    } for s in stocks])

@app.route('/api/stock/adjust', methods=['POST'])
@jwt_required()
def adjust_stock():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    data = request.get_json()
    required = ['product_id', 'branch_id', 'adjustment']  # adjustment can be positive (add) or negative (use/sell)
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    stock = Stock.query.filter_by(product_id=data['product_id'], branch_id=data['branch_id']).first_or_404()
    new_quantity = stock.quantity + float(data['adjustment'])

    if new_quantity < 0:
        return jsonify({'error': 'Cannot go below zero'}), 400

    stock.quantity = new_quantity
    db.session.commit()
    return jsonify({'message': 'Stock adjusted successfully!', 'new_quantity': new_quantity})

# Existing routes continue...

if __name__ == '__main__':
    app.run(debug=True)