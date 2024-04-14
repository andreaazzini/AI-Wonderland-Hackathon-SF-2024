from pdfrw import PdfReader, PdfWriter, IndirectPdfDict
import pdfrw
from pdfrw import PdfReader
import pdfplumber


def fill_pdf(input_pdf_path, output_pdf_path, data_dict, options_dict):
    template_pdf = PdfReader(input_pdf_path)
    for page in template_pdf.pages:
        annotations = page["/Annots"]
        if annotations:
            for annotation in annotations:
                if annotation["/Subtype"] == "/Widget" and "/T" in annotation:
                    field_name = annotation["/T"][1:-1]  # Strip parentheses
                    if field_name in data_dict:
                        value = data_dict[field_name]
                        annotation.update(pdfrw.PdfDict(V=value))
                        # Update the index for list boxes if options are provided
                        if field_name in options_dict and value in options_dict[field_name]:
                            index = options_dict[field_name].index(value)
                            annotation.update(pdfrw.PdfDict(I=[pdfrw.PdfObject(str(index))]))
                        annotation.update(pdfrw.PdfDict(AP=""))  # Attempt to reset the appearance dictionary
    PdfWriter().write(output_pdf_path, template_pdf)


def hex_to_text(hex_str):
    if hex_str.startswith("<FEFF"):
        return bytes.fromhex(hex_str[5:-1]).decode("utf-16-be")
    return hex_str


def checkbox_to_bool(value):
    return not value == "/Off"


def extract_form_data_and_options(pdf_path):
    template_pdf = PdfReader(pdf_path)
    form_fields = {}
    form_options = {}  # To store options for list boxes and checkbox states

    for page in template_pdf.pages:
        annotations = page["/Annots"]
        if annotations is None:
            continue  # No annotations on this page
        for annotation in annotations:
            if annotation["/Subtype"] == "/Widget":
                field_name = annotation["/T"][1:-1] if "/T" in annotation else None
                field_value = None
                if "/V" in annotation:
                    raw_value = annotation["/V"]
                    if isinstance(raw_value, str):
                        if raw_value.startswith("/"):
                            field_value = checkbox_to_bool(raw_value)
                        else:
                            field_value = hex_to_text(raw_value)
                if field_name:
                    form_fields[field_name] = field_value
                if "/Opt" in annotation:
                    # Extract options for list boxes or combo boxes
                    options = annotation["/Opt"]
                    options_list = [
                        hex_to_text(opt[0]) if isinstance(opt, list) else hex_to_text(opt) for opt in options
                    ]
                    form_options[field_name] = options_list
                elif "/FT" in annotation and annotation["/FT"] == "/Btn":  # Check if field is a button (checkbox/radio)
                    if "/AP" in annotation and "/N" in annotation["/AP"]:
                        states = annotation["/AP"]["/N"]
                        # Assuming the "On" state is not the standard "/Yes", extract it
                        on_state = [key for key in states.keys() if key != "/Off"]
                        if on_state:
                            form_options[field_name] = {"type": "checkbox", "on_state": on_state[0]}
                    else:
                        form_options[field_name] = {"type": "checkbox", "on_state": "/Yes"}  # Default assumption

    return form_fields, form_options


def extract_ocr_text(pdf_path):
    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:  # Check if there's any text extracted
                all_text += page_text + "\n"
    return all_text
