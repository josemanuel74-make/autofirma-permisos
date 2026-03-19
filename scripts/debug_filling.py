import os
import io
import sys
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Mock app's get_pdf_anchors
def get_pdf_anchors(template_path):
    import re
    anchors = {}
    if not os.path.exists(template_path): return anchors
    reader = PdfReader(template_path)
    for i, page in enumerate(reader.pages):
        def visitor(text, cm, tm, font_dict, font_size):
            matches = list(re.finditer(r'\{\{([a-zA-Z0-9_]+)\b\}?', text))
            if not matches: return
            base_x, base_y = tm[4], tm[5]
            for m in matches:
                tag_name = m.group(1)
                preceding_text = text[:m.start()]
                shift_x = len(preceding_text) * (font_size * 0.5) if preceding_text else 0
                key = f"{{{{{tag_name}}}}}"
                if key not in anchors: anchors[key] = []
                if base_x > 0.5 or base_y > 0.5:
                    anchors[key].append((i, base_x + shift_x, base_y))
        page.extract_text(visitor_text=visitor)
    return anchors

def debug_filling():
    labels_template = "Solicitud Permiso Definitivo+etiquetas.pdf"
    clean_template = "Solicitud Permiso Definitivo.pdf"
    
    anchors = get_pdf_anchors(labels_template)
    print(f"Detected anchors: {anchors}")

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    
    def get_best_anchor(label, page_idx, target_y_approx):
        if label not in anchors: return None
        matches = [a for a in anchors[label] if a[0] == page_idx]
        if not matches: return None
        return min(matches, key=lambda a: abs(a[2] - target_y_approx))

    def draw_debug(label, placeholder_text, fallback_x, fallback_y, page_idx, size=10):
        anchor = get_best_anchor(label, page_idx, fallback_y)
        if anchor:
            x, y = anchor[1], anchor[2]
            c.setStrokeColorRGB(0, 1, 0) # Green for found
            print(f"Found {label} at {x}, {y} on Page {page_idx+1}")
        else:
            x, y = fallback_x, fallback_y
            c.setStrokeColorRGB(1, 0, 0) # Red for fallback
            print(f"Fallback {label} at {x}, {y} on Page {page_idx+1}")
        
        c.rect(x-2, y-2, 50, 10)
        c.setFont("Helvetica", size)
        c.drawString(x, y, f"{label}:{placeholder_text}")

    # Page 1
    draw_debug('{{nombre}}', 'TEST NOMBRE 1', 85, 618, 0, size=11)
    draw_debug('{{nrp}', 'TEST NRP', 86, 559, 0)
    draw_debug('{{dni}}', 'TEST DNI', 226, 560, 0)
    draw_debug('{{asignatura}}', 'TEST ASIG', 378, 561, 0)
    draw_debug('{{nombre}}', 'TEST FIRMA', 475, 159, 0, size=9)
    c.showPage()
    
    # Page 2
    draw_debug('{{nombre}}', 'TEST NOMBRE 2', 53, 644, 1, size=9)
    draw_debug('{{nrp}}', 'TEST NRP 2', 344, 644, 1, size=9)
    draw_debug('{{motivo}}', 'TEST MOTIVO', 151, 620, 1, size=9)
    c.showPage()
    
    c.save()
    packet.seek(0)
    
    overlay = PdfReader(packet)
    writer = PdfWriter(clone_from=clean_template)
    
    for i in range(len(writer.pages)):
        if i < len(overlay.pages):
            writer.pages[i].merge_page(overlay.pages[i])
            
    with open("DEBUG_FILL_RESULT.pdf", "wb") as f:
        writer.write(f)
    print("Generated DEBUG_FILL_RESULT.pdf")

if __name__ == "__main__":
    debug_filling()
