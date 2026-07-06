import pymupdf
import base64


def read_invoice_document(pdf_path: str) -> dict:
    pages = []

    try:
        with pymupdf.open(pdf_path) as invoice_doc:
            for page_number, page in enumerate(invoice_doc, start=1):
                text = page.get_text("text") or ""

                page_data = {
                    "page_number": page_number,
                    "text": text,
                }

                # Only generate image if the PDF page contains images
                if page.get_images(full=True):
                    pix = page.get_pixmap(dpi=100)
                    image_bytes = pix.tobytes("png")

                    # # Save locally for inspection
                    # image_path = f"page_{page_number}.png"
                    # pix.save(image_path)

                    page_data["image_base64"] = (
                        base64.b64encode(image_bytes).decode("utf-8")
                    )

                pages.append(page_data)

    except Exception as e:
        return {
            "error": f"Failed to read PDF: {e}"
        }

    return {
        "page_count": len(pages),
        "extracted_text": "\n\n".join(
            f"-- PAGE {page['page_number']} --\n{page['text']}"
            for page in pages
        ),
        "extracted_image": "\n\n".join(
            f"-- PAGE {page['page_number']} --\n{page['image_base64']}"
            for page in pages
            if "image_base64" in page
        )
    }


return_data = read_invoice_document("./data/Invoice.pdf")

print(return_data["extracted_image"])