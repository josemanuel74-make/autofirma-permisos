# AutoFirma Permisos

Aplicación web para la generación y firma digital de solicitudes de permiso del IES Leopoldo Queipo (Melilla).

## ¿Qué hace?

1. **Formulario web**: El funcionario rellena sus datos (nombre, DNI, NRP, motivo, días, adjunto…).
2. **Genera el PDF**: Rellena automáticamente la plantilla oficial `Solicitud Permiso.pdf` con los datos del formulario.
3. **Firma digital**: Abre el cliente de **AutoFirma** en el equipo del usuario para firmar el documento con certificado digital. La firma queda visible (sello PAdES) en la primera página del PDF.
4. **Guarda localmente**: El PDF firmado se almacena en la carpeta `signed_docs/`.
5. **Envía a Power Automate**: Manda todos los datos + el PDF en base64 a un webhook de Power Automate que:
   - Rellena una fila en un Excel de seguimiento en OneDrive.
   - Guarda el PDF firmado en una carpeta de OneDrive y enlaza el documento en el Excel.

## Requisitos

- Python 3.9+
- AutoFirma instalado en el equipo del usuario

## Instalación

```bash
# 1. Clona el repositorio
git clone https://github.com/josemanuel74-make/autofirma-permisos.git
cd autofirma-permisos

# 2. Crea el entorno virtual e instala dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuración

Abre `app.py` y ajusta la variable `WEBHOOK_URL` con tu URL de Power Automate:

```python
WEBHOOK_URL = "https://tu-url-de-power-automate..."
```

## Ejecución

```bash
source .venv/bin/activate
python app.py
```

La aplicación arrancará en `http://localhost:5001/permiso`.

## Estructura del proyecto

```
autofirma-permisos/
├── app.py                  # Servidor Flask principal
├── requirements.txt        # Dependencias Python
├── Solicitud Permiso.pdf   # Plantilla oficial PDF
├── static/
│   ├── css/style.css       # Estilos de la web
│   ├── img/logo.gif        # Logo del centro
│   └── js/autoscript.js   # Cliente JavaScript de AutoFirma
└── templates/
    ├── index.html          # Página de inicio
    └── solicitud_permiso.html  # Formulario de solicitud
```

## Dependencias principales

| Paquete | Uso |
|---|---|
| Flask | Servidor web |
| pypdf | Manipulación de PDFs |
| reportlab | Estampado de texto sobre el PDF |
| Pillow | Conversión de imágenes a PDF |
| requests | Envío del webhook a Power Automate |
