#!/bin/bash

# --- CONFIGURACIÓN ---
PROJECT_DIR="~/autofirma-permisos" # Cambia esto si la ruta en el VPS es distinta
SERVICE_NAME="autofirma"            # Nombre del servicio systemd

echo "🚀 Iniciando despliegue..."

# 1. Entrar al directorio
cd $PROJECT_DIR || { echo "❌ Error: No se encuentra el directorio $PROJECT_DIR"; exit 1; }

# 2. Bajar cambios de GitHub
echo "📥 Descargando cambios desde GitHub..."
git pull origin main

# 3. Instalar dependencias si han cambiado (opcional)
# pip install -r requirements.txt

# 4. Reiniciar el servicio
echo "🔄 Reiniciando servicio $SERVICE_NAME..."
sudo systemctl restart $SERVICE_NAME

echo "✅ ¡Despliegue completado con éxito!"
