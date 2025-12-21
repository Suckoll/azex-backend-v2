@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and data.get('password') == 'azex2025':
        token = create_access_token(identity=str(user.id))  # String ID
        return jsonify({'access_token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/customers', methods=['POST'])
@jwt_required()
def add_customer():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(int(current_user_id))
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'error': 'Email required'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    new_user = User(
        email=data['email'],
        password='temp123',
        role='customer',
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
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Customer added successfully!'})