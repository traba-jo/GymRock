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

    return jsonify({'status':'success','init_point':r['response']['init_point']}), 200

# FRONTEND - ESTO ES LO CORREGIDO

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    d = request.get_json()
    if d.get('usuario') == 'admin' and hashlib.sha256(d.get('password','').encode()).hexdigest() == '29d34f22434f9f8d826d13e811cd90de93d44ff66f0a0150d72a25bb55040ffb':
        token = jwt.encode({'user':{'id':'admin','rol':'super_admin'},'exp':datetime.now(timezone.utc)+timedelta(days=365)}, SECRET_KEY, algorithm='HS256')
        return jsonify({'status':'success','data':{'token':token}}), 200
    return jsonify({'error':'Credenciales invalidas'}), 401

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
