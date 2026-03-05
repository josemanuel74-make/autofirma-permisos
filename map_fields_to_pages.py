from pypdf import PdfReader

reader = PdfReader('Solicitud Permiso Definitivo.pdf')
fields = reader.get_fields()

print("--- Field to Page Mapping ---")
for field_name, field_data in fields.items():
    # field_data is sometimes a list of widget dictionaries
    widgets = field_data.get('/Kids', [field_data])
    pages = []
    # This is slightly complex in pypdf, but we can try to find the page index
    # However, a easier way is to check the /P entry if it exists
    # Or just iterate all pages and check if the field's object ID is in the annots
    
    # Let's use a simpler approach: iterate pages and check /Annots
    pass

for i, page in enumerate(reader.pages):
    print(f"\n[Page {i}]")
    if "/Annots" in page:
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/Subtype") == "/Widget":
                print(f"Field: {obj.get('/T')}, Type: {obj.get('/FT')}")
