import os
import hashlib
import jwt
import mercadopago
import random
import string
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except:
    pass

app = Flask(__name__)
CORS(app)

# Configuración
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SECRET_KEY = os.getenv('SECRET_KEY', 'gymrock_super_secret_key_2026')
JWT_EXPIRATION = int(os.getenv('JWT_EXPIRATION', 7))
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'GymRock2026')
MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN', '')
BASE_URL = os.getenv('BASE_URL', 'https://gymrock.onrender.com')

# Conexión Supabase
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase conectado")
    except Exception as e:
        print(f"❌ Error Supabase: {e}")

# Funciones helper
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def generate_token(uid, email, rol):
    payload = {
        'user': {'id': uid, 'email': email, 'rol': rol},
        'exp': datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# ================================================
# ENDPOINTS
# ================================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'message': 'GymRock API funcionando',
        'version': '4.0.0'
    }), 200

# ---------- GIMNASIOS ----------
@app.route('/api/gimnasios', methods=['GET'])
def listar_gimnasios():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        result = supabase.table('gimnasios').select('*').eq('visible_publico', True).eq('estado_licencia', 'activa').execute()
        return jsonify({
            'status': 'success',
            'data': result.data if result.data else [],
            'total': len(result.data) if result.data else 0
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------- REGISTRO GIMNASIO ----------
@app.route('/api/registro/gimnasio', methods=['POST'])
def registrar_gimnasio():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        d = request.get_json()
        for campo in ['nombre', 'email', 'password', 'estado', 'municipio']:
            if not d.get(campo):
                return jsonify({'error': f'Campo {campo} requerido'}), 400
        
        email = d['email'].strip().lower()
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'error': 'Email inválido'}), 400
        if len(d['password']) < 6:
            return jsonify({'error': 'Contraseña muy corta (mín 6)'}), 400
        
        existe = supabase.table('gimnasios').select('id').eq('email', email).execute()
        if existe.data:
            return jsonify({'error': 'Este correo ya está registrado'}), 409
        
        ahora = datetime.now(timezone.utc)
        nuevo = {
            'nombre': d['nombre'].strip(),
            'email': email,
            'password_hash': hash_password(d['password']),
            'estado': d['estado'].strip(),
            'municipio': d['municipio'].strip(),
            'direccion': d.get('direccion', ''),
            'telefono': d.get('telefono', ''),
            'plan': d.get('plan', 'basico'),
            'licencia_fecha_corte': (ahora + timedelta(days=15)).isoformat(),
            'estado_licencia': 'activa',
            'visible_publico': True,
            'periodo_prueba': True,
            'fecha_registro': ahora.isoformat()
        }
        
        result = supabase.table('gimnasios').insert(nuevo).execute()
        if result.data:
            g = result.data[0]
            token = generate_token(g['id'], g['email'], 'gimnasio')
            return jsonify({
                'status': 'success',
                'message': 'Gimnasio registrado con 15 días de prueba',
                'data': {
                    'id': g['id'],
                    'nombre': g['nombre'],
                    'email': g['email'],
                    'token': token,
                    'dias_prueba': 15,
                    'fecha_corte': (ahora + timedelta(days=15)).strftime('%d/%m/%Y'),
                    'plan': d.get('plan', 'basico'),
                    'periodo_prueba': True
                }
            }), 201
        return jsonify({'error': 'Error al crear registro'}), 500
    except Exception as e:
        print(f"Error registro gimnasio: {e}")
        return jsonify({'error': 'Error interno'}), 500

# ---------- REGISTRO CLIENTE ----------
@app.route('/api/registro/cliente', methods=['POST'])
def registrar_cliente():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        d = request.get_json()
        for campo in ['nombre', 'email', 'password', 'estado', 'municipio']:
            if not d.get(campo):
                return jsonify({'error': f'Campo {campo} requerido'}), 400
        
        email = d['email'].strip().lower()
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'error': 'Email inválido'}), 400
        if len(d['password']) < 6:
            return jsonify({'error': 'Contraseña muy corta (mín 6)'}), 400
        
        existe = supabase.table('usuarios').select('id').eq('email', email).execute()
        if existe.data:
            return jsonify({'error': 'Este correo ya está registrado'}), 409
        
        nuevo = {
            'nombre': d['nombre'].strip(),
            'email': email,
            'password_hash': hash_password(d['password']),
            'estado': d['estado'].strip(),
            'municipio': d['municipio'].strip(),
            'telefono': d.get('telefono', ''),
            'fecha_registro': datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase.table('usuarios').insert(nuevo).execute()
        if result.data:
            u = result.data[0]
            token = generate_token(u['id'], u['email'], 'cliente')
            return jsonify({
                'status': 'success',
                'message': 'Cliente registrado',
                'data': {
                    'id': u['id'],
                    'nombre': u['nombre'],
                    'email': u['email'],
                    'token': token
                }
            }), 201
        return jsonify({'error': 'Error al crear registro'}), 500
    except Exception as e:
        print(f"Error registro cliente: {e}")
        return jsonify({'error': str(e)}), 500

# ---------- LOGIN ----------
@app.route('/api/login', methods=['POST'])
def login():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        d = request.get_json()
        email = d.get('email', '').strip().lower()
        password = d.get('password', '')
        rol = d.get('rol', 'cliente')
        
        if not email or not password:
            return jsonify({'error': 'Email y contraseña requeridos'}), 400
        
        hashed = hash_password(password)
        tabla = 'gimnasios' if rol == 'gimnasio' else 'usuarios'
        result = supabase.table(tabla).select('*').eq('email', email).eq('password_hash', hashed).execute()
        
        if not result.data:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        u = result.data[0]
        token = generate_token(u['id'], u['email'], rol)
        resp = {
            'id': u['id'],
            'nombre': u['nombre'],
            'email': u['email'],
            'rol': rol,
            'token': token
        }
        
        if rol == 'gimnasio':
            resp['plan'] = u.get('plan', 'basico')
            resp['periodo_prueba'] = u.get('periodo_prueba', False)
            fc = u.get('licencia_fecha_corte')
            if fc:
                resp['fecha_corte'] = str(fc)[:10]
        
        return jsonify({'status': 'success', 'message': 'Login exitoso', 'data': resp}), 200
    except Exception as e:
        print(f"Error login: {e}")
        return jsonify({'error': 'Error interno'}), 500

# ---------- ADMIN ----------
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        d = request.get_json()
        usuario = d.get('usuario', '').strip()
        password = d.get('password', '')
        
        if not usuario or not password:
            return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
        
        hashed = hash_password(password)
        result = supabase.table('super_admin').select('*').eq('usuario', usuario).eq('password_hash', hashed).execute()
        
        if not result.data:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        a = result.data[0]
        token = generate_token(a['id'], a['usuario'], 'super_admin')
        return jsonify({
            'status': 'success',
            'data': {
                'id': a['id'],
                'usuario': a['usuario'],
                'rol': 'super_admin',
                'token': token
            }
        }), 200
    except Exception as e:
        print(f"Error admin login: {e}")
        return jsonify({'error': 'Error interno'}), 500

@app.route('/api/admin/verify', methods=['POST'])
def admin_verify():
    try:
        token = request.get_json().get('token', '')
        if token == ADMIN_TOKEN:
            return jsonify({'valid': True}), 200
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            if payload['user']['rol'] == 'super_admin':
                return jsonify({'valid': True}), 200
        except:
            pass
        return jsonify({'valid': False}), 401
    except:
        return jsonify({'valid': False}), 401

@app.route('/api/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        token = request.args.get('token', '')
        ok = (token == ADMIN_TOKEN)
        if not ok:
            try:
                ok = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])['user']['rol'] == 'super_admin'
            except:
                pass
        if not ok:
            return jsonify({'error': 'No autorizado'}), 401
        
        gimnasios = supabase.table('gimnasios').select('*').execute()
        usuarios = supabase.table('usuarios').select('*').execute()
        return jsonify({
            'status': 'success',
            'data': {
                'total_gimnasios': len(gimnasios.data or []),
                'total_usuarios': len(usuarios.data or []),
                'gimnasios': gimnasios.data or []
            }
        }), 200
    except Exception as e:
        print(f"Error dashboard: {e}")
        return jsonify({'error': 'Error interno'}), 500

# ---------- ENTRENADORES ----------
@app.route('/api/entrenador/login', methods=['POST'])
def entrenador_login():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        d = request.get_json()
        codigo = d.get('codigo_acceso', '').strip().upper()
        if not codigo:
            return jsonify({'error': 'Código requerido'}), 400
        
        result = supabase.table('entrenadores').select('*').eq('codigo_acceso', codigo).eq('activo', True).execute()
        if not result.data:
            return jsonify({'error': 'Código inválido'}), 401
        
        e = result.data[0]
        token = generate_token(e['id'], e['email'], 'entrenador')
        return jsonify({
            'status': 'success',
            'data': {
                'id': e['id'],
                'nombre': e['nombre'],
                'email': e['email'],
                'codigo_acceso': e['codigo_acceso'],
                'token': token,
                'rol': 'entrenador'
            }
        }), 200
    except Exception as e:
        print(f"Error entrenador login: {e}")
        return jsonify({'error': 'Error interno'}), 500

@app.route('/api/gimnasio/<gym_id>/entrenadores', methods=['GET'])
def entrenadores_gimnasio(gym_id):
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        result = supabase.table('entrenadores').select('*').execute()
        all_data = result.data if result.data else []; data = [e for e in all_data if str(e.get("gimnasio_id","")) == gym_id]
        return jsonify({'status': 'success', 'data': data}), 200
    except:
        try:
            result = supabase.table('entrenadores').select('*').execute()
            all_all_data = result.data if result.data else []; data = [e for e in all_data if str(e.get("gimnasio_id","")) == gym_id]
            data = [e for e in all_data if str(e.get('gimnasio_id','')) == str(gym_id)]
            return jsonify({'status': 'success', 'data': data}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# ---------- CERTIFICACIONES ----------
@app.route('/api/gimnasio/<gym_id>/certificaciones', methods=['GET'])
def certificaciones_gimnasio(gym_id):
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        result = supabase.table('certificaciones').select('*').eq('gimnasio_id', gym_id).order('fecha_envio', desc=True).execute()
        return jsonify({
            'status': 'success',
            'data': result.data if result.data else []
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/certificacion/resultado', methods=['POST'])
def guardar_resultado_cert():
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        d = request.get_json()
        supabase.table('certificaciones').insert({
            'gimnasio_id': d.get('gimnasio_id', ''),
            'nombre_solicitante': d.get('nombre', ''),
            'email_solicitante': d.get('email', ''),
            'puntuacion': int(d.get('puntuacion', 0)),
            'total_preguntas': int(d.get('total', 0)),
            'clase': d.get('clase', ''),
            'estado': 'pendiente',
            'fecha_envio': datetime.now(timezone.utc).isoformat()
        }).execute()
        return jsonify({'status': 'success', 'message': 'Resultado enviado al gimnasio'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/certificacion/<cert_id>/revisar', methods=['POST'])
def revisar_certificacion(cert_id):
    if not supabase:
        return jsonify({'error': 'Servicio no disponible'}), 500
    try:
        d = request.get_json()
        estado = d.get('estado', 'aprobado')
        
        supabase.table('certificaciones').update({
            'estado': estado,
            'fecha_revision': datetime.now(timezone.utc).isoformat()
        }).eq('id', cert_id).execute()
        
        if estado == 'aprobado':
            cert = supabase.table('certificaciones').select('*').eq('id', cert_id).execute()
            if cert.data:
                c = cert.data[0]
                codigo = 'GYM-ENT-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table('entrenadores').insert({
                    'gimnasio_id': c['gimnasio_id'],
                    'nombre': c['nombre_solicitante'],
                    'email': c['email_solicitante'],
                    'codigo_acceso': codigo,
                    'especialidad': 'Entrenador Personal',
                    'certificado': True,
                    'puntuacion_test': c['puntuacion'],
                    'activo': True,
                    'precio_sesion': 350
                }).execute()
                return jsonify({'status': 'success', 'message': 'Entrenador aprobado', 'codigo': codigo}), 200
        
        return jsonify({'status': 'success', 'message': f'Certificación {estado}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------- MERCADO PAGO ----------
@app.route('/api/crear-preferencia', methods=['POST'])
def crear_preferencia():
    if not MP_ACCESS_TOKEN:
        return jsonify({'error': 'Mercado Pago no configurado'}), 500
    try:
        d = request.get_json()
        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        preference_data = {
            "items": [{
                "title": d.get('descripcion', 'Suscripción GymRock'),
                "quantity": 1,
                "unit_price": float(d.get('monto', 0)),
                "currency_id": "MXN"
            }],
            "back_urls": {
                "success": f"{BASE_URL}/cliente/suscripciones.html?status=success",
                "failure": f"{BASE_URL}/cliente/suscripciones.html?status=failure"
            },
            "auto_return": "approved"
        }
        result = sdk.preference().create(preference_data)
        return jsonify({
            'status': 'success',
            'init_point': result['response']['init_point']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================================
# FRONTEND
# ================================================
@app.route('/')
def serve_index():
    return send_from_directory('frontend_web', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    full_path = os.path.join('frontend_web', path)
    if os.path.isfile(full_path):
        return send_from_directory('frontend_web', path)
    return send_from_directory('frontend_web', 'index.html')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 GymRock API v4.0 iniciada en puerto {port}")
    app.run(host='0.0.0.0', port=port)

