from pypdf import PdfReader, PdfWriter
import os

reader = PdfReader('Solicitud Permiso Definitivo.pdf')
writer = PdfWriter()

fields = reader.get_fields()
fill_data = {}
for field_name in fields:
    fill_data[field_name] = field_name

for page in reader.pages:
    writer.add_page(page)

# This is the old way, but let's try the new way with clone_from
writer = PdfWriter(clone_from='Solicitud Permiso Definitivo.pdf')
for page in writer.pages:
    writer.update_page_form_field_values(page, fill_data)

output_path = 'identify_fields.pdf'
with open(output_path, 'wb') as f:
    writer.write(f)

print(f"Created {output_path}. Please check it to identify fields.")
