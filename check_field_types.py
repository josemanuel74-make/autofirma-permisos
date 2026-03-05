from pypdf import PdfReader

reader = PdfReader("Solicitud Permiso.pdf")

print("--- Field Types Analysis ---")
for page in reader.pages:
    if "/Annots" in page:
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/Subtype") == "/Widget":
                ft = obj.get("/FT")
                t = obj.get("/T")
                print(f"Widget T={t} FT={ft}")
