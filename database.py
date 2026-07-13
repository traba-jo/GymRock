"""
GYMROCK - database.py
Conexión y operaciones con Supabase
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno desde la carpeta actual
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# =============================================
# CONFIGURACIÓN DESDE .env
# =============================================
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Si no se cargaron desde .env, mostrar error
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: No se encontraron SUPABASE_URL o SUPABASE_KEY en .env")
    print("   Verifica que el archivo backend/.env exista y tenga las credenciales correctas.")

class Database:
    """Clase para manejar todas las operaciones de BD"""
    
    def __init__(self):
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("✅ Conexión a Supabase establecida")
        except Exception as e:
            print(f"❌ Error al conectar a Supabase: {e}")
            self.supabase = None
    
    # =============================================
    # GIMNASIOS
    # =============================================
    def registrar_gimnasio(self, data):
        """Registrar un nuevo gimnasio"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('gimnasios').insert(data).execute()
    
    def obtener_gimnasio(self, gimnasio_id):
        """Obtener datos de un gimnasio"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('gimnasios')\
            .select('*')\
            .eq('id', gimnasio_id)\
            .execute()
    
    def obtener_gimnasios_por_ubicacion(self, estado, municipio):
        """Obtener gimnasios por ubicación"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        query = self.supabase.table('gimnasios')\
            .select('*')\
            .eq('visible_publico', True)\
            .eq('estado_licencia', 'activa')
        
        if estado:
            query = query.eq('estado', estado)
        if municipio:
            query = query.eq('municipio', municipio)
        
        return query.execute()
    
    def actualizar_licencia(self, gimnasio_id, fecha_corte, estado):
        """Actualizar licencia del gimnasio"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('gimnasios')\
            .update({
                'licencia_fecha_corte': fecha_corte,
                'estado_licencia': estado
            })\
            .eq('id', gimnasio_id)\
            .execute()
    
    # =============================================
    # USUARIOS (Clientes)
    # =============================================
    def registrar_usuario(self, data):
        """Registrar un nuevo cliente"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('usuarios').insert(data).execute()
    
    def obtener_usuario(self, usuario_id):
        """Obtener datos de un usuario"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('usuarios')\
            .select('*')\
            .eq('id', usuario_id)\
            .execute()
    
    # =============================================
    # ENTRENADORES
    # =============================================
    def registrar_entrenador(self, data):
        """Registrar un nuevo entrenador"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('entrenadores').insert(data).execute()
    
    def obtener_entrenadores_por_gimnasio(self, gimnasio_id):
        """Obtener entrenadores de un gimnasio"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('entrenadores')\
            .select('*')\
            .eq('gimnasio_id', gimnasio_id)\
            .execute()
    
    def actualizar_certificado_cc(self, entrenador_id, certificado, puntaje):
        """Actualizar certificado de confianza"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('entrenadores')\
            .update({
                'certificado_cc': certificado,
                'puntaje_test': puntaje
            })\
            .eq('id', entrenador_id)\
            .execute()
    
    # =============================================
    # SUSCRIPCIONES
    # =============================================
    def crear_suscripcion(self, data):
        """Crear una nueva suscripción"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('suscripciones').insert(data).execute()
    
    def obtener_suscripciones_usuario(self, usuario_id):
        """Obtener suscripciones de un usuario"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('suscripciones')\
            .select('*, gimnasios(nombre), planes_suscripcion(nombre, precio)')\
            .eq('usuario_id', usuario_id)\
            .execute()
    
    def obtener_suscripciones_gimnasio(self, gimnasio_id):
        """Obtener suscripciones de un gimnasio"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('suscripciones')\
            .select('*, usuarios(nombre, email, telefono)')\
            .eq('gimnasio_id', gimnasio_id)\
            .execute()
    
    def renovar_suscripcion(self, suscripcion_id, nueva_fecha_corte):
        """Renovar una suscripción"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('suscripciones')\
            .update({
                'fecha_corte': nueva_fecha_corte,
                'activa': True
            })\
            .eq('id', suscripcion_id)\
            .execute()
    
    # =============================================
    # PAGOS
    # =============================================
    def registrar_pago(self, data):
        """Registrar un nuevo pago"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('pagos').insert(data).execute()
    
    def actualizar_estado_pago(self, payment_id, estado):
        """Actualizar estado de un pago"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('pagos')\
            .update({'estado': estado})\
            .eq('mp_payment_id', payment_id)\
            .execute()
    
    # =============================================
    # NOTIFICACIONES
    # =============================================
    def crear_notificacion(self, data):
        """Crear una notificación"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('notificaciones').insert(data).execute()
    
    def obtener_notificaciones_usuario(self, usuario_id):
        """Obtener notificaciones de un usuario"""
        if not self.supabase:
            return {'error': 'Sin conexión a BD'}
        return self.supabase.table('notificaciones')\
            .select('*')\
            .eq('usuario_id', usuario_id)\
            .order('fecha_envio', desc=True)\
            .execute()
    
    # =============================================
    # MÉTODO DE PRUEBA
    # =============================================
    def test_conexion(self):
        """Probar conexión a Supabase"""
        if not self.supabase:
            return {'status': 'error', 'message': 'Sin conexión a BD'}
        try:
            result = self.supabase.table('gimnasios')\
                .select('id', count='exact')\
                .limit(1)\
                .execute()
            return {'status': 'ok', 'message': 'Conexión exitosa', 'data': result.data}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Instancia global
db = Database()

# Prueba si se ejecuta directamente
if __name__ == '__main__':
    print("="*40)
    print("🏋️ GYMROCK - Database Test")
    print("="*40)
    result = db.test_conexion()
    print(f"📡 Conexión: {result['status']}")
    print(f"📝 Mensaje: {result['message']}")
    if result.get('data') is not None:
        print(f"📊 Datos: {result['data']}")
    print("="*40)