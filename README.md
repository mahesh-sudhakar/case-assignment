## Invoice Extraction Agent

This project takes an inbound **email** JSON file and an **invoice PDF** attachment (both as local files), extracts invoice/purchase data, and generates a **summary** for customer service team.

The final output includes:

- A human-readable customer service summary
- A JSON payload for downstream processing

### Setup

1. Install dependencies using `uv`:

    ```uv sync```

2. Make sure your `.env` file contains your OpenAI API key:

    ```OPENAI_API_KEY=your_api_key_here```

### Input

The inputs to this application are
1. An email JSON file.
2. A PDF invoice attachment

Both of the inputs must exist locally and should be provided as command line arguments.

### How to Run

```uv run main.py --email ./data/Email.json --pdf ./data/Invoice.pdf```

### Outputs

The application creates the following output files within an *outbound* folder:

1. `outbound_email.txt` - Human-readable summary for Customer Service
2. `outbound_json.json` - Structured JSON payload suitable for downstream processing.

### Expected Workflow:

Invoice Extraction Agent should,

1. Read inbound email JSON.
2. Process the invoice PDF attachment.
3. Extract invoice data from email text and PDF text.
4. Inspect PDF images only when needed.
5. Produce final structured invoice output.
6. Write Customer Service summary files.

### Notes:

- During processing, embedded PDF images may be saved locally for inspection within a *temp* folder.

- These files are used only when the agent needs to inspect invoice data located inside an image.

- If any of the invoice fields cannot be extracted, the agent returns null for those fields instead of hallucinating.