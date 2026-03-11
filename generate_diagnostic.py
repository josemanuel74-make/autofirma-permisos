import os
import io
import re
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics

def get_pdf_anchors(template_path):
    anchors = {}
    if not os.path.exists(template_path): return anchors
    reader = PdfReader(template_path)
    for i, page in enumerate(reader.pages):
        def visitor(text, cm, tm, font_dict, font_size):
            matches = list(re.finditer(r'\{\{([a-zA-Z0-9_]+)', text))
            if not matches: return
            base_x, base_y = tm[4], tm[5]
            for m in matches:
                tag_name = m.group(1)
                preceding = text[:m.start()]
                font_name = 'Helvetica'
                if font_dict and '/BaseFont' in font_dict:
                    fname = font_dict['/BaseFont'].lower()
                    if 'times' in fname: font_name = 'Times-Roman'
                shift_x = pdfmetrics.stringWidth(preceding, font_name, font_size)
                final_x = base_x + shift_x
                key = f'{{{{{tag_name}}}}}'
                if key not in anchors: anchors[key] = []
                if base_x > 0.001 or base_y > 0.001:
                    is_dup = False
                    for existing in anchors[key]:
                        if existing[0] == i and abs(existing[1] - final_x) < 0.5 and abs(existing[2] - base_y) < 0.5:
                            is_dup = True
                            break
                    if not is_dup:
                        anchors[key].append((i, final_x, base_y, font_size))
        page.extract_text(visitor_text=visitor)
    return anchors

def generate_diagnostic():
    template = "Solicitud Permiso Definitivo.pdf"
    labels_template = "Solicitud Permiso Definitivo+etiquetas.pdf"
    anchors = get_pdf_anchors(labels_template)
    
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    
    # Page 1
    c.setStrokeColorRGB(1, 0, 0) # Red for Page 1
    for label, pts in anchors.items():
        for p, x, y, s in pts:
            if p == 0:
                c.rect(x-1, y-1, 10, 10)
                c.setFont("Helvetica", 6)
                c.drawString(x, y+10, f"{label}")
    c.showPage()
    
    # Page 2
    c.setStrokeColorRGB(0, 0, 1) # Blue for Page 2
    for label, pts in anchors.items():
        for p, x, y, s in pts:
            if p == 1:
                # Draw a box exactly where the anchor starts
                c.rect(x-1, y-1, 5, 10)
                # Draw the label name
                c.setFont("Helvetica", 6)
                c.drawString(x, y+12, f"{label}")
                # Draw a sample text starting exactly at x
                c.setFont("Helvetica", 10)
                c.drawString(x, y, "ABC123456")
                print(f"DEBUG: Drawing {label} at P2: {x}, {y}")

    c.save()
    packet.seek(0)
    
    overlay = PdfReader(packet)
    writer = PdfWriter(clone_from=template)
    
    for i in range(len(writer.pages)):
        if i < len(overlay.pages):
            writer.pages[i].merge_page(overlay.pages[i])
            
    with open("DIAGNOSTICO_VERSION_FINAL.pdf", "wb") as f:
        writer.write(f)
    print("Generated DIAGNOSTICO_VERSION_FINAL.pdf")

if __name__ == "__main__":
    generate_diagnostic()
