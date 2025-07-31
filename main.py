#!/usr/bin/env python3
"""
Biwenger Liga Manager
Aplicación Flask para gestión de liga de Biwenger
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
import requests
from functools import wraps

# Configuración de la aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = 'biwenger-liga-manager-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biwenger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db = SQLAlchemy(app)
CORS(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos de base de datos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    biwenger_username = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Activo')
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    sanctions = db.relationship('Sanction', backref='player', lazy=True)

class Sanction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    sanction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    date_applied = db.Column(db.DateTime, default=datetime.utcnow)
    paid = db.Column(db.Boolean, default=False)
    date_paid = db.Column(db.DateTime)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_type = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Prize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Acceso denegado. Se requieren permisos de administrador.'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Rutas principales
@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('index')})
        
        return jsonify({'error': 'Credenciales incorrectas'}), 401
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        admin_key = data.get('admin_key', '')
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'El usuario ya existe'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'El email ya está registrado'}), 400
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=(admin_key == 'ADMIN2024')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Usuario registrado correctamente'})
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# API Endpoints
@app.route('/api/players', methods=['GET'])
@login_required
def get_players():
    players = Player.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'email': p.email,
        'biwenger_username': p.biwenger_username,
        'phone': p.phone,
        'balance': p.balance,
        'status': p.status,
        'join_date': p.join_date.strftime('%Y-%m-%d')
    } for p in players])

@app.route('/api/players', methods=['POST'])
@login_required
@admin_required
def add_player():
    data = request.get_json()
    
    # Verificar si el email ya existe
    if Player.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email ya registrado'}), 400
    
    player = Player(
        name=data['name'],
        email=data['email'],
        biwenger_username=data['biwenger_username'],
        phone=data['phone']
    )
    
    db.session.add(player)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Jugador agregado correctamente'})

@app.route('/api/players/<int:player_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    # Eliminar sanciones asociadas
    Sanction.query.filter_by(player_id=player_id).delete()
    
    db.session.delete(player)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Jugador eliminado correctamente'})

@app.route('/api/sanctions', methods=['GET'])
@login_required
def get_sanctions():
    sanctions = db.session.query(Sanction, Player.name).join(Player).all()
    return jsonify([{
        'id': s.Sanction.id,
        'player_name': s.name,
        'sanction_type': s.Sanction.sanction_type,
        'amount': s.Sanction.amount,
        'description': s.Sanction.description,
        'date_applied': s.Sanction.date_applied.strftime('%Y-%m-%d'),
        'paid': s.Sanction.paid
    } for s in sanctions])

@app.route('/api/sanctions', methods=['POST'])
@login_required
@admin_required
def apply_sanction():
    data = request.get_json()
    
    player = Player.query.get_or_404(data['player_id'])
    
    sanction = Sanction(
        player_id=data['player_id'],
        sanction_type=data['sanction_type'],
        amount=data['amount'],
        description=data.get('description', '')
    )
    
    # Actualizar balance del jugador
    player.balance -= data['amount']
    
    db.session.add(sanction)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Sanción aplicada correctamente'})

@app.route('/api/sanctions/<int:sanction_id>/pay', methods=['POST'])
@login_required
@admin_required
def mark_sanction_paid(sanction_id):
    sanction = Sanction.query.get_or_404(sanction_id)
    player = Player.query.get_or_404(sanction.player_id)
    
    sanction.paid = True
    sanction.date_paid = datetime.utcnow()
    player.balance += sanction.amount
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Sanción marcada como pagada'})

@app.route('/api/rules', methods=['GET'])
@login_required
def get_rules():
    rules = Rule.query.all()
    return jsonify([{
        'id': r.id,
        'rule_type': r.rule_type,
        'amount': r.amount,
        'description': r.description
    } for r in rules])

@app.route('/api/rules', methods=['POST'])
@login_required
@admin_required
def update_rules():
    data = request.get_json()
    
    for rule_data in data['rules']:
        rule = Rule.query.filter_by(rule_type=rule_data['rule_type']).first()
        if rule:
            rule.amount = rule_data['amount']
            rule.updated_at = datetime.utcnow()
        else:
            rule = Rule(
                rule_type=rule_data['rule_type'],
                amount=rule_data['amount'],
                description=rule_data.get('description', '')
            )
            db.session.add(rule)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Reglas actualizadas correctamente'})

@app.route('/api/dashboard')
@login_required
def dashboard_data():
    total_players = Player.query.count()
    pending_sanctions = Sanction.query.filter_by(paid=False).count()
    total_sanctions_amount = db.session.query(db.func.sum(Sanction.amount)).filter_by(paid=False).scalar() or 0
    
    return jsonify({
        'total_players': total_players,
        'pending_sanctions': pending_sanctions,
        'total_sanctions_amount': total_sanctions_amount,
        'current_jornada': 1  # Esto se puede integrar con la API de Biwenger
    })

@app.route('/api/whatsapp/group', methods=['POST'])
@login_required
@admin_required
def create_whatsapp_group():
    data = request.get_json()
    group_name = data.get('group_name', 'Liga Biwenger 2024')
    
    players = Player.query.all()
    phone_numbers = [p.phone for p in players]
    
    # En una implementación real, aquí integrarías con la API de WhatsApp Business
    group_info = {
        'group_name': group_name,
        'participants': len(phone_numbers),
        'phones': phone_numbers,
        'invite_link': f"https://chat.whatsapp.com/invite/{generate_group_id()}"
    }
    
    return jsonify({
        'success': True,
        'group_info': group_info,
        'message': 'Grupo de WhatsApp creado correctamente'
    })

def generate_group_id():
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=22))

# Integración con Biwenger (simulada)
@app.route('/api/biwenger/connect', methods=['POST'])
@login_required
@admin_required
def connect_biwenger():
    # En una implementación real, aquí se conectaría con la API de Biwenger
    return jsonify({
        'success': True,
        'message': 'Conexión con Biwenger establecida (simulada)',
        'features': [
            'Visualización de alineaciones',
            'Gestión de fichajes',
            'Sincronización de datos'
        ]
    })

@app.route('/api/biwenger/lineups')
@login_required
def get_lineups():
    # Simulación de datos de alineaciones
    return jsonify({
        'jornada': 1,
        'lineups': [
            {
                'player': 'Jugador 1',
                'formation': '4-3-3',
                'points': 85,
                'valid': True
            },
            {
                'player': 'Jugador 2',
                'formation': '4-4-2',
                'points': 72,
                'valid': False
            }
        ]
    })

def initialize_database():
    """Inicializar base de datos con datos por defecto"""
    db.create_all()
    
    # Crear usuario administrador por defecto
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@biwenger.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
    
    # Crear reglas por defecto
    default_rules = [
        {'rule_type': 'no_payment', 'amount': 20.0, 'description': 'No pago inicial'},
        {'rule_type': 'negative_balance', 'amount': 10.0, 'description': 'Saldo negativo'},
        {'rule_type': 'no_payment_fine', 'amount': 15.0, 'description': 'No pago de multa'},
        {'rule_type': 'wrong_lineup', 'amount': 5.0, 'description': 'Alineación indebida'},
        {'rule_type': 'missing_players', 'amount': 5.0, 'description': 'Falta de jugadores'},
    ]
    
    for rule_data in default_rules:
        if not Rule.query.filter_by(rule_type=rule_data['rule_type']).first():
            rule = Rule(**rule_data)
            db.session.add(rule)
    
    # Crear premios por defecto
    default_prizes = [
        {'position': 1, 'amount': 1000000.0, 'description': 'Primer lugar'},
        {'position': 2, 'amount': 1500000.0, 'description': 'Segundo lugar'},
        {'position': 3, 'amount': 2000000.0, 'description': 'Tercer lugar'},
    ]
    
    for prize_data in default_prizes:
        if not Prize.query.filter_by(position=prize_data['position']).first():
            prize = Prize(**prize_data)
            db.session.add(prize)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        initialize_database()
    
    print("🚀 Biwenger Liga Manager iniciado!")
    print("📱 Accede a: http://localhost:5000")
    print("👑 Usuario admin: admin / admin123")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
