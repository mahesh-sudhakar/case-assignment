import argparse
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

EXTRACTED_IMAGE_DIR = "./temp"
OUTBOUND_DIR = "./outbound"

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


class CustomerServiceNotificationInput(BaseModel):
    invoice: Invoice


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

    os.makedirs(EXTRACTED_IMAGE_DIR, exist_ok=True)

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
                    image_path = os.path.join(EXTRACTED_IMAGE_DIR, image_filename)

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

        print(f"Extracted image read from {image_path}")

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


@function_tool
def send_customer_service_notification(data: CustomerServiceNotificationInput) -> dict:
    invoice_dict = data.invoice.model_dump()

    try:
        os.makedirs(OUTBOUND_DIR, exist_ok=True)

        outbound_summary_path = os.path.join(OUTBOUND_DIR, "outbound_summary.txt")
        outbound_json_path = os.path.join(OUTBOUND_DIR, "outbound_json.json")

        summary = f"""
Invoice Processing Request

    Vendor: {invoice_dict.get("vendor_name")}
    Invoice Number: {invoice_dict.get("invoice_number")}
    Invoice Date: {invoice_dict.get("invoice_date")}
    Due Date: {invoice_dict.get("due_date")}
    Payment Terms: {invoice_dict.get("payment_terms")}
    Currency: {invoice_dict.get("currency")}
    Customer PO Number: {invoice_dict.get("customer_po_number")}

    Amounts:
    - Subtotal: {invoice_dict.get("subtotal")}
    - Taxes: {invoice_dict.get("taxes")}
    - Total Due: {invoice_dict.get("total_due")}

    Line Items:
"""

        for item in invoice_dict.get("line_items", []):
            summary += (
                f"\t- SKU: {item.get('sku')}, "
                f"Description: {item.get('description')}, "
                f"Qty: {item.get('quantity')}, "
                f"Unit Price: {item.get('unit_price')}, "
                f"Line Total: {item.get('line_total')}\n"
            )

        summary += f"""
    Site Allocations Info:
    {invoice_dict.get("site_allocations")}

    Other Info:
    {invoice_dict.get("other_info")}
"""

        with open(outbound_summary_path, "w", encoding="utf-8") as f:
            f.write(summary.strip())

        with open(outbound_json_path, "w") as f:
            json.dump(invoice_dict, f, indent=4)

        print(f"Outbound summary file and JSON dump for customer service created!\n")

        return {
            "status": "notification_created",
            "message": "Outbound summary file and JSON dump for customer service created successfully.",
            "outbound_email_file": outbound_summary_path,
            "structured_payload_file": outbound_json_path
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": f"Failed to create Customer Service notification: {e}"
        }


invoice_agent_instructions = """
You are an expert at extracting invoice and purchase data from inbound emails and PDF invoices.

Workflow:
1. First call read_email_json to inspect the inbound email.
2. Determine whether a PDF invoice path was provided.
3. If a PDF path is available, call read_invoice_document and extract data from both the email and PDF.
4. If no PDF path is available, skip PDF processing and extract data from the email only.
5. Use text sources first: email content and, when available, PDF text.
6. Only call read_invoice_image for a specific image_path when a required invoice field is missing, or likely located inside an image.
7. When read_invoice_image returns an image, visually inspect it directly. Do not request Base64 or OCR text.
8. Merge all available information into one final Invoice object.
9. After extracting the invoice data, call send_customer_service_notification with the final Invoice object.

Rules:
1. The final output must follow the Invoice schema.
2. Invoice values may come from any available source: email content, PDF text, or PDF images.
3. If PDF data is available, prefer PDF invoice values over email values when they conflict, unless the email clearly contains purchase metadata not present in the PDF.
4. If no PDF is available, extract all possible invoice data from the email only.
5. Never hallucinate.
6. If a value is missing after checking all available sources, return null.
7. Extract all invoice line items available from the provided sources.
8. Preserve currency and numeric values accurately.
9. Use other_info to briefly mention important source notes, missing attachments, or conflicts.
10. Use the final Invoice object values as the notification payload.
11. The notification must include a human-readable summary for Customer Service and a structured JSON payload for downstream processing.
"""


invoice_agent = Agent(
    name="Invoice Extraction Agent",
    model="gpt-5-mini",
    tools=[read_email_json, read_invoice_document, read_invoice_image, send_customer_service_notification],
    instructions=invoice_agent_instructions,
    output_type=Invoice
)


async def main(email_json_path: str, pdf_path:  Optional[str] = None):

    pdf_section = (
        f"2. PDF invoice:\n{pdf_path}"
        if pdf_path
        else "2. PDF invoice:\nNo PDF attachment was provided. Use email JSON only."
    )

    prompt = f"""
        Extract structured invoice details using following 2 sources:

        1. Email JSON:
        {email_json_path}

        {pdf_section}

        Important:
        - Always read the email JSON first.
        - Only call read_invoice_document if a valid PDF path is provided.
        - If no PDF path is provided, extract all possible invoice data from the email only.
        - After extraction, create the outbound Customer Service summary.
        - Return one final Invoice object.
    """

    print("Processing email and invoice structure...\n")

    result = await Runner.run(
        invoice_agent,
        prompt
    )

    invoice: Invoice = result.final_output

    print(json.dumps(invoice.model_dump(), indent=2))


if __name__ == "__main__":

    parser = argparse.ArgumentParser("Extract invoice info from an email JSON and attachment PDF")

    parser.add_argument(
        "--email",
        required=True,
        help="Path to the email JSON file"
    )

    parser.add_argument(
        "--pdf",
        required=False,
        default=None,
        help="Optional path to the invoice PDF file"
    )

    args = parser.parse_args()

    asyncio.run(main(args.email, args.pdf))