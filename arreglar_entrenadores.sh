#!/bin/bash

echo "🔧 ARREGLANDO PROBLEMA DE ENTRENADORES APROBADOS"

# Hacer backup del archivo original
cp frontend_web/gimnasio/entrenadores.html frontend_web/gimnasio/entrenadores.html.backup
echo "✅ Backup creado"

# Corrección principal - cambiar 'estado' por 'estado_certificacion'
sed -i 's/.eq('\''estado'\'', '\''aprobado'\'')/.eq('\''estado_certificacion'\'', '\''aprobado'\'')/g' frontend_web/gimnasio/entrenadores.html

# Corrección adicional - cambiar 'estado' por 'estado_certificacion' en rechazados
sed -i 's/.eq('\''estado'\'', '\''rechazado'\'')/.eq('\''estado_certificacion'\'', '\''rechazado'\'')/g' frontend_web/gimnasio/entrenadores.html

# También arreglar en cliente si existe
if [ -f "frontend_web/cliente/entrenadores.html" ]; then
    sed -i 's/.eq('\''estado'\'', '\''aprobado'\'')/.eq('\''estado_certificacion'\'', '\''aprobado'\'')/g' frontend_web/cliente/entrenadores.html
    sed -i 's/.eq('\''estado'\'', '\''rechazado'\'')/.eq('\''estado_certificacion'\'', '\''rechazado'\'')/g' frontend_web/cliente/entrenadores.html
    echo "✅ Cliente también arreglado"
fi

echo "✅ ARCHIVOS MODIFICADOS CORRECTAMENTE"
echo ""
echo "📋 VERIFICACIÓN:"
echo "Archivo modificado: frontend_web/gimnasio/entrenadores.html"
echo "Backup creado: frontend_web/gimnasio/entrenadores.html.backup"
echo ""
echo "🔄 RECUERDA: Refrescar la página en el navegador"
