import asyncio
import base64
import pymupdf
import json

from agents import Agent, Runner, function_tool
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv


load_dotenv()

class InvoiceLineItem(BaseModel):
    sku: str = None
    description: str = None
    quantity: float = None
    unit_price: float = None
    line_total: float = None


class Invoice(BaseModel):
    vendor_name: str = None
    invoice_number: str = None
    invoice_date: str = None
    due_date: str = None
    payment_terms: str = None
    currency: str = None
    customer_po_number: str = None
    total_due: float = None
    subtotal: float = None
    taxes: float = None
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    site_allocations: Optional[str] = None
    other_info: Optional[str] = None


@function_tool
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

invoice_agent_instructions = """
You are an expert in extracting information from invoices.
Always folow the workflow and rules provided below.

Workflow:
1. Use all tools that you may have access to.
2. Read the `extracted_text` from the document first.
3. If there is an image available for any page then inspect the `extracted_image` to extract information from it.
4. Return structured information following the schema provided.

Rules:
1. Never hallucinate.
2. If values are missing even after using all the tools and following the workflow, then populate null instead.
3. Preserve the currency values accurately.
4. Extract all invoice line items.
5. Use the page images whenever tables, logos, signatures, images or scanned content are difficult to interpret from text alone.

"""

invoice_agent = Agent(
    name="Invoice Extraction Agent",
    model="gpt-5-mini",
    tools=[read_invoice_document],
    instructions=invoice_agent_instructions,
    output_type=Invoice
)


async def main():
    pdf_path = "data/Invoice.pdf"
    prompt = f"Please process and extract structured invoice details from {pdf_path}."

    print("Processing invoice structure...")
    result = await Runner.run(
        invoice_agent,
        prompt
    )

    invoice: Invoice = result.final_output

    print(json.dumps(invoice.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())