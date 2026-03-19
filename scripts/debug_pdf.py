from pypdf import PdfReader, PdfWriter
import io

try:
    writer = PdfWriter(clone_from="Solicitud Permiso Definitivo.pdf")
    
    fields = {
        'NOMBRE Y APELLIDOS DEL PROFESORA': 'Test Name',
        'DNI': '12345678Z',
        'NRP': '123456',
        'ASIGNATURA': 'Informatica',
        'POR EL SIGUIENTE MOTIVO': 'Pruebas',
        'AL AMPARO DEL ARTÍCULO': '73',
        'SOLICITA PERMISO OFICIAL PARA LOS DÍAS': 'Hoy',
        'diasPermiso': '1',
        'A tal efecto el interesado acompaña documento justificativo consistente en': 'Ninguno',
        'Melilla a': '4',
        'de': 'Enero',
        'undefined_3': '2026',
    }
    
    print("Catalog:", writer.root_object)
    
    writer.update_page_form_field_values(writer.pages[0], fields)
    print("Successfully updated fields")

    output = io.BytesIO()
    writer.write(output)
    print("Successfully wrote to stream")
    
except Exception as e:
    print(f"Error: {e}")
