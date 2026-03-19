from pypdf import PdfReader

reader = PdfReader("Solicitud Permiso.pdf")

print("--- Root AcroForm ---")
if "/AcroForm" in reader.root_object:
    acro = reader.root_object["/AcroForm"]
    print(f"NeedAppearances: {acro.get('/NeedAppearances')}")
    print(f"DA (Global): {acro.get('/DA')}")
    if "/DR" in acro:
        print(f"DR (Resources): {acro['/DR'].keys()}")
        if "/Font" in acro["/DR"]:
            print(f"Fonts: {acro['/DR']['/Font'].keys()}")

print("\n--- Field Analysis ---")
fields = reader.get_fields()
if fields:
    for name, field in list(fields.items())[:5]: # Check first 5 fields
        print(f"Field: {name}")
        # We need to access the raw object to see /DA
        # pypdf's get_fields returns a dictionary of data, not the object itself usually in a simple way
        # Let's try to find the object via pages
        pass

# Low level traversal to find widgets
for page in reader.pages:
    if "/Annots" in page:
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/Subtype") == "/Widget":
                print(f"Widget T={obj.get('/T')} DA={obj.get('/DA')}")
