from pypdf import PdfReader

reader = PdfReader("Solicitud Permiso.pdf")

if "/AcroForm" in reader.root_object:
    acro = reader.root_object["/AcroForm"]
    if "/DR" in acro and "/Font" in acro["/DR"]:
        fonts = acro["/DR"]["/Font"]
        if "/Helv" in fonts:
            helv = fonts["/Helv"].get_object()
            print(f"Helv Object: {helv}")
            encoding = helv.get("/Encoding")
            print(f"Encoding: {encoding}")
            if isinstance(encoding, dict) and "/Differences" in encoding:
                diffs = encoding["/Differences"]
                
                print("--- Mapping for /Helv ---")
                current_code = 0
                mapping = {}
                
                for item in diffs:
                    if isinstance(item, int):
                        current_code = item
                    else:
                        # item is a NameObject, e.g. /Agrave
                        name = str(item).replace('/', '')
                        # mapping[name] = current_code
                        print(f"Code {current_code} (0x{current_code:02x}) -> {name}")
                        current_code += 1
        else:
            print("Helv font not found in /AcroForm/DR/Font")
    else:
        print("Required font structure not found")
else:
    print("No /AcroForm found")
