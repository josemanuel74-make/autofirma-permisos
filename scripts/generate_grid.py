import os
import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

def draw_grid(template_path, output_path):
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found.")
        return

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    
    # Draw Grid
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.3)
    c.setFont("Helvetica", 6)
    
    for x in range(0, 600, 20):
        c.line(x, 0, x, 842)
        c.drawString(x, 10, str(x))
        
    for y in range(0, 850, 20):
        c.line(0, y, 595, y)
        c.drawString(10, y, str(y))
        
    # Draw minor grid
    c.setStrokeColor(colors.whitesmoke)
    c.setLineWidth(0.1)
    for x in range(0, 600, 5):
        if x % 20 != 0: c.line(x, 0, x, 842)
    for y in range(0, 850, 5):
        if y % 20 != 0: c.line(0, y, 595, y)

    c.save()
    packet.seek(0)
    
    overlay = PdfReader(packet)
    reader = PdfReader(template_path)
    writer = PdfWriter()
    
    for i in range(len(reader.pages)):
        page = reader.pages[i]
        if i < len(overlay.pages):
            page.merge_page(overlay.pages[0])
        writer.add_page(page)
        
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"Grid PDF generated: {output_path}")

if __name__ == "__main__":
    draw_grid("Solicitud Permiso Definitivo.pdf", "GRID_SOLICITUD.pdf")
