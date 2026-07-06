import pymupdf
import base64


def read_invoice_document(pdf_path: str):
    pages = []

    try:
        with pymupdf.open(pdf_path) as doc:
            for idx, page in enumerate(doc):
                text = page.get_text("text") or ""

                pix = page.get_pixmap(dpi=100)
                image_bytes = pix.tobytes("png")

                pages.append({
                    "page_number": idx + 1,
                    "text": text,
                    "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
                })

    except Exception as e:
        return {
            "error": f"Failed to read PDF: {e}"
        }

    return {
        "pages": pages,
        "extracted_text": "\n\n".join(
            f"-- PAGE {page['page_number']} --\n{page['text']}"
            for page in pages
        )
    }


return_data = read_invoice_document("./data/Invoice.pdf")

print(return_data)