import asyncio
import base64
import json
import os
import pymupdf

from agents import Agent, Runner, function_tool
from agents.tool import ToolOutputImage
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv


load_dotenv()


class InvoiceLineItem(BaseModel):
    sku: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None


class Invoice(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: Optional[str] = None
    customer_po_number: Optional[str] = None
    total_due: Optional[float] = None
    subtotal: Optional[float] = None
    taxes: Optional[float] = None
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    site_allocations: Optional[str] = None
    other_info: Optional[str] = None


@function_tool
def read_email_json(email_json_path: str) -> dict:
    try:
        with open(email_json_path, "r") as f:
            email_data = json.load(f)

        print(f"Email json read from {email_json_path}")
        return {
            "email": email_data
        }

    except Exception as e:
        return {
            "error": f"Failed to read email JSON: {e}"
        }

@function_tool
def read_invoice_document(pdf_path: str) -> dict:
    pages = []
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    try:
        with pymupdf.open(pdf_path) as invoice_doc:
            print(f"PDF invoice read from {pdf_path}")
            for page_number, page in enumerate(invoice_doc, start=1):
                text = page.get_text("text") or ""

                page_data = {
                    "page_number": page_number,
                    "text": text,
                    "images": []
                }

                images = page.get_images(full=True)

                for image_index, image in enumerate(images, start=1):
                    xref = image[0]

                    image_info = invoice_doc.extract_image(xref)
                    image_bytes = image_info["image"]
                    image_ext = image_info["ext"]

                    image_filename = (
                        f"page_{page_number}_image_{image_index}.{image_ext}"
                    )
                    image_path = os.path.join(output_dir, image_filename)

                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    print(f"Extracted image saved as {image_path}")

                    page_data["images"].append({
                        "image_path": image_path,
                        "ext": image_ext
                    })

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


@function_tool
def read_invoice_image(image_path: str) -> dict:
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        print(f"Extracted image read from {image_path}\n")

        mime = os.path.splitext(image_path)[1].lower().replace(".", "")
        image_url = (
            f"data:image/{mime};base64,"
            f"{base64.b64encode(image_bytes).decode('utf-8')}"
        )

        return ToolOutputImage(
            image_url=image_url,
            detail="high"
        )

    except Exception as e:
        return {
            "error": f"Failed to read image: {e}"
        }


invoice_agent_instructions = """
You are an expert at extracting invoice and purchase data from inbound emails and PDF invoices.

Workflow:
1. First call read_email_json to inspect the inbound email.
2. Then call read_invoice_document to inspect the PDF invoice.
3. Use email content and PDF text first.
4. Only call read_invoice_image for the specific image_path that may contain missing invoice fields.
5. When read_invoice_image returns an image, visually inspect it directly. Do not ask for Base64 or OCR text.
6. Merge information from the email and PDF into one final Invoice object.

Rules:
1. The final output must follow the Invoice schema.
2. The Invoice values may come from the email, the PDF text, or PDF images.
3. Prefer PDF invoice values over email values when they conflict, unless the email clearly contains purchase metadata not present in the PDF.
4. Never hallucinate.
5. If a value is missing after checking available sources, return null.
6. Extract all invoice line items.
7. Preserve currency and numeric values accurately.
8. Use other_info to briefly mention important source notes or conflicts.
"""


invoice_agent = Agent(
    name="Invoice Extraction Agent",
    model="gpt-5-mini",
    tools=[read_email_json, read_invoice_document, read_invoice_image],
    instructions=invoice_agent_instructions,
    output_type=Invoice
)


async def main():
    email_json_path = "data/Email.json"
    pdf_path = "data/Invoice.pdf"

    prompt = f"""
Extract structured invoice details using both sources:

1. Email JSON:
{email_json_path}

2. PDF invoice:
{pdf_path}

Use the email and PDF text first.
Only inspect PDF images if needed.
Return one final Invoice object.
"""

    print("Processing email and invoice structure...\n")

    result = await Runner.run(
        invoice_agent,
        prompt
    )

    invoice: Invoice = result.final_output

    print(json.dumps(invoice.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())