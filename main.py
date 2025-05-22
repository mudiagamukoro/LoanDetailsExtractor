import os
import fitz  # PyMuPDF
import json
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Configure Gemini with your API key from env var
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

app = FastAPI()

# Serve static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.post("/api/extract-loan-details/")
async def extract_loan_details(image_file: UploadFile = File(...)):
    if image_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    try:
        # Extract text from all PDF pages
        file_bytes = await image_file.read()
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = "\n".join(page.get_text() for page in pdf_doc)

        # Prepare Gemini prompt
        model = genai.GenerativeModel("gemini-pro")
        prompt_text = """
        Analyze this document/text of a loan contract. If it's a multi-page document or long text, look for all relevant information across all pages/sections. If a piece of information, like payment schedule rows, is found across multiple pages/sections, combine them. If the loan terms or parties are identical across pages/sections, provide them only once.

        Extract the following details:
        1.  **Lender Name** (string, e.g., "PAYHIPPO LIMITED")
        2.  **Borrower Name** (string, e.g., "Mudiaga Umukoro")
        3.  **Loan Amount** (numeric float, e.g., 3978455.00)
        4.  **Interest Rate** (numeric float, as percentage, e.g., 5.0 for 5%)
        5.  **Loan Term** (string, e.g., "6 months")
        6.  **Agreement Date** (string, e.g., "24th of April, 2024")

        7.  **Payment Schedule:** This is a table. Extract all entries into a JSON array of objects.
            Each object should have these keys: "Tenor", "Principal", "Principal Repayment", "Interest Repayment", "Monthly Repayment".
            Parse all numeric values as floats. Use null if a value is missing.

        Format the response as a single JSON object. Example:
        {
          "lender_name": "...",
          "borrower_name": "...",
          "loan_amount": ...,
          "interest_rate": ...,
          "loan_term": "...",
          "agreement_date": "...",
          "payment_schedule": [ { ... }, { ... } ]
        }
        """

        response = model.generate_content([prompt_text, full_text])
        gemini_output = response.text.strip()

        # Clean JSON formatting
        if gemini_output.startswith("```json"):
            gemini_output = gemini_output[len("```json"):].strip()
        if gemini_output.endswith("```"):
            gemini_output = gemini_output[:-len("```")].strip()

        # Try parsing JSON
        try:
            extracted_data = json.loads(gemini_output)
            return JSONResponse(content=extracted_data)
        except json.JSONDecodeError:
            return JSONResponse(status_code=500, content={
                "message": "Gemini's response was not valid JSON",
                "raw_gemini_output": gemini_output
            })

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {str(e)}"})
