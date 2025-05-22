import os
import fitz
import json
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

app = FastAPI()

# Serve static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

# Helper function to format numbers
def format_with_commas(value):
    try:
        return f"{float(value):,.2f}"
    except:
        return value



@app.post("/api/extract-loan-details/")
async def extract_loan_details(image_file: UploadFile = File(...)):
    if image_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")




    try:
        file_bytes = await image_file.read()
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = "\n".join(page.get_text() for page in pdf_doc)


        prompt_text = """
        Analyze this document/text of a loan contract. Extract all loan details into a structured JSON format including a payment schedule.
        """
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content([prompt_text, full_text])
        gemini_output = response.text.strip()

        if gemini_output.startswith("```json"):
            gemini_output = gemini_output[len("```json"):].strip()
        if gemini_output.endswith("```"):
            gemini_output = gemini_output[:-len("```")].strip()

        try:
            extracted_data = json.loads(gemini_output)

            # Process payment_schedule: rename 'Tenor' to 'Due Date' and format numbers
            if "payment_schedule" in extracted_data:
                for entry in extracted_data["payment_schedule"]:
                    # Rename key
                    if "Tenor" in entry:
                        entry["Due Date"] = entry.pop("Tenor")

                    # Format numeric fields
                    for field in ["Principal", "Principal Repayment", "Interest Repayment", "Monthly Repayment"]:
                        if field in entry:
                            entry[field] = format_with_commas(entry[field])




            return JSONResponse(content=extracted_data)

        except json.JSONDecodeError:
            return JSONResponse(status_code=500, content={
                "message": "Gemini's response was not valid JSON",
                "raw_gemini_output": gemini_output
            })

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {str(e)}"})
