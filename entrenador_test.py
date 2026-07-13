"""
GYMROCK - entrenador_test.py
Sistema de Certificado de Confianza (C.C.) para entrenadores
"""

import json
from datetime import datetime
from database import db

class EntrenadorTest:
    """Clase para manejar el sistema de certificación de entrenadores"""
    
    def __init__(self):
        # Banco de preguntas para el test
        self.preguntas = [
            {
                "id": 1,
                "categoria": "Anatomía",
                "pregunta": "¿Cuál es el músculo principal trabajado en un press de banca?",
                "opciones": ["Bíceps", "Pectoral", "Tríceps", "Deltoides"],
                "correcta": 1,
                "explicacion": "El press de banca trabaja principalmente el pectoral mayor"
            },
            {
                "id": 2,
                "categoria": "Anatomía",
                "pregunta": "¿Qué músculo forma parte del 'core' (zona media)?",
                "opciones": ["Bíceps", "Recto abdominal", "Cuádriceps", "Gemelos"],
                "correcta": 1,
                "explicacion": "El recto abdominal es parte fundamental del core"
            },
            {
                "id": 3,
                "categoria": "Nutrición",
                "pregunta": "¿Qué macronutriente es más importante para la recuperación muscular post-entreno?",
                "opciones": ["Grasas", "Proteínas", "Carbohidratos", "Fibra"],
                "correcta": 1,
                "explicacion": "Las proteínas son esenciales para la reparación muscular"
            },
            {
                "id": 4,
                "categoria": "Nutrición",
                "pregunta": "¿Cuánta agua se recomienda beber al día para una persona activa?",
                "opciones": ["1-2 litros", "2-3 litros", "3-4 litros", "4-5 litros"],
                "correcta": 1,
                "explicacion": "Se recomiendan 2-3 litros para personas activas"
            },
            {
                "id": 5,
                "categoria": "Entrenamiento",
                "pregunta": "¿Cuál es la técnica correcta para una sentadilla?",
                "opciones": [
                    "Rodillas sobre puntas de pies",
                    "Cadera atrás y pecho arriba",
                    "Espalda redondeada",
                    "Talones levantados"
                ],
                "correcta": 1,
                "explicacion": "La cadera atrás y pecho arriba mantiene la columna neutra"
            },
            {
                "id": 6,
                "categoria": "Entrenamiento",
                "pregunta": "¿Cuántas series se recomiendan para hipertrofia muscular?",
                "opciones": ["1-2 series", "3-4 series", "5-6 series", "7-8 series"],
                "correcta": 1,
                "explicacion": "3-4 series es el rango óptimo para hipertrofia"
            },
            {
                "id": 7,
                "categoria": "Nutrición",
                "pregunta": "¿Qué vitamina es clave para la absorción de calcio?",
                "opciones": ["Vitamina A", "Vitamina C", "Vitamina D", "Vitamina E"],
                "correcta": 2,
                "explicacion": "La vitamina D es esencial para la absorción del calcio"
            },
            {
                "id": 8,
                "categoria": "Anatomía",
                "pregunta": "¿Cuál es el hueso más largo del cuerpo humano?",
                "opciones": ["Fémur", "Tibia", "Húmero", "Radio"],
                "correcta": 0,
                "explicacion": "El fémur es el hueso más largo y fuerte del cuerpo"
            },
            {
                "id": 9,
                "categoria": "Entrenamiento",
                "pregunta": "¿Cuánto tiempo de descanso se recomienda entre series para fuerza?",
                "opciones": ["30 segundos", "1 minuto", "2-3 minutos", "5 minutos"],
                "correcta": 2,
                "explicacion": "2-3 minutos permite recuperación completa del ATP"
            },
            {
                "id": 10,
                "categoria": "Nutrición",
                "pregunta": "¿Qué alimento es una fuente completa de proteínas?",
                "opciones": ["Arroz", "Huevo", "Pan", "Pasta"],
                "correcta": 1,
                "explicacion": "El huevo contiene todos los aminoácidos esenciales"
            }
        ]
        
        self.minimo_aprobacion = 80  # Porcentaje mínimo para obtener C.C.
        print("✅ Sistema de Certificación de Entrenadores inicializado")
        print(f"📋 Banco de preguntas: {len(self.preguntas)} preguntas")
    
    def obtener_todas_preguntas(self):
        """
        Obtener todas las preguntas del test
        
        Returns:
            list: Lista de preguntas (sin la respuesta correcta)
        """
        preguntas_publicas = []
        for p in self.preguntas:
            preguntas_publicas.append({
                "id": p["id"],
                "categoria": p["categoria"],
                "pregunta": p["pregunta"],
                "opciones": p["opciones"]
            })
        return preguntas_publicas
    
    def evaluar_test(self, respuestas):
        """
        Evaluar las respuestas del test
        
        Args:
            respuestas (list): Lista de respuestas del usuario
            
        Returns:
            dict: Resultado de la evaluación
        """
        if not respuestas or len(respuestas) != len(self.preguntas):
            return {
                "status": "error",
                "message": f"Se requieren {len(self.preguntas)} respuestas"
            }
        
        aciertos = 0
        resultados_detalle = []
        
        for i, respuesta in enumerate(respuestas):
            pregunta = self.preguntas[i]
            es_correcta = (respuesta == pregunta["correcta"])
            if es_correcta:
                aciertos += 1
            
            resultados_detalle.append({
                "pregunta_id": pregunta["id"],
                "pregunta": pregunta["pregunta"],
                "respuesta_usuario": respuesta,
                "respuesta_correcta": pregunta["correcta"],
                "es_correcta": es_correcta,
                "explicacion": pregunta["explicacion"]
            })
        
        porcentaje = (aciertos / len(self.preguntas)) * 100
        aprobado = porcentaje >= self.minimo_aprobacion
        
        return {
            "status": "success",
            "aciertos": aciertos,
            "total": len(self.preguntas),
            "porcentaje": round(porcentaje, 2),
            "aprobado": aprobado,
            "certificado_cc": aprobado,
            "detalle": resultados_detalle,
            "mensaje": "¡Felicidades! Obtuviste el Certificado de Confianza 🏅" if aprobado else "No alcanzaste el puntaje mínimo. ¡Sigue preparándote!"
        }
    
    def registrar_entrenador(self, nombre, email, telefono, gimnasio_id, especialidad="entrenador"):
        """
        Registrar un nuevo entrenador en el sistema
        
        Args:
            nombre (str): Nombre completo
            email (str): Email del entrenador
            telefono (str): Número de teléfono
            gimnasio_id (str): ID del gimnasio al que pertenece
            especialidad (str): entrenador, nutriologo, ambos
            
        Returns:
            dict: Resultado del registro
        """
        try:
            # Verificar si el email ya está registrado
            existing = db.obtener_entrenadores_por_gimnasio(gimnasio_id)
            if existing and hasattr(existing, 'data'):
                for entrenador in existing.data:
                    if entrenador.get('email') == email:
                        return {
                            "status": "error",
                            "message": "Este email ya está registrado como entrenador"
                        }
            
            # Datos del entrenador (sin certificado aún)
            entrenador_data = {
                'nombre': nombre,
                'email': email,
                'telefono': telefono,
                'gimnasio_id': gimnasio_id,
                'especialidad': especialidad,
                'certificado_cc': False,
                'puntaje_test': None,
                'disponible': True,
                'fecha_registro': datetime.now().isoformat()
            }
            
            result = db.registrar_entrenador(entrenador_data)
            
            if result and hasattr(result, 'data') and result.data:
                return {
                    "status": "success",
                    "message": "Entrenador registrado exitosamente",
                    "data": result.data[0],
                    "siguiente_paso": "Aplicar test de certificación"
                }
            else:
                return {
                    "status": "error",
                    "message": "Error al registrar entrenador"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def certificar_entrenador(self, entrenador_id, respuestas):
        """
        Aplicar el test y certificar a un entrenador
        
        Args:
            entrenador_id (str): ID del entrenador
            respuestas (list): Lista de respuestas del test
            
        Returns:
            dict: Resultado de la certificación
        """
        try:
            # Evaluar el test
            resultado = self.evaluar_test(respuestas)
            
            if resultado["status"] == "error":
                return resultado
            
            # Actualizar la base de datos
            db.actualizar_certificado_cc(
                entrenador_id,
                resultado["certificado_cc"],
                resultado["porcentaje"]
            )
            
            return {
                "status": "success",
                "entrenador_id": entrenador_id,
                "certificado_cc": resultado["certificado_cc"],
                "porcentaje": resultado["porcentaje"],
                "aciertos": resultado["aciertos"],
                "total": resultado["total"],
                "mensaje": resultado["mensaje"],
                "detalle": resultado["detalle"]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al certificar entrenador: {str(e)}"
            }
    
    def obtener_entrenadores_certificados(self, gimnasio_id):
        """
        Obtener todos los entrenadores certificados de un gimnasio
        
        Args:
            gimnasio_id (str): ID del gimnasio
            
        Returns:
            dict: Lista de entrenadores certificados
        """
        try:
            result = db.obtener_entrenadores_por_gimnasio(gimnasio_id)
            
            if not result or not hasattr(result, 'data'):
                return {
                    "status": "success",
                    "data": [],
                    "total": 0
                }
            
            entrenadores = result.data
            certificados = [e for e in entrenadores if e.get('certificado_cc', False)]
            
            return {
                "status": "success",
                "data": certificados,
                "total": len(certificados),
                "total_entrenadores": len(entrenadores)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def obtener_estadisticas_gimnasio(self, gimnasio_id):
        """
        Obtener estadísticas de certificación de un gimnasio
        
        Args:
            gimnasio_id (str): ID del gimnasio
            
        Returns:
            dict: Estadísticas
        """
        try:
            result = db.obtener_entrenadores_por_gimnasio(gimnasio_id)
            
            if not result or not hasattr(result, 'data'):
                return {
                    "status": "success",
                    "total": 0,
                    "certificados": 0,
                    "sin_certificar": 0,
                    "porcentaje_certificados": 0
                }
            
            entrenadores = result.data
            total = len(entrenadores)
            certificados = len([e for e in entrenadores if e.get('certificado_cc', False)])
            sin_certificar = total - certificados
            
            return {
                "status": "success",
                "total": total,
                "certificados": certificados,
                "sin_certificar": sin_certificar,
                "porcentaje_certificados": round((certificados / total * 100), 2) if total > 0 else 0
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }

# Instancia global
test_entrenador = EntrenadorTest()

# Prueba si se ejecuta directamente
if __name__ == '__main__':
    print("="*40)
    print("🏅 GYMROCK - Sistema de Certificación de Entrenadores")
    print("="*40)
    
    print(f"\n📋 Banco de preguntas: {len(test_entrenador.preguntas)} preguntas")
    print(f"📊 Mínimo para aprobar: {test_entrenador.minimo_aprobacion}%")
    print("\n📝 Preguntas de ejemplo:")
    
    # Mostrar primeras 3 preguntas
    for i, p in enumerate(test_entrenador.preguntas[:3]):
        print(f"\n{i+1}. [{p['categoria']}] {p['pregunta']}")
        for j, opcion in enumerate(p['opciones']):
            print(f"   {j}. {opcion}")
        print(f"   ✅ Respuesta correcta: {p['correcta']}")
    
    print("\n" + "="*40)
    print("✅ Sistema listo para usar")
    print("📋 Métodos disponibles:")
    print("   - obtener_todas_preguntas()")
    print("   - evaluar_test(respuestas)")
    print("   - registrar_entrenador(...)")
    print("   - certificar_entrenador(...)")
    print("   - obtener_entrenadores_certificados(...)")
    print("   - obtener_estadisticas_gimnasio(...)")
    print("="*40)