import pymupdf
import base64
import os

def read_invoice_document(pdf_path: str, output_dir: str) -> dict:
    pages = []

    try:
        with pymupdf.open(pdf_path) as invoice_doc:
            for page_number, page in enumerate(invoice_doc, start=1):
                text = page.get_text("text") or ""

                page_data = {
                    "page_number": page_number,
                    "text": text,
                    "images": []
                }

                images = page.get_images(full=True)
                if not images:
                    print(f"Page {page_number} has no embedded images.")
                    continue

                print(f"Found {len(images)} image(s) in page {page_number}")
                for image_idx, image in enumerate(images, start=1):
                    xref = image[0]

                    image_info = invoice_doc.extract_image(xref)
                    image_bytes = image_info["image"]
                    image_ext = image_info["ext"]

                    image_filename = (
                        f"page_{page_number}_image_{image_idx}.{image_ext}"
                    )
                    image_path = os.path.join(output_dir, image_filename)

                    # Save locally for debugging
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    print(f"Image saved at {image_path}")

                    # Also provide base64 to the agent
                    page_data["images"].append(
                        {
                            "image_path": image_path,
                            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
                            "ext": image_ext
                        }
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

        "extracted_images": [
            {
                "page_number": page["page_number"],
                "images": page["images"]
            }
            for page in pages
            if page["images"]
        ]
    }


output_dir = "temp"
os.makedirs(output_dir, exist_ok=True)

return_data = read_invoice_document("./data/Invoice.pdf", output_dir)

print(return_data["extracted_images"])