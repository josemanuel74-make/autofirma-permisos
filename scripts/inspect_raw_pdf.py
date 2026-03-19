import os
from pypdf import PdfReader

def inspect_content_stream(template_path):
    if not os.path.exists(template_path): return
    reader = PdfReader(template_path)
    page = reader.pages[0]
    
    # Get the raw content stream
    content = page.get_contents()
    if isinstance(content, list):
        data = b"".join([c.get_data() for c in content])
    else:
        data = content.get_data()
        
    print("--- Inspecting Content Stream (Raw) ---")
    # Search for patterns like ({{dni}}) Tj or [({{dni}})] TJ
    for tag in [b'{{dni}}', b'{{asignatura}}', b'{{nrp}}']:
        idx = data.find(tag)
        if idx != -1:
            print(f"Found tag {tag} in raw content stream at index {idx}")
            # Show surrounding context
            start = max(0, idx - 50)
            end = min(len(data), idx + 100)
            print(f"Context: {data[start:end]}")

if __name__ == "__main__":
    template = "Solicitud Permiso Definitivo+etiquetas.pdf"
    inspect_content_stream(template)
