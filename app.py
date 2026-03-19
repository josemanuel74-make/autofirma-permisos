from flask import Flask, render_template, request, jsonify
import base64
import os
import time
import io
from pypdf import PdfReader, PdfWriter, PageObject
from PIL import Image
import requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# --- CONFIGURATION ---
# Replace this with your actual Power Automate Webhook URLs
WEBHOOK_URL_PERMISO = "https://default70879308da7343a1acdf57810f4ae6.2b.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/6500d208c0ce4a4d91f2e8d313e22aac/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=LI_rqf4S28tioqVtXr2WmztpmdqY4qqnlGjTOSc92mc" 
WEBHOOK_URL_JUSTIFICANTE = "https://default70879308da7343a1acdf57810f4ae6.2b.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/c94fa3e6d5e44c95b834cb47140f9362/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=4l1709SOgNvMKMcPO4jj0x7eHCtvEVKVRiE7LLAsy7I"

def optimize_image_for_pdf(image_content, max_dim=1200):
# ... (existing code for optimize_image_for_pdf)
    """Resizes and compresses an image to reduce PDF size."""
    try:
        img = Image.open(io.BytesIO(image_content))
        # Ensure RGB (removes alpha if any)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large
        w, h = img.size
        if max(w, h) > max_dim:
            if w > h:
                new_w = max_dim
                new_h = int(h * (max_dim / w))
            else:
                new_h = max_dim
                new_w = int(w * (max_dim / h))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        img_pdf_io = io.BytesIO()
        # Save as JPEG inside the PDF container to save space
        img.save(img_pdf_io, format='JPEG', quality=80, optimize=True)
        img_pdf_io.seek(0)
        return img_pdf_io
    except Exception as e:
        print(f"ERROR optimizing image: {e}")
        return io.BytesIO(image_content) # Fallback to original
# ---------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/permisos')
def permisos_form():
    return render_template('solicitud_permiso.html')

@app.route('/justificante')
def justificante_form():
    return render_template('solicitud_justificante.html')

@app.route('/save', methods=['POST'])
def save_signature():
    try:
        data = request.json
        signature_b64 = data.get('signature')
        nombre_original = data.get('nombre', 'Anonimo')
        doc_type = data.get('type', 'permiso') # Default to permiso
        
        nombre_sanitizado = nombre_original.replace(' ', '_')
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # Select Webhook
        target_webhook = WEBHOOK_URL_PERMISO
        if doc_type == 'justificante':
            target_webhook = WEBHOOK_URL_JUSTIFICANTE
            print(f"DEBUG: Using JUSTIFICANTE webhook for type={doc_type}")
        else:
            print(f"DEBUG: Using PERMISO webhook (default) for type={doc_type}")

        # Sanitize filename
        safe_nombre = "".join([c for c in nombre_sanitizado if c.isalnum() or c in ('_', '-')]).rstrip()
        filename = f"Solicitud_{doc_type.capitalize()}_{safe_nombre}_{timestamp}_Firmado.pdf"
        
        print(f"DEBUG: Processing signature for {filename}")

        # --- POWER AUTOMATE INTEGRATION ---
        webhook_status = "skipped"
        if target_webhook:
            try:
                print(f"DEBUG: Sending to Webhook: {target_webhook}")
                # Send all metadata and base64 file as a JSON payload
                payload = data.copy()
                payload.update({
                    'timestamp': timestamp,
                    'filename': filename,
                    'file_base64': signature_b64
                })
                response = requests.post(target_webhook, json=payload)
                print(f"DEBUG: Webhook Response: {response.status_code} - {response.text}")
                if response.ok:
                    webhook_status = "success"
                else:
                    webhook_status = f"failed_http_{response.status_code}"
            except Exception as e_webhook:
                print(f"ERROR: Webhook execution failed: {str(e_webhook)}")
                webhook_status = f"error_{str(e_webhook)}"
        else:
            print("DEBUG: No webhook URL configured for this type. Skipping.")
            webhook_status = "no_url_configured"
        # ----------------------------------

        return jsonify({
            "status": "success", 
            "message": "Signature processed and sent", 
            "webhook_status": webhook_status
        })
    except Exception as e:
        print(f"ERROR in /save: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Removed redundant /permiso route

def get_pdf_anchors(template_path):
    import re
    from reportlab.pdfbase import pdfmetrics
    anchors = {}
    if not os.path.exists(template_path):
        return anchors
    
    try:
        reader = PdfReader(template_path)
        for i, page in enumerate(reader.pages):
            def visitor(text, cm, tm, font_dict, font_size):
                matches = list(re.finditer(r'\{\{([a-zA-Z0-9_]+)', text))
                if not matches:
                    return

                # CM: [a, b, c, d, e, f]
                # Transformation to global coordinates
                ca, cb, cc, cd, ce, cf = cm
                base_x, base_y = tm[4], tm[5]
                
                for m in matches:
                    tag_name = m.group(1)
                    preceding_text = text[:m.start()]
                    
                    font_name = "Helvetica"
                    if font_dict and "/BaseFont" in font_dict:
                        fname = font_dict["/BaseFont"].lower()
                        if "times" in fname: font_name = "Times-Roman"
                        elif "bold" in fname: font_name = "Helvetica-Bold"
                    
                    # Exact shift using reportlab's metrics
                    shift_x = pdfmetrics.stringWidth(preceding_text, font_name, font_size)
                    
                    # Apply CM to calculated local (shift_x, base_y)
                    # Note: We use shift_x relative to tm's base_x
                    local_x = base_x + shift_x
                    local_y = base_y
                    
                    final_x = local_x * ca + local_y * cc + ce
                    final_y = local_x * cb + local_y * cd + cf
                    
                    key = f"{{{{{tag_name}}}}}"
                    if key not in anchors:
                        anchors[key] = []
                    
                    # Deduplication & basic filter (ignore anchors that seem invalid or at 0,0)
                    if abs(final_x) > 10 and abs(final_y) > 10:
                        is_dup = False
                        for existing in anchors[key]:
                            if existing[0] == i and abs(existing[1] - final_x) < 0.5 and abs(existing[2] - final_y) < 0.5:
                                is_dup = True
                                break
                        if not is_dup:
                            anchors[key].append((i, final_x, final_y, font_size))
            
            page.extract_text(visitor_text=visitor)
        return anchors
    except Exception as e:
        print(f"ERROR extracting anchors: {str(e)}")
        return {}

@app.route('/generate_justificante', methods=['POST'])
def generate_justificante():
    try:
        data = request.form
        nombre_profe = data.get('nombre', 'Anonimo')
        absence_mode = data.get('absence_mode', 'specific')
        
        # Robust template path finding
        template_name = "justificacionfaltasprofesores.pdf"
        
        # Try several possible locations
        possible_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), template_name),
            os.path.join(os.getcwd(), template_name),
            template_name
        ]
        
        template_path = None
        for p in possible_paths:
            if os.path.exists(p):
                template_path = p
                break
        
        if not template_path:
            # Case-insensitive fallback
            try:
                base_dirs = [os.path.dirname(os.path.abspath(__file__)), os.getcwd()]
                for d in base_dirs:
                    if os.path.exists(d):
                        for f in os.listdir(d):
                            if f.lower() == template_name.lower():
                                template_path = os.path.join(d, f)
                                break
                    if template_path: break
            except: pass

        if not template_path:
            cwd = os.getcwd()
            return jsonify({
                "status": "error", 
                "message": f"No se encuentra la plantilla: {template_name} en {os.path.dirname(os.path.abspath(__file__))}. (CWD: {cwd})"
            }), 404

        anchors = get_pdf_anchors(template_path)
        
        packet = io.BytesIO()
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.utils import simpleSplit
        c = canvas.Canvas(packet, pagesize=A4)
        
        anchor_key = '<<texto>>'
        matches = anchors.get(anchor_key, [])
        if matches:
            a = matches[0]
            start_x, start_y = a[1], a[2]
        else:
            start_x, start_y = 70, 630

        # 0. HIDE THE ANCHOR MARKER
        c.setFillColor(colors.white)
        # Small white rectangle over the <<texto>> text in the template
        c.rect(start_x - 2, start_y - 2, 60, 15, fill=1, stroke=0)
        c.setFillColor(colors.black)

        # 1. DRAW HEADER TEXT (Using Times-Roman 10pt)
        header_text = (
            f"D/Dª {data.get('nombre', '')} con DNI {data.get('dni', '')} y NRP {data.get('nrp', '')} "
            f"le comunico a usted que no pude asistir al Centro a impartir mis clases y/o el horario "
            f"complementario, los días que a continuación se indican, por los siguientes motivos que igualmente expreso:"
        )
        
        c.setFont("Times-Roman", 10)
        # Use simpleSplit for wrapping
        lines = simpleSplit(header_text, "Times-Roman", 10, 460)
        line_y = start_y
        for line in lines:
            c.drawString(start_x, line_y, line)
            line_y -= 14 # Slightly tighter leading for Times

        # 2. DRAW AUTHENTIC TABLE
        table_top = line_y - 25
        col_x = [70, 160, 215, 275, 530] # Column boundaries
        
        # Draw table header background (Lighter Grey)
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(col_x[0], table_top - 20, col_x[4] - col_x[0], 20, fill=1, stroke=0)
        c.setFillColor(colors.black)

        # Draw table headers
        c.setFont("Times-Bold", 10)
        c.drawString(col_x[0] + 5, table_top - 15, "DÍA")
        c.drawString(col_x[1] + 5, table_top - 15, "HORA")
        c.drawString(col_x[2] + 5, table_top - 15, "CURSO")
        c.drawString(col_x[3] + 5, table_top - 15, "MOTIVOS")
        
        # Header Grid Lines
        c.setLineWidth(1.2)
        c.line(col_x[0], table_top, col_x[4], table_top) # Top line
        c.line(col_x[0], table_top - 20, col_x[4], table_top - 20) # Under header line
        
        # Prepare Data Rows
        rows_to_draw = []
        if absence_mode == 'range':
            f_ini, f_fin = data.get('fecha_inicio', ''), data.get('fecha_fin', '')
            try:
                if '-' in f_ini: f_ini = "/".join(f_ini.split('-')[::-1])
                if '-' in f_fin: f_fin = "/".join(f_fin.split('-')[::-1])
            except: pass
            motivo = data.get('motivo_general', '')
            rows_to_draw.append({'dia': f"Desde {f_ini}", 'hora': "Todas", 'curso': "Todos", 'motivo': motivo})
            rows_to_draw.append({'dia': f"Hasta {f_fin}", 'hora': "Todas", 'curso': "Todos", 'motivo': motivo})
        else:
            dias, horas, cursos, motivos = request.form.getlist('fila_dia[]'), request.form.getlist('fila_hora[]'), request.form.getlist('fila_curso[]'), request.form.getlist('fila_motivo[]')
            for i in range(len(dias)):
                d = dias[i]
                if '-' in d: d = "/".join(d.split('-')[::-1])
                rows_to_draw.append({'dia': d, 'hora': horas[i], 'curso': cursos[i], 'motivo': motivos[i]})

        # Draw Data Rows and Grid
        row_y = table_top - 20
        c.setFont("Times-Roman", 10)
        c.setLineWidth(0.5)
        
        for r in rows_to_draw:
            if row_y < 180: break # Avoid overlapping signature
            
            c.drawString(col_x[0] + 5, row_y - 14, r['dia'])
            c.drawString(col_x[1] + 5, row_y - 14, r['hora'])
            c.drawString(col_x[2] + 5, row_y - 14, r['curso'])
            m_text = r['motivo'][:52] + "..." if len(r['motivo']) > 55 else r['motivo']
            c.drawString(col_x[3] + 5, row_y - 14, m_text)
            
            row_y -= 20
            c.line(col_x[0], row_y, col_x[4], row_y) # Bottom line of the row
        
        # Vertical Lines for the grid (Uniform 0.5 grid)
        c.setLineWidth(0.5)
        for x in col_x:
            c.line(x, table_top, x, row_y)

        # 3. FOOTER TEXT (Times-Roman 10pt)
        row_y -= 25
        c.setFont("Times-Roman", 10)
        c.drawString(start_x, row_y, "Lo que participo a usted a los efectos oportunos.")

        # Prepare Overlay
        c.save()
        packet.seek(0)
        overlay_reader = PdfReader(packet)
        
        # Merge with template
        reader = PdfReader(template_path)
        writer = PdfWriter()
        
        # Add template pages (merging overlay on page 1)
        for i in range(len(reader.pages)):
            page = reader.pages[i]
            if i == 0:
                page.merge_page(overlay_reader.pages[0])
            writer.add_page(page)

        # 4. APPEND ATTACHMENT
        adjunto_content = None
        adjunto_ext = None
        
        if 'archivo_adjunto' in request.files:
            f = request.files['archivo_adjunto']
            if f.filename != '':
                adjunto_content = f.read()
                adjunto_ext = f.filename.split('.')[-1].lower()
        
        if not adjunto_content and data.get('adjunto_base64'):
            try:
                adjunto_content = base64.b64decode(data.get('adjunto_base64'))
                adjunto_name = data.get('adjunto_nombre', 'archivo')
                adjunto_ext = adjunto_name.split('.')[-1].lower()
            except: pass

        if adjunto_content:
            try:
                if adjunto_ext in ['jpg', 'jpeg', 'png']:
                    img_pdf_io = optimize_image_for_pdf(adjunto_content)
                    writer.append(PdfReader(img_pdf_io))
                elif adjunto_ext == 'pdf':
                    writer.append(PdfReader(io.BytesIO(adjunto_content)))
            except Exception as e_merge:
                print(f"WARNING: Could not merge attachment to justificante: {str(e_merge)}")

        for page in writer.pages:
            page.compress_content_streams() # Compress PDF content
        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        pdf_b64 = base64.b64encode(out.read()).decode('utf-8')
        
        fecha_corta = time.strftime('%d/%m/%Y a las %H:%M')
        extra = (
            f"signaturePage=1\n"
            f"layer2Text=Firmado digitalmente por {nombre_profe}\\nFecha: {fecha_corta}\n"
            f"signaturePositionOnPageLowerLeftX=320\n"
            f"signaturePositionOnPageLowerLeftY=170\n"
            f"signaturePositionOnPageUpperRightX=550\n"
            f"signaturePositionOnPageUpperRightY=225\n"
            f"signatureCertificationLevel=2\n"
        )
        print(f"DEBUG: Justificante generated. PDF Size: {len(pdf_b64)} chars. ExtraParams:\n{extra}")
        return jsonify({"status": "success", "pdf_base64": pdf_b64, "extra_params": extra})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

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
        # Background: Clean version for rendering
        # Coordination: Tagged version for anchors
        template_render = "Solicitud Permiso Definitivo.pdf"
        template_anchors = "Solicitud Permiso Definitivo+etiquetas.pdf"
        
        if not os.path.exists(template_render):
            template_render = template_anchors # Fallback if clean is missing
            
        writer = PdfWriter(clone_from=template_render)



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
        # We use the tagged template to find anchors
        anchors = get_pdf_anchors(template_anchors)
        
        def hide_anchors_on_page(page_idx):
            # User requested to remove the white-box approach
            pass
        
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
        # Actually, let's just use the helper to find the best match by Y coordinate if multiple exist.
        def get_best_anchor(label, page_idx, target_y_approx):
            if label not in anchors: return None
            matches = [a for a in anchors[label] if a[0] == page_idx]
            if not matches: return None
            # Return match with closest Y
            return min(matches, key=lambda a: abs(a[2] - target_y_approx))

        def draw_smart(label, text, fallback_x, fallback_y, page_idx, size=None, multiline=False, width=450, offset_x=0):
            anchor = get_best_anchor(label, page_idx, fallback_y)
            # Use detected size if available, otherwise use provided or default 10
            draw_size = anchor[3] if anchor and len(anchor) > 3 else (size or 10)
            x, y = (anchor[1], anchor[2]) if anchor else (fallback_x, fallback_y)
            
            # Apply manual offset if provided
            x += offset_x
            
            if multiline:
                draw_multiline(x, y, text, width, draw_size)
            else:
                draw_text(x, y, text, draw_size)

        # PÁGINA 1
        hide_anchors_on_page(0)
        draw_smart('{{nombre}}', data.get('nombre', ''), 85, 618, 0, size=11)
        draw_smart('{{nrp}}', data.get('nrp', ''), 86, 558, 0) # Aligned with NRP tag
        draw_smart('{{dni}}', data.get('dni', ''), 235, 558.6, 0)
        draw_smart('{{asignatura}}', data.get('asignatura', ''), 390, 558.6, 0) # Shifted right from previous 380
        
        # Use multiline for dias and motivo on BOTH pages if needed
        draw_smart('{{dias_solicitados}}', data.get('dias_solicitados', ''), 82, 458, 0, multiline=True, width=450)
        draw_smart('{{motivo}}', data.get('motivo', ''), 82, 354, 0, multiline=True, width=450)
        
        draw_smart('{{articulo}}', data.get('articulo', ''), 207, 253, 0)
        # Applying same fix as Page 2: lowering Y (159->150) and shifting left (-70px)
        draw_smart('{{nombre}}', data.get('nombre', ''), 475, 150, 0, size=9, offset_x=-70)

        c.showPage()  # Fin Página 1

        # --- PÁGINA 2 (ANEXO I) ---
        hide_anchors_on_page(1)
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
        # Reverting Page 2 to its original stable position
        draw_smart('{{nombre}}', data.get('nombre', ''), 297, 317, 1)
        # New NRP tag at the end of page 2
        draw_smart('{{nrp}}', data.get('nrp', ''), 108, 304, 1)

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
                    img_pdf_io = optimize_image_for_pdf(content)
                    attachment_reader = PdfReader(img_pdf_io)
                    writer.append(attachment_reader)
                elif ext == 'pdf':
                    attachment_reader = PdfReader(io.BytesIO(content))
                    writer.append(attachment_reader)
            except Exception as e_merge:
                print(f"WARNING: Could not merge attachment: {str(e_merge)}")

        for page in writer.pages:
            page.compress_content_streams() # Compress PDF content
        # Write result to memory
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        
        # CSV Registration removed (now handled by Power Automate)
        
        # Encode to Base64
        pdf_base64 = base64.b64encode(output_stream.read()).decode('utf-8')
        print(f"DEBUG: PDF generated successfully for {data.get('nombre')}")
        
        # Extra parameters for visible signature (PAdES)
        # Moving it slightly up (Y from 150->160 and 205->215) to avoid overlapping "Fdo.:"
        fecha_corta = time.strftime('%d/%m/%Y a las %H:%M')
        extra_params = (
            f"signaturePage=1\n"
            f"layer2Text=Firmado digitalmente por {nombre_profe}\\nFecha: {fecha_corta}\n"
            f"signaturePositionOnPageLowerLeftX=320\n"
            f"signaturePositionOnPageLowerLeftY=160\n"
            f"signaturePositionOnPageUpperRightX=550\n"
            f"signaturePositionOnPageUpperRightY=215\n"
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

# --- SERVLETS FOR MOBILE / MINIAPPLET SUPPORT ---
# Temporary storage for signatures during the out-of-band mobile signing process.
# Mapping: string identifier (v) -> base64 signature data
signature_storage = {}

def make_cors_response(content, status=200):
    from flask import Response
    resp = Response(content, status=status, mimetype='text/plain')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route('/storage', methods=['GET', 'POST', 'OPTIONS'])
def storage_servlet():
    if request.method == 'OPTIONS':
        return make_cors_response("")

    # Robust parameter detection (args, form, or json)
    op = request.args.get('op') or request.form.get('op')
    v = request.args.get('v') or request.form.get('v')
    
    print(f"DEBUG: /storage method={request.method} op={op} v={v}")
    
    if op == 'check':
        return make_cors_response("OK")
    
    if op == 'put':
        # Data can be in 'dat' param or raw body
        data = request.form.get('dat') or request.get_data()
        if v and data:
            if isinstance(data, bytes):
                try:
                    data = data.decode('utf-8')
                except:
                    import base64
                    data = base64.b64encode(data).decode('utf-8')
            signature_storage[v] = data
            print(f"DEBUG: /storage SUCCESS v={v} size={len(data)}")
            return make_cors_response("OK")
            
    return make_cors_response("BadRequest", 400)

@app.route('/retriever', methods=['GET', 'POST', 'OPTIONS'])
def retriever_servlet():
    if request.method == 'OPTIONS':
        return make_cors_response("")

    op = request.args.get('op') or request.form.get('op')
    v = request.args.get('v') or request.form.get('v')
    
    print(f"DEBUG: /retriever op={op} v={v}")
    
    if op == 'check':
        return make_cors_response("OK")
        
    if op == 'get':
        if v and v in signature_storage:
            data = signature_storage[v]
            print(f"DEBUG: /retriever SUCCESS v={v}")
            return make_cors_response(data)
        print(f"DEBUG: /retriever NOT FOUND v={v}")
        return make_cors_response("NotFound", 404)
        
    return make_cors_response("BadRequest", 400)

if __name__ == '__main__':
    # Running on 0.0.0.0 to ensure accessibility if needed, debug=True for dev
    app.run(debug=True, port=5001)
