"""
GYMROCK - Backend Principal
app.py - Servidor Flask con autenticación y endpoints completos
"""

import os
import hashlib
import jwt
import datetime
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client

# =====================================================
# CONFIGURACIÓN
# =====================================================
app = Flask(__name__)
CORS(app)

# Variables de entorno
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SECRET_KEY = os.environ.get('SECRET_KEY', 'gymrock_secret_key_2026')
JWT_EXPIRATION = int(os.environ.get('JWT_EXPIRATION', 7))
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'GymRock2026')

# Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(user_id, email, rol):
    payload = {
        'user': {'id': user_id, 'email': email, 'rol': rol},
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRATION)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'error': 'Token requerido'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = data['user']
        except:
            return jsonify({'error': 'Token inválido'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# =====================================================
# ENDPOINTS DE API
# =====================================================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'GymRock API funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.3'
    }), 200

@app.route('/api/test/db', methods=['GET'])
def test_db():
    try:
        result = supabase.table('gimnasios').select('id', count='exact').limit(1).execute()
        return jsonify({
            'status': 'ok',
            'message': 'Conexión a Supabase exitosa',
            'total_registros': result.count if result.count else 0
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/gimnasios', methods=['GET'])
def listar_gimnasios():
    try:
        result = supabase.table('gimnasios').select('*').eq('visible_publico', True).eq('estado_licencia', 'activa').execute()
        return jsonify({'status': 'success', 'data': result.data, 'total': len(result.data)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/registro/gimnasio', methods=['POST'])
def registrar_gimnasio():
    try:
        data = request.get_json()
        required = ['nombre', 'email', 'password', 'estado', 'municipio']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Campo {field} requerido'}), 400
        
        hashed = hash_password(data['password'])
        fecha_corte = datetime.now() + timedelta(days=30)
        
        new_gym = {
            'nombre': data['nombre'],
            'email': data['email'],
            'password_hash': hashed,
            'estado': data['estado'],
            'municipio': data['municipio'],
            'direccion': data.get('direccion', ''),
            'telefono': data.get('telefono', ''),
            'plan': data.get('plan', 'basico'),
            'licencia_fecha_corte': fecha_corte.isoformat(),
            'estado_licencia': 'activa',
            'visible_publico': True,
            'fecha_registro': datetime.now().isoformat()
        }
        
        result = supabase.table('gimnasios').insert(new_gym).execute()
        
        if result.data:
            gym = result.data[0]
            token = generate_token(gym['id'], gym['email'], 'gimnasio')
            return jsonify({
                'status': 'success',
                'message': 'Gimnasio registrado exitosamente',
                'data': {
                    'id': gym['id'],
                    'nombre': gym['nombre'],
                    'email': gym['email'],
                    'token': token
                }
            }), 201
        return jsonify({'error': 'Error al registrar'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/registro/cliente', methods=['POST'])
def registrar_cliente():
    try:
        data = request.get_json()
        required = ['nombre', 'email', 'password', 'estado', 'municipio']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Campo {field} requerido'}), 400
        
        hashed = hash_password(data['password'])
        
        new_user = {
            'nombre': data['nombre'],
            'email': data['email'],
            'password_hash': hashed,
            'estado': data['estado'],
            'municipio': data['municipio'],
            'telefono': data.get('telefono', ''),
            'fecha_registro': datetime.now().isoformat()
        }
        
        result = supabase.table('usuarios').insert(new_user).execute()
        
        if result.data:
            user = result.data[0]
            token = generate_token(user['id'], user['email'], 'cliente')
            return jsonify({
                'status': 'success',
                'message': 'Cliente registrado exitosamente',
                'data': {
                    'id': user['id'],
                    'nombre': user['nombre'],
                    'email': user['email'],
                    'token': token
                }
            }), 201
        return jsonify({'error': 'Error al registrar'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        rol = data.get('rol', 'cliente')
        
        if not email or not password:
            return jsonify({'error': 'Email y password requeridos'}), 400
        
        hashed = hash_password(password)
        
        if rol == 'gimnasio':
            result = supabase.table('gimnasios').select('*').eq('email', email).eq('password_hash', hashed).execute()
        else:
            result = supabase.table('usuarios').select('*').eq('email', email).eq('password_hash', hashed).execute()
        
        if not result.data:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        user = result.data[0]
        token = generate_token(user['id'], user['email'], rol)
        
        return jsonify({
            'status': 'success',
            'message': 'Login exitoso',
            'data': {
                'id': user['id'],
                'nombre': user['nombre'],
                'email': user['email'],
                'rol': rol,
                'token': token
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/verify-token', methods=['POST'])
def verify_admin_token():
    try:
        data = request.get_json()
        token = data.get('token')
        if token == ADMIN_TOKEN:
            return jsonify({'status': 'success', 'valid': True}), 200
        return jsonify({'status': 'error', 'valid': False}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/dashboard', methods=['GET'])
def admin_dashboard():
    try:
        token = request.args.get('token')
        if token != ADMIN_TOKEN:
            return jsonify({'error': 'Token inválido'}), 401
        
        gimnasios = supabase.table('gimnasios').select('*').execute()
        usuarios = supabase.table('usuarios').select('*').execute()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_gimnasios': len(gimnasios.data),
                'total_usuarios': len(usuarios.data),
                'gimnasios': gimnasios.data
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# SERVIR FRONTEND (Render)
# =====================================================
@app.route('/')
def serve_index():
    return send_from_directory('../frontend_web', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend_web', path)

# =====================================================
# INICIO
# =====================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)