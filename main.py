import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles # Import StaticFiles
import google.generativeai as genai
import io
import json
import fitz  # PyMuPDF for PDF handling


app = FastAPI()

# Configure Gemini API
# On Cloud Run, it will automatically pick up credentials from the assigned service account
# if that service account has the 'Vertex AI User' role.
# For local testing, ensure 'gcloud auth application-default login' has been run,
# or set GEMINI_API_KEY environment variable.
genai.configure() # No explicit api_key needed here for Cloud Run with ADC
#
# --- API Endpoints ---

# This endpoint is specific to the API functionality
@app.post("/api/extract-loan-details/")
async def extract_loan_details(image_file: UploadFile = File(...)):
    """
    Receives an image file or PDF of a loan contract, uses Google Gemini to extract details,
    and returns them as JSON.
    """
    if not (image_file.content_type.startswith("image/") or image_file.content_type == "application/pdf"):
        raise HTTPException(
            status_code=400, detail="Invalid file types. Only images or PDFs allowed."
        )

    try:
        file_bytes = await image_file.read()
        
        # Handle PDF files
        if image_file.content_type == "application/pdf":
            try:
                pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
                first_page = pdf_document[0]
                pix = first_page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing PDF: {str(e)}"
                )
        else:
            # Handle image files
            try:
                img = Image.open(io.BytesIO(file_bytes))
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing image: {str(e)}"
                )

        model = genai.GenerativeModel('gemini-pro-vision')
        #exETL

        # --- CRITICAL: The Prompt ---
        # This prompt is designed to instruct Gemini to extract specific data
        # and format it as JSON. Be as specific as possible for best results.
        # Include data types and expected formats.
        prompt = """
        Analyze this image of a loan contract. Extract the following details:
        1.  **Lender Name** (string, e.g., "PAYHIPPO LIMITED")
        2.  **Borrower Name** (string, e.g., "Mudiaga Umukoro")
        3.  **Loan Amount** (numeric float, e.g., 3978455.00)
        4.  **Interest Rate** (numeric float, as percentage, e.g., 5.0 for 5%)
        5.  **Loan Term** (string, e.g., "6 months")
        6.  **Agreement Date** (string, e.g., "24th of April, 2024")

        7.  **Payment Schedule:** This is a table. Extract it as a JSON array of objects.
            Each object should have the following exact keys and attempt to extract numeric values (float) where appropriate. For "Tenor", it should be a string which is the date.
            Required keys: "Tenor", "Principal", "Principal Repayment", "Interest Repayment", "Monthly Repayment".
            Ensure all numeric values are parsed as floats.

        Format your entire response as a single JSON object. If a field is not found or cannot be extracted, omit it or use null.
        Example JSON structure:
        {
          "lender_name": "...",
          "borrower_name": "...",
          "loan_amount": ...,
          "interest_rate": ...,
          "loan_term": "...",
          "agreement_date": "...",
          "payment_schedule": [
            {
              "Tenor": "May 28th, 2024",
              "Principal": 3978455.00,
              "Principal Repayment": 663075.83,
              "Interest Repayment": 218815.03,
              "Monthly Repayment": 881890.86
            },
            {
              "Tenor": "June 27th, 2024",
              "Principal": 3315379.17,
              "Principal Repayment": 663075.83,
              "Interest Repayment": 165768.96,
              "Monthly Repayment": 828844.79
            }
            // ... more payment entries
          ]
        }
        """

        response = model.generate_content([prompt, img])
        
        gemini_output_text = response.text.strip()
        
        # Sanitize Gemini's response: remove markdown code block fences if present
        if gemini_output_text.startswith("```json"):
            gemini_output_text = gemini_output_text[len("```json"):].strip()
        if gemini_output_text.endswith("```"):
            gemini_output_text = gemini_output_text[:-len("```")].strip()

        try:
            extracted_data = json.loads(gemini_output_text)
        except json.JSONDecodeError:
            # If Gemini didn't return valid JSON, this allows inspecting the raw output
            return JSONResponse(status_code=500, content={
                "message": "Gemini's response was not perfect JSON. Check raw_gemini_output.",
                "raw_gemini_output": gemini_output_text
            })

        return JSONResponse(content=extracted_data)

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )

# --- Static Files Serving ---
# This must be mounted AFTER all other specific API routes,
# so the API routes take precedence.
# It serves files from the 'static' directory.
# If a direct file is not found (e.g., /), it serves index.html (html=True).
app.mount("/", StaticFiles(directory="static", html=True), name="static") 