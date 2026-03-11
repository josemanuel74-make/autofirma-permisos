import io
import os
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def create_debug_pdf(template_path, output_path):
    reader = PdfReader(template_path)
    writer = PdfWriter()
    
    for page_index in range(len(reader.pages)):
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        
        # Dibujar rejilla cada 50 puntos
        c.setStrokeColorRGB(0.8, 0.8, 0.8) # Gris claro
        c.setLineWidth(0.5)
        
        for x in range(0, 600, 50):
            c.line(x, 0, x, 842)
            c.setFont("Helvetica", 6)
            c.drawString(x + 2, 10, str(x))
            
        for y in range(0, 850, 50):
            c.line(0, y, 595, y)
            c.setFont("Helvetica", 6)
            c.drawString(10, y + 2, str(y))
            
        # Dibujar coordenadas finas cada 10 puntos
        c.setStrokeColorRGB(0.9, 0.9, 0.9)
        for x in range(0, 600, 10):
            if x % 50 != 0:
                c.line(x, 0, x, 842)
        for y in range(0, 850, 10):
            if y % 50 != 0:
                c.line(0, y, 595, y)

        # Pintar algunos textos de prueba para ver el offset actual
        c.setFillColorRGB(1, 0, 0) # Rojo
        c.setFont("Helvetica-Bold", 10)
        
        if page_index == 0:
            c.drawString(71, 632, "PRUEBA_NOMBRE_A_632")
            c.drawString(132, 562, "NRP_562")
            c.drawString(283, 562, "DNI_562")
            c.drawString(430, 562, "ASIG_562")
        elif page_index == 1:
            c.drawString(85, 644, "D_Dª_644")
            c.drawString(395, 644, "NRP_644")
            c.drawString(85, 620, "DIAS_620")
            
        c.save()
        packet.seek(0)
        
        overlay = PdfReader(packet).pages[0]
        page = reader.pages[page_index]
        page.merge_page(overlay)
        writer.add_page(page)
        
    with open(output_path, "wb") as f:
        writer.write(f)

if __name__ == "__main__":
    template = "Solicitud Permiso Definitivo.pdf"
    output = "DEBUG_COORDENADAS.pdf"
    if os.path.exists(template):
        print(f"Generando {output}...")
        create_debug_pdf(template, output)
        print("Hecho.")
    else:
        print(f"Error: no encuentro {template}")
