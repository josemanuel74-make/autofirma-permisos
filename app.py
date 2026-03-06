from flask import Flask, render_template, request, jsonify
import base64
import os
import time
import io
from pypdf import PdfReader, PdfWriter, PageObject
from PIL import Image
import requests

app = Flask(__name__)

# Enforce the folder where signed documents will be saved
SIGNED_DOCS_FOLDER = os.path.join(os.getcwd(), 'signed_docs')
if not os.path.exists(SIGNED_DOCS_FOLDER):
    os.makedirs(SIGNED_DOCS_FOLDER)

UPLOADS_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)

# --- CONFIGURATION ---
# Replace this with your actual Power Automate Webhook URL
WEBHOOK_URL = "https://default70879308da7343a1acdf57810f4ae6.2b.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/6500d208c0ce4a4d91f2e8d313e22aac/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=LI_rqf4S28tioqVtXr2WmztpmdqY4qqnlGjTOSc92mc" 
# ---------------------

@app.route('/')
@app.route('/permiso')
def permiso_form_root():
    return render_template('solicitud_permiso.html')

@app.route('/save', methods=['POST'])
def save_signature():
    try:
        data = request.json
        signature_b64 = data.get('signature')
        nombre_original = data.get('nombre', 'Anonimo')
        nombre_sanitizado = nombre_original.replace(' ', '_')
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # Sanitize filename
        safe_nombre = "".join([c for c in nombre_sanitizado if c.isalnum() or c in ('_', '-')]).rstrip()
        filename = f"Solicitud_Permiso_{safe_nombre}_{timestamp}_Firmado.pdf"
        
        save_path = os.path.join(SIGNED_DOCS_FOLDER, filename)
        
        print(f"DEBUG: Saving signature for {filename}")
        # Decode and save
        with open(save_path, "wb") as fh:
            fh.write(base64.b64decode(signature_b64))
            
        print(f"DEBUG: File saved successfully at {save_path}")

        # --- POWER AUTOMATE INTEGRATION ---
        webhook_status = "skipped"
        if WEBHOOK_URL:
            try:
                print(f"DEBUG: Sending to Webhook: {WEBHOOK_URL}")
                with open(save_path, 'rb') as pdf_file:
                    # Send all metadata and base64 file as a JSON payload
                    payload = {
                        'nombre': nombre_original,
                        'timestamp': timestamp,
                        'filename': filename,
                        'dni': data.get('dni', ''),
                        'nrp': data.get('nrp', ''),
                        'asignatura': data.get('asignatura', ''),
                        'motivo': data.get('motivo', ''),
                        'articulo': data.get('articulo', ''),
                        'dias_solicitados': data.get('dias_solicitados', ''),
                        'total_dias': data.get('total_dias', '0'),
                        'descripcion_adjunto': data.get('descripcion_adjunto', ''),
                        'fecha_solicitud': data.get('fecha', ''),
                        'file_base64': signature_b64
                    }
                    response = requests.post(WEBHOOK_URL, json=payload)
                    print(f"DEBUG: Webhook Response: {response.status_code} - {response.text}")
                    if response.ok:
                        webhook_status = "success"
                    else:
                        webhook_status = f"failed_http_{response.status_code}"
            except Exception as e_webhook:
                print(f"ERROR: Webhook execution failed: {str(e_webhook)}")
                webhook_status = f"error_{str(e_webhook)}"
        # ----------------------------------

        return jsonify({
            "status": "success", 
            "message": "File saved successfully", 
            "path": save_path,
            "webhook_status": webhook_status
        })
    except Exception as e:
        print(f"ERROR in /save: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/permiso')
def permiso_form():
    return render_template('solicitud_permiso.html')

@app.route('/generate_permiso', methods=['POST'])
def generate_permiso():
    try:
        # Check if content type is json or multipart
        if request.is_json:
            data = request.json
            files = request.files
        else:
            data = request.form
            files = request.files
        
        # Handle justification description
        attachment_path = None
        justificacion_text = data.get('descripcion_adjunto', 'No adjunto')
        
        nombre_profe = data.get('nombre', 'Anonimo').replace(' ', '_')
        # Sanitize name for filesystem
        safe_name = "".join([c for c in nombre_profe if c.isalnum() or c in ('_', '-')]).rstrip()
        timestamp_str = time.strftime('%Y%m%d_%H%M%S')

        if 'justificacion_file' in files:
            file = files['justificacion_file']
            if file.filename != '':
                ext = file.filename.split('.')[-1]
                secure_name = f"Justificante_{safe_name}_{timestamp_str}.{ext}"
                attachment_path = os.path.join(UPLOADS_FOLDER, secure_name)
                file.save(attachment_path)
        
        # Load and clone the PDF to preserve structure and forms
        # We rename the template if it's renamed, or just keep using the same file but updating references
        template_name = "Solicitud Permiso Definitivo.pdf"
        if not os.path.exists(template_name):
            template_name = "Solicitud Permiso.pdf"  # Fallback a la plantilla anterior
            
        writer = PdfWriter(clone_from=template_name)



        # --- STAMPING APPROACH (Fix for Adobe Acrobat Tildes) ---
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        # Create the overlay PDF with text
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        
        # Helper to draw
        def draw_text(x, y, text, size=10):
            if not text: return
            c.setFont("Helvetica", size)
            c.drawString(x, y, str(text))

        # Helper for multi-line text (simple wrapping)
        def draw_multiline(x, y, text, width, size=10):
            if not text: return
            c.setFont("Helvetica", size)
            import textwrap
            chars_per_line = int(width / 6)
            lines = textwrap.wrap(str(text), chars_per_line)
            current_y = y
            for line in lines:
                c.drawString(x, current_y, line)
                current_y -= (size + 4)

        # --- PÁGINA 1 (ANEXO II) ---
        # NOMBRE: etiqueta en Y~644.7, ponemos texto en Y=632
        draw_text(71, 632, data.get('nombre', ''), size=11)

        # NRP: etiqueta en Y~574.2, ponemos texto en Y=562
        draw_text(132, 562, data.get('nrp', ''))

        # DNI: etiqueta en Y~574.2, offset X=283
        draw_text(283, 562, data.get('dni', ''))

        # ASIGNATURA: offset X~430
        draw_text(430, 562, data.get('asignatura', ''))

        # DIAS SOLICITADOS: etiqueta en Y~486.1, texto en Y=474
        draw_multiline(71, 474, data.get('dias_solicitados', ''), width=450)

        # MOTIVO: etiqueta en Y~380.9, texto en Y=368
        draw_multiline(71, 368, data.get('motivo', ''), width=450)

        # ARTICULO: etiqueta en Y~252.6, texto en Y=252
        draw_text(210, 252, data.get('articulo', ''))

        # FECHA: "Melilla, a __ de __ de __" en Y~206
        draw_text(390, 195, data.get('dia_firma', ''))
        draw_text(430, 195, data.get('mes_firma', ''))
        draw_text(500, 195, data.get('anio_firma', ''))

        c.showPage()  # Fin Página 1

        # --- PÁGINA 2 (ANEXO I) ---
        # D/Dª (nombre): etiqueta Y~644.2, texto Y=644? No, subir un poco.
        draw_text(85, 644, data.get('nombre', ''), size=9)

        # NRP: offset X=395
        draw_text(395, 644, data.get('nrp', ''), size=9)

        # Días: etiqueta Y~631.9, texto Y=620
        draw_text(85, 620, data.get('dias_solicitados', ''), size=9)

        # Motivo: etiqueta Y~619.9, texto Y=608
        motivo_short = (data.get('motivo', '')[:80] + '...') if len(data.get('motivo', '')) > 80 else data.get('motivo', '')
        draw_text(85, 608, motivo_short, size=9)

        # Descripcion justificante: etiqueta Y~595.7, texto Y=583
        draw_text(150, 583, data.get('descripcion_adjunto', ''), size=9)

        c.save()
        packet.seek(0)
        
        # Merge Overlay
        overlay_pdf = PdfReader(packet)
        
        # Merge with existing pages
        # writer already has the cloned pages. We merge page by page.
        if len(writer.pages) >= 1 and len(overlay_pdf.pages) >= 1:
            # Page 1
            writer.pages[0].merge_page(overlay_pdf.pages[0])
            
        if len(writer.pages) >= 2 and len(overlay_pdf.pages) >= 2:
            # Page 2
            writer.pages[1].merge_page(overlay_pdf.pages[1])
            
        # Clean up form fields (flattening is hard in pypdf easily without removing annotations)
        # We just leave them distinct since we are drawing ON TOP.
        # But to avoid user confusion, we can try to remove the form fields or just ensure the text is visible.
        # Usually merging writes content stream on top.



        # Merge the uploaded file if it exists
        if attachment_path:
            try:
                ext = attachment_path.lower().split('.')[-1]
                if ext in ['jpg', 'jpeg', 'png']:
                    img = Image.open(attachment_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img_pdf_io = io.BytesIO()
                    img.save(img_pdf_io, format='PDF')
                    img_pdf_io.seek(0)
                    attachment_reader = PdfReader(img_pdf_io)
                    writer.append(attachment_reader)
                elif ext == 'pdf':
                    attachment_reader = PdfReader(attachment_path)
                    writer.append(attachment_reader)
            except Exception as e_merge:
                print(f"WARNING: Could not merge attachment: {str(e_merge)}")

        # Write result to memory
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        
        # CSV Registration (local for OneDrive syncing)
        # ... (CSV part already updated in previous turn, but keeping consistency)
        try:
            csv_path = 'registros_permisos.csv'
            import csv
            file_exists = os.path.isfile(csv_path)
            # Use 'utf-8-sig' for better Excel compatibility with accents
            with open(csv_path, mode='a', newline='', encoding='utf-8-sig') as f:
                header = ['timestamp', 'nombre', 'dni', 'dias', 'motivo', 'archivo_adjunto']
                writer_csv = csv.DictWriter(f, fieldnames=header)
                if not file_exists:
                    writer_csv.writeheader()
                writer_csv.writerow({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'nombre': data.get('nombre'),
                    'dni': data.get('dni'),
                    'dias': data.get('dias_solicitados'),
                    'motivo': data.get('motivo'),
                    'archivo_adjunto': os.path.basename(attachment_path) if attachment_path else 'N/A'
                })
        except Exception as e_csv:
            print(f"WARNING: CSV Log failed: {str(e_csv)}")
        
        # Encode to Base64
        pdf_base64 = base64.b64encode(output_stream.read()).decode('utf-8')
        print(f"DEBUG: PDF generated successfully for {data.get('nombre')}")
        
        # Extra parameters for visible signature (PAdES)
        # Position is set to cover the area right below "Melilla, a fecha firma electróncio"
        # Original text is around X=375, Y=206. "Fdo.:" is around Y=148.
        fecha_corta = time.strftime('%d/%m/%Y a las %H:%M')
        extra_params = (
            f"signaturePage=1\n"
            f"layer2Text=Firmado digitalmente por {nombre_profe}\\nFecha: {fecha_corta}\n"
            f"signaturePositionOnPageLowerLeftX=320\n"
            f"signaturePositionOnPageLowerLeftY=150\n"
            f"signaturePositionOnPageUpperRightX=550\n"
            f"signaturePositionOnPageUpperRightY=205\n"
            f"signatureCertificationLevel=2\n"
        )
        
        final_filename = f"Solicitud_Permiso_{safe_name}_{timestamp_str}_Rellena.pdf"
        
        return jsonify({
            "status": "success", 
            "pdf_base64": pdf_base64, 
            "filename": final_filename,
            "extra_params": extra_params
        })

    except Exception as e:
        print(f"ERROR in /generate_permiso: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/storage')
@app.route('/retriever')
def dummy_servlets():
    return "OK"

if __name__ == '__main__':
    # Running on 0.0.0.0 to ensure accessibility if needed, debug=True for dev
    app.run(debug=True, port=5001)
