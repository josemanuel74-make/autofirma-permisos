from pypdf import PdfReader

reader = PdfReader('Solicitud Permiso Definitivo.pdf')

print("--- Field Mapping by Page ---")
for i, page in enumerate(reader.pages):
    print(f"\n[Page {i}]")
    if "/Annots" in page:
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/Subtype") == "/Widget":
                print(f"Name: {obj.get('/T')}, Rect: {obj.get('/Rect')}")
