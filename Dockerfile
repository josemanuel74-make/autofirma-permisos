# Usar imagen base ligera de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema si fueran necesarias
# (Para pypdf no solemos necesitar nada especial, pero por si acaso)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . .

# Crear la carpeta de documentos firmados y asegurar permisos
RUN mkdir -p signed_docs && chmod 777 signed_docs

# Exponer el puerto que usará Gunicorn
EXPOSE 5001

# Comando para ejecutar la aplicación con Gunicorn
# -w 4: 4 workers (ajustable según el servidor)
# -b 0.0.0.0:5001: escuchar en todas las interfaces
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "app:app"]
