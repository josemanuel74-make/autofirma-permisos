import os
import re
from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics

def debug_anchors_deep(template_path):
    if not os.path.exists(template_path): return
    reader = PdfReader(template_path)
    page = reader.pages[0]
    
    print(f"--- Deep Anchor Search Page 0 ---")
    
    # Store all found text with their coordinates
    all_text = []
    
    def visitor(text, cm, tm, font_dict, font_size):
        if text.strip():
            all_text.append({
                'text': text,
                'x': tm[4],
                'y': tm[5],
                'font_size': font_size,
                'font_dict': font_dict
            })
            
    page.extract_text(visitor_text=visitor)
    
    for item in all_text:
        # Search for tags even if they have spaces or are partial
        if '{{' in item['text']:
            print(f"FOUND TAG CANDIDATE: '{item['text']}' at X={item['x']:.2f}, Y={item['y']:.2f}")
            # Try to see if it's split
            
    # Print the neighbors of {{nrp}} to find dni and asignatura
    nrp_y = None
    for item in all_text:
        if '{{nrp}}' in item['text']:
            nrp_y = item['y']
            print(f"NRP reference found at Y={nrp_y}")
            break
            
    if nrp_y is not None:
        print(f"--- Items near Y={nrp_y} (+/- 20 pts) ---")
        for item in all_text:
            if abs(item['y'] - nrp_y) < 20:
                print(f"Text: '{item['text']}' | X={item['x']:.2f}, Y={item['y']:.2f}")

if __name__ == "__main__":
    template = "Solicitud Permiso Definitivo+etiquetas.pdf"
    debug_anchors_deep(template)
