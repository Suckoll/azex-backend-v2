from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os

# -------------------------------
# App Setup
# -------------------------------
app = Flask(__name__)

# Basic config (Heroku sets DATABASE_URL automatically)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-super-secret')

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)  # Allows your Vercel portal to talk to this backend

# -------------------------------
# Simple Models (just so DB creates)
# -------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='admin')

# Create tables on first run
with app.app_context():
    db.create_all()
    
    # Create default admin if not exists
    if not User.query.filter_by(email='admin@azex.com').first():
        admin = User(email='admin@azex.com', password='azex2025', role='admin')
        db.session.add(admin)
        db.session.commit()

# -------------------------------
# Routes
# -------------------------------
@app.route('/')
def home():
    return "AZEX PestGuard CMS is running! Backend is LIVE!"

@app.route('/api/auth/login', methods=['POST'])
def