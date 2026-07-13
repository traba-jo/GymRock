"""
GYMROCK - Backend Principal
app.py - Servidor Flask con autenticación y endpoints completos
"""

import os
import sys
import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client

# =====================================================
# CONFIGURACIÓN DE RUTAS
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    env_path = os.path.join(BASE_DIR, '.env')
    load_dotenv(env_path)
    print(f"✅ Cargando .env desde: {env_path}")
except ImportError:
    print("⚠️ python-dotenv no instalado, usando variables de entorno del sistema")

# =====================================================
# CONFIGURACIÓN
# =====================================================
app = Flask(__name__)
CORS(app)

# Variables de entorno
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SECRET_KEY = os.getenv('SECRET_KEY', 'gymrock_secret_key_2026')
JWT_EXPIRATION = int(os.getenv('JWT_EXPIRATION', 7))
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'GymRock2026')

# Verificar credenciales
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Faltan SUPABASE_URL o SUPABASE_KEY")
    print("   En Render: agrega las variables en Environment")
    # No usar sys.exit(1) en Render, mejor mostrar error en ruta
    # pero inicializar igual para que no crashee
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Conexión a Supabase establecida")
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        supabase = None

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(user_id, email, rol):
    payload = {
        'user': {'id': user_id, 'email': email, 'rol': rol},
        'exp': datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION)
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
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.4',
        'supabase': 'conectado' if supabase else 'no configurado'
    }), 200

@app.route('/api/test/db', methods=['GET'])
def test_db():
    if not supabase:
        return jsonify({'status': 'error', 'message': 'Supabase no configurado'}), 500
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
    if not supabase:
        return jsonify({'error': 'Supabase no configurado'}), 500
    try:
        result = supabase.table('gimnasios').select('*').eq('visible_publico', True).eq('estado_licencia', 'activa').execute()
        return jsonify({'status': 'success', 'data': result.data, 'total': len(result.data)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/registro/gimnasio', methods=['POST'])
def registrar_gimnasio():
    if not supabase:
        return jsonify({'error': 'Supabase no configurado'}), 500
    try:
        data = request.get_json()
        required = ['nombre', 'email', 'password', 'estado', 'municipio']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Campo {field} requerido'}), 400
        
        hashed = hash_password(data['password'])
        fecha_corte = datetime.now(timezone.utc) + timedelta(days=30)
        
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
            'fecha_registro': datetime.now(timezone.utc).isoformat()
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
    if not supabase:
        return jsonify({'error': 'Supabase no configurado'}), 500
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
            'fecha_registro': datetime.now(timezone.utc).isoformat()
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
    if not supabase:
        return jsonify({'error': 'Supabase no configurado'}), 500
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
    if not supabase:
        return jsonify({'error': 'Supabase no configurado'}), 500
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
# SERVIR FRONTEND (CON DEBUG)
# =====================================================
import os

@app.route('/')
def serve_index():
    try:
        # Mostrar qué archivos hay en la raíz
        files = os.listdir('.')
        print(f"Archivos en raíz: {files}")
        
        # Intentar servir index.html
        return send_from_directory('frontend_web', 'index.html')
    except Exception as e:
        return jsonify({
            'error': str(e),
            'files': os.listdir('.'),
            'cwd': os.getcwd()
        }), 404

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory('frontend_web', path)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# =====================================================
# INICIO
# =====================================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 Servidor iniciado en http://localhost:{port}")
    print(f"📁 Directorio base: {BASE_DIR}")
    app.run(host='0.0.0.0', port=port, debug=False)