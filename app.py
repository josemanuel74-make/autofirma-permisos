from flask import Flask, render_template, request, jsonify
import base64
import os
import time
import io
from pypdf import PdfReader, PdfWriter, PageObject
from PIL import Image
import requests

app = Flask(__name__)

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
        
        print(f"DEBUG: Processing signature for {filename}")
        # We no longer save the file locally.

        # --- POWER AUTOMATE INTEGRATION ---
        webhook_status = "skipped"
        if WEBHOOK_URL:
            try:
                print(f"DEBUG: Sending to Webhook: {WEBHOOK_URL}")
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
            "message": "Signature processed and sent", 
            "webhook_status": webhook_status
        })
    except Exception as e:
        print(f"ERROR in /save: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/permiso')
def permiso_form():
    return render_template('solicitud_permiso.html')

def get_pdf_anchors(template_path):
    """
    Scans a PDF for labels like {{label}} and returns their coordinates.
    High precision: uses reportlab's stringWidth for exact shifting.
    """
    import re
    from reportlab.pdfbase import pdfmetrics
    anchors = {}
    if not os.path.exists(template_path):
        return anchors
    
    try:
        reader = PdfReader(template_path)
        for i, page in enumerate(reader.pages):
            def visitor(text, cm, tm, font_dict, font_size):
                # We normalize the search to be more lenient
                matches = list(re.finditer(r'\{\{([a-zA-Z0-9_]+)\b\}?', text))
                if not matches:
                    return

                # Calculate base coordinates
                base_x = tm[4]
                base_y = tm[5]
                
                for m in matches:
                    tag_name = m.group(1)
                    preceding_text = text[:m.start()]
                    
                    # Detect font type for more accurate width calculation
                    font_name = "Helvetica"
                    if font_dict and "/BaseFont" in font_dict:
                        fname = font_dict["/BaseFont"].lower()
                        if "times" in fname: font_name = "Times-Roman"
                        elif "bold" in fname: font_name = "Helvetica-Bold"
                    
                    # Exact shift using reportlab's metrics
                    shift_x = pdfmetrics.stringWidth(preceding_text, font_name, font_size)
                    
                    key = f"{{{{{tag_name}}}}}" # Canonical form {{name}}
                    if key not in anchors:
                        anchors[key] = []
                    
                    # Reject (0,0) as it's usually a coordinate system error in visitor
                    if base_x > 0.001 or base_y > 0.001:
                        # Store (page, x, y, size)
                        anchors[key].append((i, base_x + shift_x, base_y, font_size))
            
            page.extract_text(visitor_text=visitor)
    except Exception as e:
        print(f"ERROR extracting anchors: {str(e)}")
    
    return anchors

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
        attachment_data = None
        justificacion_text = data.get('descripcion_adjunto', 'No adjunto')
        
        nombre_profe = data.get('nombre', 'Anonimo').replace(' ', '_')
        # Sanitize name for filesystem
        safe_name = "".join([c for c in nombre_profe if c.isalnum() or c in ('_', '-')]).rstrip()
        timestamp_str = time.strftime('%Y%m%d_%H%M%S')

        if 'justificacion_file' in files:
            file = files['justificacion_file']
            if file.filename != '':
                ext = file.filename.split('.')[-1].lower()
                attachment_content = file.read()
                attachment_data = {
                    'ext': ext,
                    'content': attachment_content,
                    'filename': file.filename
                }
        
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

        # --- DYNAMIC ANCHOR APPROACH ---
        # We use the '+etiquetas' version to find WHERE to draw, 
        # but we draw on the 'Definitivo' version to keep it clean.
        labels_template = "Solicitud Permiso Definitivo+etiquetas.pdf"
        anchors = get_pdf_anchors(labels_template)
        
        # Helper to draw using anchors with fallback
        def draw_at_anchor(label, text, fallback_x, fallback_y, page_idx=0, size=10, multiline=False, width=450, occurrence=0):
            if not text: return
            
            x, y = fallback_x, fallback_y
            found_page = page_idx
            
            # Check if we have this anchor
            if label in anchors:
                matches = [a for a in anchors[label] if a[0] == page_idx]
                if matches and len(matches) > occurrence:
                    found_page, x, y, detected_size = matches[occurrence]
                elif matches: # fallback to first match on that page if occurrence not found
                    found_page, x, y, detected_size = matches[0]
            
            # Switch page if needed (though we usually handle pages sequentially)
            # For simplicity in this logic, we assume we are on the correct c.showPage() cycle
            
            if multiline:
                draw_multiline(x, y, text, width, size)
            else:
                draw_text(x, y, text, size)

        # --- PÁGINA 1 (ANEXO II) ---
        # NOMBRE: {{nombre}} (primera aparición en pág 1)
        draw_at_anchor('{{nombre}}', data.get('nombre', ''), 85, 618, page_idx=0, size=11, occurrence=1) # The one at top is actually 2nd in extraction order sometimes, let's use occurrence logic or coordinate logic.
        # Wait, my research showed:
        # Page 1: {{nombre}} at (85.09, 618.14)
        # Page 1: {{nombre}} at (474.90, 159.02)
        # In my manual extraction, 159.02 came first? Let's check.
        # Page 1: {{articulo}} at (207.37, 252.57)
        # Page 1: {{nombre}} at (474.90, 159.02)
        # Page 1: {{nombre}} at (85.09, 618.14)
        
        # Actually, let's just use the helper to find the best match by Y coordinate if multiple exist.
        def get_best_anchor(label, page_idx, target_y_approx):
            if label not in anchors: return None
            matches = [a for a in anchors[label] if a[0] == page_idx]
            if not matches: return None
            # Return match with closest Y
            return min(matches, key=lambda a: abs(a[2] - target_y_approx))

        def draw_smart(label, text, fallback_x, fallback_y, page_idx, size=None, multiline=False, width=450):
            anchor = get_best_anchor(label, page_idx, fallback_y)
            # Use detected size if available, otherwise use provided or default 10
            draw_size = anchor[3] if anchor and len(anchor) > 3 else (size or 10)
            x, y = (anchor[1], anchor[2]) if anchor else (fallback_x, fallback_y)
            
            if multiline:
                draw_multiline(x, y, text, width, draw_size)
            else:
                draw_text(x, y, text, draw_size)

        # PÁGINA 1
        draw_smart('{{nombre}}', data.get('nombre', ''), 85, 618, 0, size=11)
        draw_smart('{{nrp}}', data.get('nrp', ''), 86, 559, 0) # Use canonical key
        draw_smart('{{dni}}', data.get('dni', ''), 226, 560, 0)
        draw_smart('{{asignatura}}', data.get('asignatura', ''), 378, 561, 0)
        
        # Use multiline for dias and motivo on BOTH pages if needed
        draw_smart('{{dias_solicitados}}', data.get('dias_solicitados', ''), 82, 458, 0, multiline=True, width=450)
        draw_smart('{{motivo}}', data.get('motivo', ''), 82, 354, 0, multiline=True, width=450)
        
        draw_smart('{{articulo}}', data.get('articulo', ''), 207, 253, 0)
        draw_smart('{{nombre}}', data.get('nombre', ''), 475, 159, 0, size=9)

        c.showPage()  # Fin Página 1

        # --- PÁGINA 2 (ANEXO I) ---
        draw_smart('{{nombre}}', data.get('nombre', ''), 53, 644, 1)
        draw_smart('{{nrp}}', data.get('nrp', ''), 344, 644, 1)
        draw_smart('{{dias_solicitados}}', data.get('dias_solicitados', ''), 299, 632, 1)
        
        motivo_val = data.get('motivo', '')
        # For motivo on page 2, if it's long we use a smaller font and multiline
        if len(motivo_val) > 60:
            draw_smart('{{motivo}}', motivo_val, 151, 620, 1, size=8, multiline=True, width=380)
        else:
            draw_smart('{{motivo}}', motivo_val, 151, 620, 1)
        
        draw_smart('{{justificante}}', data.get('descripcion_adjunto', ''), 150, 570, 1)
        draw_smart('{{nombre}}', data.get('nombre', ''), 297, 317, 1)

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
        if attachment_data:
            try:
                ext = attachment_data['ext']
                content = attachment_data['content']
                if ext in ['jpg', 'jpeg', 'png']:
                    img = Image.open(io.BytesIO(content))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img_pdf_io = io.BytesIO()
                    img.save(img_pdf_io, format='PDF')
                    img_pdf_io.seek(0)
                    attachment_reader = PdfReader(img_pdf_io)
                    writer.append(attachment_reader)
                elif ext == 'pdf':
                    attachment_reader = PdfReader(io.BytesIO(content))
                    writer.append(attachment_reader)
            except Exception as e_merge:
                print(f"WARNING: Could not merge attachment: {str(e_merge)}")

        # Write result to memory
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        
        # CSV Registration removed (now handled by Power Automate)
        
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
