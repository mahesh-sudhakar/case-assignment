## Invoice Extraction Agent

This project takes an inbound **email** JSON file and optionally an **invoice PDF** attachment (both as local files), extracts invoice and purchase data, and generates a **summary** for customer service team.

The final output includes:

- A human-readable customer service summary
- A structured JSON payload for downstream processing

### Setup

1. Install dependencies using `uv`:

    ```uv sync```

2. Make sure your `.env` file contains your OpenAI API key:

    ```OPENAI_API_KEY=your_api_key_here```

### Input

The inputs to this application are
1. An email JSON file.
2. A PDF invoice attachment - Optional

The email JSON file is required and must be supplied as a command-line argument. The PDF invoice is optional; when provided, it is used to enrich the extracted invoice information.

### How to Run

#### Email only

```uv run main.py --email ./data/Email.json```

#### Email + PDF

```uv run main.py --email ./data/Email.json --pdf ./data/Invoice.pdf```

### Outputs

The application creates the following output files in the *outbound* folder:

1. `outbound_email.txt` - Human-readable summary for Customer Service.
2. `outbound_json.json` - Structured JSON payload suitable for downstream processing.

### Expected Workflow:

The Invoice Extraction Agent performs the following steps:

1. Read the inbound email JSON.
2. Determine whether a PDF invoice was provided.
3. If a PDF is available, process the PDF and extract invoice information from its text.
4. Inspect embedded PDF images only when required to recover missing or uncertain invoice fields.
5. Merge information from all available sources into a single structured invoice.
6. Generate the Customer Service notification files.

### Notes:

- Embedded images extracted from the PDF may be temporarily saved in the *temp* directory during processing.

- These images are only inspected when invoice information cannot be reliably extracted from the email or PDF text.

- If a PDF is not provided, the agent extracts all available information from the email only.

- If any of the invoice fields cannot be extracted, the agent returns `null` for those fields instead of hallucinating.