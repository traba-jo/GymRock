"""
GYMROCK - Backend Principal
app.py - Servidor Flask con autenticación y endpoints completos
"""

# =====================================================
# 1. IMPORTACIONES
# =====================================================
import os
import json
import hashlib
import jwt
import datetime
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv

# Importar módulos propios
from database import db
from mp_integration import mp
from entrenador_test import test_entrenador

# Cargar variables de entorno
load_dotenv()

# =====================================================
# 2. CONFIGURACIÓN
# =====================================================
app = Flask(__name__)
CORS(app)  # Permitir peticiones desde cualquier origen (desarrollo)

# Configuración de JWT
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gymrock_secret_key_2026')
app.config['JWT_EXPIRATION'] = int(os.getenv('JWT_EXPIRATION', 7))

# Token de Super Admin (desde .env)
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'GymRock2026')

# =====================================================
# 3. DECORADORES DE AUTENTICACIÓN
# =====================================================

def token_required(f):
    """Decorador para proteger rutas que requieren autenticación"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Obtener token del header Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token requerido', 'status': 401}), 401
        
        try:
            # Decodificar token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado', 'status': 401}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido', 'status': 401}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# =====================================================
# 4. FUNCIONES AUXILIARES
# =====================================================

def hash_password(password):
    """Hashear contraseña usando SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(user_id, email, rol):
    """Generar JWT token"""
    payload = {
        'user': {
            'id': user_id,
            'email': email,
            'rol': rol
        },
        'exp': datetime.utcnow() + timedelta(days=app.config['JWT_EXPIRATION'])
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def validate_email(email):
    """Validación básica de email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# =====================================================
# 5. ENDPOINTS DE AUTENTICACIÓN
# =====================================================

@app.route('/api/registro/gimnasio', methods=['POST'])
def registrar_gimnasio():
    """
    Registro de un nuevo gimnasio
    Body: { nombre, email, password, estado, municipio, direccion, telefono, plan }
    """
    try:
        data = request.get_json()
        
        # Validaciones básicas
        required_fields = ['nombre', 'email', 'password', 'estado', 'municipio']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo {field} requerido', 'status': 400}), 400
        
        if not validate_email(data['email']):
            return jsonify({'error': 'Email inválido', 'status': 400}), 400
        
        # Verificar si el gimnasio ya existe
        existing = db.supabase.table('gimnasios')\
            .select('id')\
            .eq('email', data['email'])\
            .execute()
        
        if existing.data:
            return jsonify({'error': 'Email ya registrado', 'status': 409}), 409
        
        # Crear gimnasio
        hashed_password = hash_password(data['password'])
        fecha_corte = datetime.now() + timedelta(days=30)
        
        new_gym = {
            'nombre': data['nombre'],
            'email': data['email'],
            'password_hash': hashed_password,
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
        
        result = db.supabase.table('gimnasios')\
            .insert(new_gym)\
            .execute()
        
        if result.data:
            gym_data = result.data[0]
            token = generate_token(gym_data['id'], gym_data['email'], 'gimnasio')
            
            return jsonify({
                'status': 'success',
                'message': 'Gimnasio registrado exitosamente',
                'data': {
                    'id': gym_data['id'],
                    'nombre': gym_data['nombre'],
                    'email': gym_data['email'],
                    'plan': gym_data['plan'],
                    'licencia_fecha_corte': gym_data['licencia_fecha_corte'],
                    'token': token
                }
            }), 201
        else:
            return jsonify({'error': 'Error al registrar gimnasio', 'status': 500}), 500
            
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/api/registro/cliente', methods=['POST'])
def registrar_cliente():
    """
    Registro de un nuevo cliente
    Body: { nombre, email, password, estado, municipio, telefono }
    """
    try:
        data = request.get_json()
        
        required_fields = ['nombre', 'email', 'password', 'estado', 'municipio']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo {field} requerido', 'status': 400}), 400
        
        if not validate_email(data['email']):
            return jsonify({'error': 'Email inválido', 'status': 400}), 400
        
        existing = db.supabase.table('usuarios')\
            .select('id')\
            .eq('email', data['email'])\
            .execute()
        
        if existing.data:
            return jsonify({'error': 'Email ya registrado', 'status': 409}), 409
        
        hashed_password = hash_password(data['password'])
        
        new_user = {
            'nombre': data['nombre'],
            'email': data['email'],
            'password_hash': hashed_password,
            'estado': data['estado'],
            'municipio': data['municipio'],
            'telefono': data.get('telefono', ''),
            'fecha_registro': datetime.now().isoformat()
        }
        
        result = db.supabase.table('usuarios')\
            .insert(new_user)\
            .execute()
        
        if result.data:
            user_data = result.data[0]
            token = generate_token(user_data['id'], user_data['email'], 'cliente')
            
            return jsonify({
                'status': 'success',
                'message': 'Cliente registrado exitosamente',
                'data': {
                    'id': user_data['id'],
                    'nombre': user_data['nombre'],
                    'email': user_data['email'],
                    'token': token
                }
            }), 201
        else:
            return jsonify({'error': 'Error al registrar cliente', 'status': 500}), 500
            
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """
    Login para gimnasios y clientes
    Body: { email, password, rol (gimnasio/cliente) }
    """
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email y password requeridos', 'status': 400}), 400
        
        email = data['email']
        password = hash_password(data['password'])
        rol = data.get('rol', 'cliente')
        
        if rol == 'gimnasio':
            result = db.supabase.table('gimnasios')\
                .select('*')\
                .eq('email', email)\
                .eq('password_hash', password)\
                .execute()
            id_field = 'id'
        else:
            result = db.supabase.table('usuarios')\
                .select('*')\
                .eq('email', email)\
                .eq('password_hash', password)\
                .execute()
            id_field = 'id'
        
        if not result.data:
            return jsonify({'error': 'Credenciales inválidas', 'status': 401}), 401
        
        user_data = result.data[0]
        token = generate_token(user_data[id_field], user_data['email'], rol)
        
        response_data = {
            'status': 'success',
            'message': 'Login exitoso',
            'data': {
                'id': user_data[id_field],
                'nombre': user_data['nombre'],
                'email': user_data['email'],
                'rol': rol,
                'token': token
            }
        }
        
        if rol == 'gimnasio':
            response_data['data']['licencia'] = {
                'fecha_corte': user_data.get('licencia_fecha_corte'),
                'estado': user_data.get('estado_licencia', 'activa'),
                'plan': user_data.get('plan', 'basico')
            }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

# =====================================================
# 6. ENDPOINTS PROTEGIDOS
# =====================================================

@app.route('/api/perfil', methods=['GET'])
@token_required
def obtener_perfil(current_user):
    """Obtener perfil del usuario autenticado"""
    try:
        user_id = current_user['id']
        rol = current_user['rol']
        
        if rol == 'gimnasio':
            result = db.supabase.table('gimnasios')\
                .select('id, nombre, email, estado, municipio, direccion, telefono, plan, licencia_fecha_corte, estado_licencia, visible_publico')\
                .eq('id', user_id)\
                .execute()
        else:
            result = db.supabase.table('usuarios')\
                .select('id, nombre, email, estado, municipio, telefono')\
                .eq('id', user_id)\
                .execute()
        
        if not result.data:
            return jsonify({'error': 'Usuario no encontrado', 'status': 404}), 404
        
        return jsonify({
            'status': 'success',
            'data': result.data[0]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

# =====================================================
# 7. ENDPOINTS PÚBLICOS
# =====================================================

@app.route('/api/gimnasios', methods=['GET'])
def listar_gimnasios():
    """Listar gimnasios públicos"""
    try:
        query = db.supabase.table('gimnasios')\
            .select('*')\
            .eq('visible_publico', True)\
            .eq('estado_licencia', 'activa')
        
        estado = request.args.get('estado')
        municipio = request.args.get('municipio')
        
        if estado:
            query = query.eq('estado', estado)
        if municipio:
            query = query.eq('municipio', municipio)
        
        result = query.execute()
        
        return jsonify({
            'status': 'success',
            'data': result.data,
            'total': len(result.data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/api/gimnasio/<gimnasio_id>', methods=['GET'])
def obtener_gimnasio(gimnasio_id):
    """Obtener detalles de un gimnasio"""
    try:
        result = db.supabase.table('gimnasios')\
            .select('*')\
            .eq('id', gimnasio_id)\
            .eq('visible_publico', True)\
            .eq('estado_licencia', 'activa')\
            .execute()
        
        if not result.data:
            return jsonify({'error': 'Gimnasio no encontrado', 'status': 404}), 404
        
        gym = result.data[0]
        
        entrenadores = db.supabase.table('entrenadores')\
            .select('id, nombre, especialidad, certificado_cc, foto')\
            .eq('gimnasio_id', gimnasio_id)\
            .execute()
        
        gym['entrenadores'] = entrenadores.data if entrenadores.data else []
        
        return jsonify({
            'status': 'success',
            'data': gym
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

# =====================================================
# 8. ENDPOINTS DE SUPER ADMIN
# =====================================================

@app.route('/api/admin/verify-token', methods=['POST'])
def verificar_token_admin():
    """Verificar token de Super Admin"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'status': 'error', 'message': 'Token requerido'}), 400
        
        if token == ADMIN_TOKEN:
            return jsonify({'status': 'success', 'valid': True}), 200
        else:
            return jsonify({'status': 'error', 'valid': False}), 401
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/dashboard', methods=['GET'])
def admin_dashboard():
    """Obtener métricas para Super Admin"""
    try:
        token = request.args.get('token')
        
        if token != ADMIN_TOKEN:
            return jsonify({'status': 'error', 'message': 'Token inválido'}), 401
        
        gimnasios = db.supabase.table('gimnasios').select('*').execute()
        usuarios = db.supabase.table('usuarios').select('*').execute()
        entrenadores = db.supabase.table('entrenadores').select('*').execute()
        suscripciones = db.supabase.table('suscripciones').select('*').eq('activa', True).execute()
        
        ingresos_totales = 0
        for g in gimnasios.data:
            if g.get('plan') == 'premium':
                ingresos_totales += 1200
            elif g.get('plan') == 'pro':
                ingresos_totales += 800
            else:
                ingresos_totales += 500
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_gimnasios': len(gimnasios.data),
                'total_usuarios': len(usuarios.data),
                'total_entrenadores': len(entrenadores.data),
                'suscripciones_activas': len(suscripciones.data),
                'ingresos_totales': ingresos_totales,
                'gimnasios': gimnasios.data,
                'suscripciones_recientes': suscripciones.data[:5]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# =====================================================
# 9. ENDPOINTS DE MERCADO PAGO
# =====================================================

@app.route('/api/crear-pago', methods=['POST'])
@token_required
def crear_pago(current_user):
    """Crear preferencia de pago"""
    try:
        data = request.get_json()
        suscripcion_id = data.get('suscripcion_id')
        monto = data.get('monto')
        concepto = data.get('concepto')
        
        user_result = db.supabase.table('usuarios')\
            .select('email, nombre')\
            .eq('id', current_user['id'])\
            .execute()
        
        if not user_result.data:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        user = user_result.data[0]
        
        resultado = mp.crear_preferencia_suscripcion(
            suscripcion_id=suscripcion_id,
            monto=monto,
            concepto=concepto,
            usuario_email=user['email'],
            usuario_nombre=user['nombre']
        )
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/api/webhook', methods=['POST'])
def webhook_mp():
    """Webhook de Mercado Pago"""
    try:
        data = request.get_json()
        resultado = mp.procesar_webhook(data)
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

# =====================================================
# 10. ENDPOINTS DE ENTRENADORES
# =====================================================

@app.route('/api/entrenadores/preguntas', methods=['GET'])
def obtener_preguntas_test():
    """Obtener preguntas del test"""
    try:
        preguntas = test_entrenador.obtener_todas_preguntas()
        return jsonify({
            'status': 'success',
            'data': preguntas
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/api/entrenadores/evaluar', methods=['POST'])
def evaluar_test():
    """Evaluar respuestas del test"""
    try:
        data = request.get_json()
        respuestas = data.get('respuestas', [])
        resultado = test_entrenador.evaluar_test(respuestas)
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/api/entrenadores/registrar', methods=['POST'])
@token_required
def registrar_entrenador(current_user):
    """Registrar entrenador (solo gimnasios)"""
    try:
        if current_user['rol'] != 'gimnasio':
            return jsonify({'error': 'Solo gimnasios pueden registrar entrenadores'}), 403
        
        data = request.get_json()
        gimnasio_id = current_user['id']
        
        resultado = test_entrenador.registrar_entrenador(
            nombre=data.get('nombre'),
            email=data.get('email'),
            telefono=data.get('telefono'),
            gimnasio_id=gimnasio_id,
            especialidad=data.get('especialidad', 'entrenador')
        )
        
        return jsonify(resultado), 201 if resultado['status'] == 'success' else 400
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

# =====================================================
# 11. ENDPOINTS DE PRUEBA
# =====================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check del servidor"""
    return jsonify({
        'status': 'ok',
        'message': 'GymRock API funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.2',
        'dependencies': {
            'flask': True,
            'jwt': True,
            'supabase': True,
            'dotenv': True
        }
    }), 200

@app.route('/api/test/db', methods=['GET'])
def test_db_connection():
    """Probar conexión con Supabase"""
    try:
        result = db.supabase.table('gimnasios')\
            .select('id', count='exact')\
            .limit(1)\
            .execute()
        
        return jsonify({
            'status': 'ok',
            'message': 'Conexión a base de datos exitosa',
            'total_registros': result.count if result.count else 0
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

# =====================================================
# 12. MANEJO DE ERRORES
# =====================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Ruta no encontrada',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Error interno del servidor',
        'status': 500
    }), 500

# =====================================================
# 13. INICIO DEL SERVIDOR
# =====================================================

if __name__ == '__main__':
    print("="*50)
    print("🏋️ GYMROCK - Backend Server v1.0.2")
    print("="*50)
    print(f"📡 Puerto: 5000")
    print(f"🌐 URL: http://localhost:5000")
    print("-"*50)
    print("📦 Dependencias:")
    print("   Flask: ✅")
    print("   JWT:   ✅")
    print("   Supabase: ✅")
    print("   Dotenv: ✅")
    print("-"*50)
    print("📋 Endpoints disponibles:")
    print("  POST /api/registro/gimnasio")
    print("  POST /api/registro/cliente")
    print("  POST /api/login")
    print("  GET  /api/perfil (requiere token)")
    print("  GET  /api/gimnasios")
    print("  GET  /api/gimnasio/<id>")
    print("  POST /api/admin/verify-token")
    print("  GET  /api/admin/dashboard?token=...")
    print("  POST /api/crear-pago (requiere token)")
    print("  POST /api/webhook")
    print("  GET  /api/entrenadores/preguntas")
    print("  POST /api/entrenadores/evaluar")
    print("  POST /api/entrenadores/registrar (requiere token)")
    print("  GET  /api/health")
    print("  GET  /api/test/db")
    print("="*50)
    print("🚀 Servidor iniciado...")
    app.run(debug=True, host='0.0.0.0', port=5000)