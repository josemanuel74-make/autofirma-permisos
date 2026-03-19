import os
from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics

def extract_text_coords(template_path):
    if not os.path.exists(template_path): return
    reader = PdfReader(template_path)
    page = reader.pages[0]
    
    print(f"--- Text Extraction Page 0 ---")
    def visitor(text, cm, tm, font_dict, font_size):
        if text.strip():
            print(f"Text: '{text}' | Coords: X={tm[4]:.2f}, Y={tm[5]:.2f} | CM: {cm}")
            
    page.extract_text(visitor_text=visitor)

if __name__ == "__main__":
    template = "Solicitud Permiso Definitivo+etiquetas.pdf"
    extract_text_coords(template)
