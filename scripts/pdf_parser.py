from pypdf import PdfReader

def read_invoice_document(pdf_path: str):
    text_content = []

    try:
        reader = PdfReader(pdf_path)
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text_content.append(f"-- PAGE {idx+1} -- \n{text}")
    except Exception as e:
        text_content = [f"Text extraction failed: {e}"]

    return {
        "extracted_text": "\n\n".join(text_content)
    }


return_data = read_invoice_document("./data/Invoice.pdf")

print(return_data["extracted_text"])