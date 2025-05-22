import os
import fitz  # PyMuPDF
import json
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Configure Gemini API
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
        # Extract text from all pages
        file_bytes = await image_file.read()
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = "\n".join(page.get_text() for page in pdf_doc)

        # Gemini prompt with 'Due Date' and formatting guidance
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
            Each object should have the following exact keys:
              - "Due Date"
              - "Principal"
              - "Principal Repayment"
              - "Interest Repayment"
              - "Monthly Repayment"

            Format all numeric values with commas and two decimal places (e.g., 1,500,000.00).

        Format your entire response as a single JSON object. If a field is missing, use null.
        """
