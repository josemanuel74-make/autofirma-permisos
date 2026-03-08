import os
import sys
# Add current dir to path to import from app
sys.path.append(os.getcwd())
from app import get_pdf_anchors

template = "Solicitud Permiso Definitivo+etiquetas.pdf"
print(f"Testing anchors for: {template}")
anchors = get_pdf_anchors(template)

expected_labels = ['{{nombre}}', '{{nrp}}', '{{dni}}', '{{articulo}}']
for label in expected_labels:
    # Some labels might have slight variations in the PDF, let's check
    found = False
    for k in anchors.keys():
        if label in k:
            print(f"MATCH: {label} -> {k}: {anchors[k]}")
            found = True
    if not found:
        print(f"MISSING: {label}")

print("\nAll detected anchors:")
for k, v in anchors.items():
    print(f"  {k}: {v}")
