"""
GYMROCK - mp_integration.py
Integración con Mercado Pago para pagos
"""

import os
from datetime import datetime, timedelta
from database import db

# Intentar importar Mercado Pago
try:
    import mercadopago
    print("✅ Librería Mercado Pago importada")
except ImportError:
    print("❌ Error: Instala 'pip install mercadopago'")
    exit(1)

class MercadoPago:
    """Clase para manejar la integración con Mercado Pago"""
    
    def __init__(self):
        """Inicializar SDK de Mercado Pago"""
        # 🔴 ACCESS TOKEN REAL (Configurado) 🔴
        self.access_token = 'TEST-6071603897073892-071217-d43ed37fe27e0ef6db3036fb838a8215-3536704335'
        
        # Inicializar SDK
        try:
            self.sdk = mercadopago.SDK(self.access_token)
            print("✅ SDK de Mercado Pago inicializado")
        except Exception as e:
            print(f"❌ Error al inicializar SDK: {e}")
            self.sdk = None
        
        self.base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    
    def crear_preferencia_suscripcion(self, suscripcion_id, monto, concepto, usuario_email, usuario_nombre):
        """
        Crear una preferencia de pago para una suscripción
        
        Args:
            suscripcion_id (str): ID de la suscripción en GymRock
            monto (float): Monto a cobrar
            concepto (str): Descripción del pago
            usuario_email (str): Email del cliente
            usuario_nombre (str): Nombre del cliente
            
        Returns:
            dict: Respuesta de Mercado Pago con el link de pago
        """
        try:
            if not self.sdk:
                return {"status": "error", "message": "SDK no inicializado"}
            
            preference_data = {
                "items": [
                    {
                        "title": concepto,
                        "description": f"Suscripción GymRock - {concepto}",
                        "quantity": 1,
                        "currency_id": "MXN",
                        "unit_price": float(monto)
                    }
                ],
                "payer": {
                    "email": usuario_email,
                    "name": usuario_nombre
                },
                "back_urls": {
                    "success": f"{self.base_url}/api/pago-exitoso",
                    "failure": f"{self.base_url}/api/pago-fallido",
                    "pending": f"{self.base_url}/api/pago-pendiente"
                },
                "auto_return": "approved",
                "external_reference": str(suscripcion_id),
                "notification_url": f"{self.base_url}/api/webhook"
            }
            
            # Para versión 3.x de Mercado Pago
            try:
                response = self.sdk.preference().create(preference_data)
            except AttributeError:
                # Para versión 2.x de Mercado Pago
                response = self.sdk.create_preference(preference_data)
            
            if response["status"] == 201:
                preference = response["response"]
                return {
                    "status": "success",
                    "payment_link": preference["init_point"],
                    "preference_id": preference["id"]
                }
            else:
                return {
                    "status": "error",
                    "message": "Error al crear la preferencia",
                    "details": response
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def verificar_pago(self, payment_id):
        """
        Verificar el estado de un pago en Mercado Pago
        
        Args:
            payment_id (str): ID del pago en Mercado Pago
            
        Returns:
            dict: Información del pago
        """
        try:
            if not self.sdk:
                return {"status": "error", "message": "SDK no inicializado"}
            
            try:
                response = self.sdk.payment().get(payment_id)
            except AttributeError:
                response = self.sdk.get_payment(payment_id)
            
            if response["status"] == 200:
                payment = response["response"]
                return {
                    "status": payment.get("status"),
                    "amount": payment.get("transaction_amount"),
                    "external_reference": payment.get("external_reference"),
                    "payment_method": payment.get("payment_type_id"),
                    "installments": payment.get("installments"),
                    "card_brand": payment.get("card", {}).get("brand")
                }
            else:
                return {
                    "status": "error",
                    "message": "No se pudo obtener el pago"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def procesar_webhook(self, data):
        """
        Procesar la notificación de pago de Mercado Pago (webhook)
        
        Args:
            data (dict): Datos recibidos de Mercado Pago
            
        Returns:
            dict: Estado del procesamiento
        """
        try:
            payment_id = data.get('data', {}).get('id')
            if not payment_id:
                return {"status": "error", "message": "No se encontró payment_id"}
            
            payment_info = self.verificar_pago(payment_id)
            
            if payment_info.get("status") != "approved":
                return {
                    "status": "error", 
                    "message": f"Pago no aprobado: {payment_info.get('status')}"
                }
            
            external_reference = payment_info.get("external_reference")
            if not external_reference:
                return {"status": "error", "message": "No se encontró referencia externa"}
            
            return self._actualizar_suscripcion_pagada(
                int(external_reference),
                payment_id,
                payment_info["amount"],
                payment_info["status"]
            )
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al procesar webhook: {str(e)}"
            }
    
    def _actualizar_suscripcion_pagada(self, suscripcion_id, payment_id, monto, estado):
        """
        Actualizar la base de datos cuando un pago es aprobado
        """
        try:
            # Registrar el pago en la tabla pagos
            pago_data = {
                'suscripcion_id': suscripcion_id,
                'monto': monto,
                'mp_payment_id': str(payment_id),
                'estado': estado,
                'fecha_pago': datetime.now().isoformat()
            }
            
            db.registrar_pago(pago_data)
            
            # Actualizar la suscripción
            nueva_fecha_corte = datetime.now() + timedelta(days=30)
            db.renovar_suscripcion(suscripcion_id, nueva_fecha_corte.isoformat())
            
            return {
                "status": "success",
                "message": "Pago procesado correctamente",
                "suscripcion_id": suscripcion_id,
                "nueva_fecha_corte": nueva_fecha_corte.isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al actualizar BD: {str(e)}"
            }
    
    def crear_enlace_pago_licencia(self, gimnasio_id, plan, monto):
        """
        Crear un enlace de pago para la licencia de un gimnasio
        """
        try:
            gym_result = db.obtener_gimnasio(gimnasio_id)
            if not gym_result.data:
                return {"status": "error", "message": "Gimnasio no encontrado"}
            
            gym = gym_result.data[0]
            
            preference_data = {
                "items": [
                    {
                        "title": f"Licencia GymRock - Plan {plan.capitalize()}",
                        "description": f"Licencia operativa para {gym['nombre']} - Plan {plan}",
                        "quantity": 1,
                        "currency_id": "MXN",
                        "unit_price": float(monto)
                    }
                ],
                "payer": {
                    "email": gym['email'],
                    "name": gym['nombre']
                },
                "back_urls": {
                    "success": f"{self.base_url}/api/licencia-exitosa",
                    "failure": f"{self.base_url}/api/licencia-fallida"
                },
                "auto_return": "approved",
                "external_reference": f"licencia_{gimnasio_id}",
                "notification_url": f"{self.base_url}/api/webhook-licencia"
            }
            
            try:
                response = self.sdk.preference().create(preference_data)
            except AttributeError:
                response = self.sdk.create_preference(preference_data)
            
            if response["status"] == 201:
                preference = response["response"]
                return {
                    "status": "success",
                    "payment_link": preference["init_point"],
                    "preference_id": preference["id"]
                }
            else:
                return {
                    "status": "error",
                    "message": "Error al crear la preferencia"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def crear_tarjeta_puntos(self, usuario_id, monto):
        """
        Recargar tarjeta de puntos para un cliente
        
        Args:
            usuario_id (str): ID del usuario
            monto (float): Monto a recargar
            
        Returns:
            dict: Link de pago para la recarga
        """
        try:
            user_result = db.obtener_usuario(usuario_id)
            if not user_result.data:
                return {"status": "error", "message": "Usuario no encontrado"}
            
            user = user_result.data[0]
            
            preference_data = {
                "items": [
                    {
                        "title": "Recarga de Puntos GymRock",
                        "description": f"Recarga de puntos para {user['nombre']}",
                        "quantity": 1,
                        "currency_id": "MXN",
                        "unit_price": float(monto)
                    }
                ],
                "payer": {
                    "email": user['email'],
                    "name": user['nombre']
                },
                "back_urls": {
                    "success": f"{self.base_url}/api/recarga-exitosa",
                    "failure": f"{self.base_url}/api/recarga-fallida"
                },
                "auto_return": "approved",
                "external_reference": f"puntos_{usuario_id}",
                "notification_url": f"{self.base_url}/api/webhook-puntos"
            }
            
            try:
                response = self.sdk.preference().create(preference_data)
            except AttributeError:
                response = self.sdk.create_preference(preference_data)
            
            if response["status"] == 201:
                preference = response["response"]
                return {
                    "status": "success",
                    "payment_link": preference["init_point"],
                    "preference_id": preference["id"]
                }
            else:
                return {
                    "status": "error",
                    "message": "Error al crear la preferencia"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }

# Instancia global
mp = MercadoPago()

# Prueba si se ejecuta directamente
if __name__ == '__main__':
    print("="*40)
    print("💳 GYMROCK - Mercado Pago Test")
    print("="*40)
    if mp.sdk:
        print("✅ Mercado Pago inicializado correctamente")
        print(f"🔑 Access Token: {mp.access_token[:20]}...")
        print("📋 Métodos disponibles:")
        print("   - crear_preferencia_suscripcion()")
        print("   - verificar_pago()")
        print("   - procesar_webhook()")
        print("   - crear_enlace_pago_licencia()")
        print("   - crear_tarjeta_puntos()")
    else:
        print("❌ Mercado Pago NO inicializado")
    print("="*40)