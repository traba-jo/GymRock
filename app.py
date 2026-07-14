"""
GYMROCK - Backend Principal
app.py - Servidor Flask con autenticación, endpoints y Mercado Pago
Versión 2.1 - Con pagos integrados
"""

import os
import hashlib
import jwt
import mercadopago
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client

# =====================================================
# CONFIGURACIÓN
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from dotenv import load_dotenv
    env_path = os.path.join(BASE_DIR, '.env')
    load_dotenv(env_path)
    print(f"✅ Cargando .env desde: {env_path}")
except ImportError:
    print("⚠️ python-dotenv no instalado")

app = Flask(__name__)
CORS(app)

# Variables de entorno
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SECRET_KEY = os.getenv('SECRET_KEY', 'gymrock_super_secret_key_2026')
JWT_EXPIRATION = int(os.getenv('JWT_EXPIRATION', 7))
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'GymRock2026')
MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN', '')

# Conexión a Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Faltan SUPABASE_URL o SUPABASE_KEY")
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Conexión a Supabase establecida")
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        supabase = None

# Mercado Pago
if MP_ACCESS_TOKEN:
    print("✅ Mercado Pago configurado")
else:
    print("⚠️ Mercado Pago no configurado (MP_ACCESS_TOKEN vacío)")

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
            return jsonify({'error': 'Token inválido o expirado'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# =====================================================
# ENDPOINTS PÚBLICOS
# =====================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'GymRock API funcionando',
        'version': '2.1.0',
        'supabase': 'conectado' if supabase else 'no configurado',
        'mercadopago': 'configurado' if MP_ACCESS_TOKEN else 'no configurado',
        'timestamp': datetime.now(timezone.utc).isoformat()
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
        return jsonify({
            'status': 'success',
            'data': result.data if result.data else [],
            'total': len(result.data) if result.data else 0
        }), 200
    except Exception as e:
        print(f"Error en /api/gimnasios: {str(e)}")
        return jsonify({'error': 'Error al obtener gimnasios'}), 500

# =====================================================
# REGISTRO DE GIMNASIO (15 DÍAS DE PRUEBA)
# =====================================================

@app.route('/api/registro/gimnasio', methods=['POST'])
def registrar_gimnasio():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    
    try:
        data = request.get_json()
        
        required = ['nombre', 'email', 'password', 'estado', 'municipio']
        for field in required:
            if field not in data or not data[field]:
                return jsonify({'error': f'Campo {field} requerido'}), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        nombre = data['nombre'].strip()
        estado = data['estado'].strip()
        municipio = data['municipio'].strip()
        telefono = data.get('telefono', '').strip()
        direccion = data.get('direccion', '').strip()
        plan = data.get('plan', 'basico')
        
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'error': 'Correo electrónico inválido'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        existente = supabase.table('gimnasios').select('id').eq('email', email).execute()
        if existente.data and len(existente.data) > 0:
            return jsonify({'error': 'Este correo ya está registrado'}), 409
        
        hashed = hash_password(password)
        fecha_actual = datetime.now(timezone.utc)
        fecha_corte = fecha_actual + timedelta(days=15)
        
        nuevo_gimnasio = {
            'nombre': nombre,
            'email': email,
            'password_hash': hashed,
            'estado': estado,
            'municipio': municipio,
            'direccion': direccion,
            'telefono': telefono,
            'plan': plan,
            'licencia_fecha_corte': fecha_corte.isoformat(),
            'estado_licencia': 'activa',
            'visible_publico': True,
            'periodo_prueba': True,
            'fecha_registro': fecha_actual.isoformat(),
            'ip_registro': request.remote_addr or 'desconocida'
        }
        
        result = supabase.table('gimnasios').insert(nuevo_gimnasio).execute()
        
        if result.data:
            gym = result.data[0]
            token = generate_token(gym['id'], gym['email'], 'gimnasio')
            
            return jsonify({
                'status': 'success',
                'message': '🎁 ¡Gimnasio registrado con 15 días de prueba gratis!',
                'data': {
                    'id': gym['id'],
                    'nombre': gym['nombre'],
                    'email': gym['email'],
                    'token': token,
                    'dias_prueba': 15,
                    'fecha_corte': fecha_corte.strftime('%d/%m/%Y'),
                    'plan': plan,
                    'periodo_prueba': True
                }
            }), 201
        
        return jsonify({'error': 'Error al crear el registro'}), 500
        
    except Exception as e:
        print(f"❌ Error en registro gimnasio: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# =====================================================
# REGISTRO DE CLIENTE
# =====================================================

@app.route('/api/registro/cliente', methods=['POST'])
def registrar_cliente():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    
    try:
        data = request.get_json()
        
        required = ['nombre', 'email', 'password', 'estado', 'municipio']
        for field in required:
            if field not in data or not data[field]:
                return jsonify({'error': f'Campo {field} requerido'}), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'error': 'Correo electrónico inválido'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        existente = supabase.table('usuarios').select('id').eq('email', email).execute()
        if existente.data and len(existente.data) > 0:
            return jsonify({'error': 'Este correo ya está registrado'}), 409
        
        hashed = hash_password(password)
        
        nuevo_usuario = {
            'nombre': data['nombre'].strip(),
            'email': email,
            'password_hash': hashed,
            'estado': data['estado'].strip(),
            'municipio': data['municipio'].strip(),
            'telefono': data.get('telefono', '').strip(),
            'fecha_registro': datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase.table('usuarios').insert(nuevo_usuario).execute()
        
        if result.data:
            user = result.data[0]
            token = generate_token(user['id'], user['email'], 'cliente')
            
            return jsonify({
                'status': 'success',
                'message': '✅ Cliente registrado exitosamente',
                'data': {
                    'id': user['id'],
                    'nombre': user['nombre'],
                    'email': user['email'],
                    'token': token
                }
            }), 201
        
        return jsonify({'error': 'Error al crear el registro'}), 500
        
    except Exception as e:
        print(f"❌ Error en registro cliente: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# =====================================================
# LOGIN
# =====================================================

@app.route('/api/login', methods=['POST'])
def login():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        rol = data.get('rol', 'cliente')
        
        if not email or not password:
            return jsonify({'error': 'Email y contraseña requeridos'}), 400
        
        hashed = hash_password(password)
        
        if rol == 'gimnasio':
            result = supabase.table('gimnasios').select('*').eq('email', email).eq('password_hash', hashed).execute()
        else:
            result = supabase.table('usuarios').select('*').eq('email', email).eq('password_hash', hashed).execute()
        
        if not result.data or len(result.data) == 0:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        user = result.data[0]
        token = generate_token(user['id'], user['email'], rol)
        
        response_data = {
            'id': user['id'],
            'nombre': user['nombre'],
            'email': user['email'],
            'rol': rol,
            'token': token
        }
        
        if rol == 'gimnasio':
            response_data['plan'] = user.get('plan', 'basico')
            response_data['periodo_prueba'] = user.get('periodo_prueba', False)
            if user.get('licencia_fecha_corte'):
                fecha_corte = user['licencia_fecha_corte']
                if isinstance(fecha_corte, str):
                    response_data['fecha_corte'] = fecha_corte[:10]
                else:
                    response_data['fecha_corte'] = fecha_corte.strftime('%d/%m/%Y')
        
        return jsonify({
            'status': 'success',
            'message': 'Login exitoso',
            'data': response_data
        }), 200
        
    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# =====================================================
# SUPER ADMIN
# =====================================================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    
    try:
        data = request.get_json()
        usuario = data.get('usuario', '').strip()
        password = data.get('password', '')
        
        if not usuario or not password:
            return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
        
        hashed = hash_password(password)
        result = supabase.table('super_admin').select('*').eq('usuario', usuario).eq('password_hash', hashed).execute()
        
        if not result.data or len(result.data) == 0:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        admin = result.data[0]
        token = generate_token(admin['id'], admin['usuario'], 'super_admin')
        
        return jsonify({
            'status': 'success',
            'message': 'Login de administrador exitoso',
            'data': {
                'id': admin['id'],
                'usuario': admin['usuario'],
                'rol': 'super_admin',
                'token': token
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error en login admin: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/admin/verify', methods=['POST'])
def verify_admin():
    try:
        data = request.get_json()
        token = data.get('token', '')
        
        if token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                if payload['user']['rol'] == 'super_admin':
                    return jsonify({'status': 'success', 'valid': True, 'user': payload['user']}), 200
            except:
                pass
        
        if token == ADMIN_TOKEN:
            return jsonify({'status': 'success', 'valid': True, 'user': {'rol': 'super_admin'}}), 200
        
        return jsonify({'status': 'error', 'valid': False}), 401
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    
    try:
        token = request.args.get('token', '')
        
        valido = False
        if token == ADMIN_TOKEN:
            valido = True
        else:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                if payload['user']['rol'] == 'super_admin':
                    valido = True
            except:
                pass
        
        if not valido:
            return jsonify({'error': 'No autorizado'}), 401
        
        gimnasios = supabase.table('gimnasios').select('*').execute()
        usuarios = supabase.table('usuarios').select('*').execute()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_gimnasios': len(gimnasios.data) if gimnasios.data else 0,
                'total_usuarios': len(usuarios.data) if usuarios.data else 0,
                'gimnasios': gimnasios.data if gimnasios.data else []
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error en dashboard admin: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# =====================================================
# MERCADO PAGO - CREAR PREFERENCIA DE PAGO
# =====================================================

@app.route('/api/crear-preferencia', methods=['POST'])
def crear_preferencia():
    """Crear preferencia de pago en Mercado Pago"""
    if not MP_ACCESS_TOKEN:
        return jsonify({'error': 'Mercado Pago no configurado. Agrega MP_ACCESS_TOKEN en Render.'}), 500
    
    try:
        data = request.get_json()
        
        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        
        preference_data = {
            "items": [
                {
                    "title": data.get('descripcion', 'Suscripción GymRock'),
                    "quantity": 1,
                    "unit_price": float(data.get('monto', 0)),
                    "currency_id": "MXN"
                }
            ],
            "back_urls": {
                "success": f"{request.host_url}cliente/suscripciones.html?status=success",
                "failure": f"{request.host_url}cliente/suscripciones.html?status=failure",
                "pending": f"{request.host_url}cliente/suscripciones.html?status=pending"
            },
            "auto_return": "approved",
            "external_reference": data.get('gimnasio_id', ''),
            "payer": {
                "name": data.get('nombre', 'Cliente GymRock'),
                "email": data.get('email', 'cliente@gymrock.com')
            }
        }
        
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        return jsonify({
            'status': 'success',
            'preference_id': preference['id'],
            'init_point': preference['init_point']
        }), 200
        
    except Exception as e:
        print(f"❌ Error creando preferencia: {str(e)}")
        return jsonify({'error': f'Error al crear preferencia: {str(e)}'}), 500

# =====================================================
# SERVIR FRONTEND
# =====================================================

@app.route('/')
def serve_index():
    return send_from_directory('frontend_web', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend_web', path)

# =====================================================
# MANEJO DE ERRORES
# =====================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Ruta no encontrada'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Error interno del servidor'}), 500

# =====================================================
# INICIO
# =====================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 GymRock API v2.1 iniciada en http://localhost:{port}")
    print(f"📁 Frontend: frontend_web/")
    print(f"🗄️ Supabase: {'Conectado' if supabase else 'NO CONFIGURADO'}")
    print(f"💳 Mercado Pago: {'Configurado' if MP_ACCESS_TOKEN else 'NO CONFIGURADO'}")
    app.run(host='0.0.0.0', port=port, debug=False)