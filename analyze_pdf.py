from pypdf import PdfReader

reader = PdfReader('Solicitud Permiso Definitivo.pdf')
print(f"Total Pages: {len(reader.pages)}")

# Print all form fields with their names and values
fields = reader.get_fields()
print("\n--- All Form Fields ---")
for field_name, field_data in fields.items():
    print(f"Field Name: {field_name}")
    # print(f"Field Data: {field_data}") # Too much info

print("\n--- Page by Page Fields ---")
for i, page in enumerate(reader.pages):
    print(f'--- Page {i} ---')
    if '/Annots' in page:
        for annot in page['/Annots']:
            obj = annot.get_object()
            if obj.get('/Subtype') == '/Widget':
                field_name = obj.get('/T')
                field_type = obj.get('/FT')
                print(f"Name: {field_name}, Type: {field_type}")
