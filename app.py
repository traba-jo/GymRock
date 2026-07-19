import os, hashlib, jwt, mercadopago
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except: pass

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SECRET_KEY = os.getenv('SECRET_KEY', 'gymrock_super_secret_key_2026')
JWT_EXPIRATION = int(os.getenv('JWT_EXPIRATION', 7))
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'GymRock2026')
MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN', '')
BASE_URL = os.getenv('BASE_URL', 'https://gymrock.onrender.com')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
print("✅ Supabase:", "OK" if supabase else "NO")
print("💳 MP:", "OK" if MP_ACCESS_TOKEN else "NO")

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def generate_token(uid, email, rol):
    return jwt.encode({'user':{'id':uid,'email':email,'rol':rol},'exp':datetime.now(timezone.utc)+timedelta(days=JWT_EXPIRATION)}, SECRET_KEY, algorithm='HS256')

# API
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status':'ok','message':'GymRock API','version':'2.3.0','supabase':'ok' if supabase else 'no','mp':'ok' if MP_ACCESS_TOKEN else 'no'}), 200

@app.route('/api/gimnasios', methods=['GET'])
def gimnasios():
    if not supabase: return jsonify({'error':'No DB'}), 500
    r = supabase.table('gimnasios').select('*').eq('visible_publico',True).eq('estado_licencia','activa').execute()
    return jsonify({'status':'success','data':r.data or [],'total':len(r.data) if r.data else 0}), 200

@app.route('/api/registro/gimnasio', methods=['POST'])
def reg_gym():
    if not supabase: return jsonify({'error':'No DB'}), 500
    d = request.get_json()
    for f in ['nombre','email','password','estado','municipio']:
        if not d.get(f): return jsonify({'error':f'Falta {f}'}), 400
    email = d['email'].strip().lower()
    if '@' not in email or '.' not in email: return jsonify({'error':'Email invalido'}), 400
    if len(d['password'])<6: return jsonify({'error':'Contraseña corta'}), 400
    if supabase.table('gimnasios').select('id').eq('email',email).execute().data: return jsonify({'error':'Ya existe'}), 409
    h = hash_password(d['password'])
    ahora = datetime.now(timezone.utc)
    nuevo = {'nombre':d['nombre'].strip(),'email':email,'password_hash':h,'estado':d['estado'].strip(),'municipio':d['municipio'].strip(),'direccion':d.get('direccion','').strip(),'telefono':d.get('telefono','').strip(),'plan':d.get('plan','basico'),'licencia_fecha_corte':(ahora+timedelta(days=15)).isoformat(),'estado_licencia':'activa','visible_publico':True,'periodo_prueba':True,'fecha_registro':ahora.isoformat()}
    r = supabase.table('gimnasios').insert(nuevo).execute()
    if r.data:
        g = r.data[0]
        return jsonify({'status':'success','data':{'id':g['id'],'nombre':g['nombre'],'email':g['email'],'token':generate_token(g['id'],g['email'],'gimnasio'),'dias_prueba':15,'fecha_corte':(ahora+timedelta(days=15)).strftime('%d/%m/%Y')}}), 201
    return jsonify({'error':'Error'}), 500

@app.route('/api/registro/cliente', methods=['POST'])
def reg_cli():
    if not supabase: return jsonify({'error':'No DB'}), 500
    d = request.get_json()
    for f in ['nombre','email','password','estado','municipio']:
        if not d.get(f): return jsonify({'error':f'Falta {f}'}), 400
    email = d['email'].strip().lower()
    if '@' not in email or '.' not in email: return jsonify({'error':'Email invalido'}), 400
    if len(d['password'])<6: return jsonify({'error':'Contraseña corta'}), 400
    if supabase.table('usuarios').select('id').eq('email',email).execute().data: return jsonify({'error':'Ya existe'}), 409
    h = hash_password(d['password'])
    nuevo = {'nombre':d['nombre'].strip(),'email':email,'password_hash':h,'estado':d['estado'].strip(),'municipio':d['municipio'].strip(),'telefono':d.get('telefono','').strip(),'fecha_registro':datetime.now(timezone.utc).isoformat()}
    r = supabase.table('usuarios').insert(nuevo).execute()
    if r.data:
        u = r.data[0]
        return jsonify({'status':'success','data':{'id':u['id'],'nombre':u['nombre'],'email':u['email'],'token':generate_token(u['id'],u['email'],'cliente')}}), 201
    return jsonify({'error':'Error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    if not supabase: return jsonify({'error':'No DB'}), 500
    d = request.get_json()
    email = d.get('email','').strip().lower()
    pw = d.get('password','')
    rol = d.get('rol','cliente')
    if not email or not pw: return jsonify({'error':'Faltan datos'}), 400
    h = hash_password(pw)
    t = 'gimnasios' if rol=='gimnasio' else 'usuarios'
    r = supabase.table(t).select('*').eq('email',email).eq('password_hash',h).execute()
    if not r.data: return jsonify({'error':'Credenciales invalidas'}), 401
    u = r.data[0]
    resp = {'id':u['id'],'nombre':u['nombre'],'email':u['email'],'rol':rol,'token':generate_token(u['id'],u['email'],rol)}
    if rol=='gimnasio':
        resp['plan'] = u.get('plan','basico')
        resp['periodo_prueba'] = u.get('periodo_prueba',False)
        if u.get('licencia_fecha_corte'): resp['fecha_corte'] = u['licencia_fecha_corte'][:10]
    return jsonify({'status':'success','data':resp}), 200

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    if not supabase: return jsonify({'error':'No DB'}), 500
    d = request.get_json()
    u = d.get('usuario','').strip()
    p = d.get('password','')
    if not u or not p: return jsonify({'error':'Faltan datos'}), 400
    r = supabase.table('super_admin').select('*').eq('usuario',u).eq('password_hash',hash_password(p)).execute()
    if not r.data: return jsonify({'error':'Invalido'}), 401
    a = r.data[0]
    return jsonify({'status':'success','data':{'id':a['id'],'usuario':a['usuario'],'rol':'super_admin','token':generate_token(a['id'],a['usuario'],'super_admin')}}), 200

@app.route('/api/admin/verify', methods=['POST'])
def verify():
    t = request.get_json().get('token','')
    if t==ADMIN_TOKEN: return jsonify({'valid':True}), 200
    try:
        if jwt.decode(t,SECRET_KEY,algorithms=['HS256'])['user']['rol']=='super_admin': return jsonify({'valid':True}), 200
    except: pass
    return jsonify({'valid':False}), 401

@app.route('/api/admin/dashboard', methods=['GET'])
def dashboard():
    if not supabase: return jsonify({'error':'No DB'}), 500
    t = request.args.get('token','')
    ok = t==ADMIN_TOKEN
    if not ok:
        try: ok = jwt.decode(t,SECRET_KEY,algorithms=['HS256'])['user']['rol']=='super_admin'
        except: pass
    if not ok: return jsonify({'error':'No autorizado'}), 401
    g = supabase.table('gimnasios').select('*').execute()
    u = supabase.table('usuarios').select('*').execute()
    return jsonify({'status':'success','data':{'total_gimnasios':len(g.data or []),'total_usuarios':len(u.data or []),'gimnasios':g.data or []}}), 200

@app.route('/api/crear-preferencia', methods=['POST'])
def preferencia():
    if not MP_ACCESS_TOKEN: return jsonify({'error':'No MP'}), 500
    d = request.get_json()
    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
    pref = {"items":[{"title":d.get('descripcion','Suscripcion'),"quantity":1,"unit_price":float(d.get('monto',0)),"currency_id":"MXN"}],"back_urls":{"success":f"{BASE_URL}/cliente/suscripciones.html?status=success","failure":f"{BASE_URL}/cliente/suscripciones.html?status=failure","pending":f"{BASE_URL}/cliente/suscripciones.html?status=pending"},"auto_return":"approved"}
    r = sdk.preference().create(pref)
    return jsonify({'status':'success','init_point':r['response']['init_point']}), 200


@app.route('/api/gimnasio/<gym_id>/banco', methods=['GET'])
def get_banco_gimnasio(gym_id):
    if not supabase: return jsonify({'error':'No DB'}), 500
    try:
        r = supabase.table('gimnasios').select('banco_nombre,banco_titular,banco_cuenta').eq('id', gym_id).execute()
        if r.data and len(r.data) > 0:
            g = r.data[0]
            cuenta = g.get('banco_cuenta','')
            return jsonify({'status':'success','data':{'banco':g.get('banco_nombre',''),'titular':g.get('banco_titular',''),'cuenta':cuenta[-4:] if cuenta else '****'}}), 200
        return jsonify({'status':'error','message':'Gimnasio no encontrado'}), 404
    except Exception as e:
        return jsonify({'error':str(e)}), 500



@app.route('/api/entrenador/login', methods=['POST'])
def entrenador_login():
    if not supabase: return jsonify({'error':'No DB'}), 500
    try:
        d=request.get_json()
        codigo=d.get('codigo_acceso','').strip().upper()
        if not codigo: return jsonify({'error':'Codigo requerido'}), 400
        r=supabase.table('entrenadores').select('*').eq('codigo_acceso',codigo).eq('activo',True).execute()
        if not r.data: return jsonify({'error':'Codigo invalido'}), 401
        e=r.data[0]
        token=generate_token(e['id'],e['email'],'entrenador')
        return jsonify({'status':'success','data':{'id':e['id'],'nombre':e['nombre'],'email':e['email'],'codigo_acceso':e['codigo_acceso'],'token':token,'rol':'entrenador'}}),200
    except Exception as e: return jsonify({'error':str(e)}),500


@app.route('/api/certificacion/resultado', methods=['POST'])
def guardar_resultado_certificacion():
    if not supabase: return jsonify({'error':'No DB'}), 500
    try:
        d = request.get_json()
        gimnasio_id = d.get('gimnasio_id','')
        nombre = d.get('nombre','')
        email = d.get('email','')
        clase = d.get('clase','')
        puntuacion = int(d.get('puntuacion',0))
        total = int(d.get('total',0))
        
        if not gimnasio_id or not nombre or not email:
            return jsonify({'error':'Faltan datos'}), 400
        
        # Guardar en tabla certificaciones
        result = supabase.table('certificaciones').insert({
            'gimnasio_id': gimnasio_id,
            'nombre_solicitante': nombre,
            'email_solicitante': email,
            'puntuacion': puntuacion,
            'total_preguntas': total,
            'clase': clase,
            'estado': 'pendiente',
            'fecha_envio': datetime.now(timezone.utc).isoformat()
        }).execute()
        
        return jsonify({'status':'success','message':'Resultado enviado al gimnasio'}), 200
    except Exception as e:
        print(f"Error guardando certificacion: {e}")
        return jsonify({'error':str(e)}), 500

# Ruta para que el gimnasio vea sus certificaciones pendientes
@app.route('/api/gimnasio/<gym_id>/certificaciones', methods=['GET'])
def ver_certificaciones(gym_id):
    if not supabase: return jsonify({'error':'No DB'}), 500
    try:
        result = supabase.table('certificaciones').select('*').eq('gimnasio_id', gym_id).order('fecha_envio', desc=True).execute()
        return jsonify({'status':'success','data':result.data if result.data else []}), 200
    except Exception as e:
        return jsonify({'error':str(e)}), 500

# Ruta para aprobar/rechazar certificacion
@app.route('/api/certificacion/<cert_id>/revisar', methods=['POST'])
def revisar_certificacion(cert_id):
    if not supabase: return jsonify({'error':'No DB'}), 500
    try:
        d = request.get_json()
        estado = d.get('estado','aprobado')
        
        # Actualizar estado
        supabase.table('certificaciones').update({
            'estado': estado,
            'fecha_revision': datetime.now(timezone.utc).isoformat()
        }).eq('id', cert_id).execute()
        
        if estado == 'aprobado':
            # Obtener datos de la certificacion
            cert = supabase.table('certificaciones').select('*').eq('id', cert_id).execute()
            if cert.data:
                c = cert.data[0]
                # Generar codigo unico
                import random, string
                codigo = 'GYM-ENT-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                
                # Crear entrenador
                supabase.table('entrenadores').insert({
                    'gimnasio_id': c['gimnasio_id'],
                    'nombre': c['nombre_solicitante'],
                    'email': c['email_solicitante'],
                    'password_hash': hashlib.sha256('entrenador123'.encode()).hexdigest(),
                    'codigo_acceso': codigo,
                    'especialidad': 'Entrenador',
                    'certificado': True,
                    'puntuacion_test': c['puntuacion'],
                    'activo': True,
                    'precio_sesion': 350
                }).execute()
                
                return jsonify({'status':'success','message':'Entrenador aprobado','codigo':codigo}), 200
        
        return jsonify({'status':'success','message':'Certificacion '+estado}), 200
    except Exception as e:
        print(f"Error revisando certificacion: {e}")
        return jsonify({'error':str(e)}), 500

# FRONTEND - ESTO ES LO CORREGIDO
@app.route('/')
def index():
    return send_from_directory('frontend_web', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    full_path = os.path.join('frontend_web', path)
    if os.path.exists(full_path):
        return send_from_directory('frontend_web', path)
    # Si no existe el archivo, mostrar index
    return send_from_directory('frontend_web', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',5000)))
