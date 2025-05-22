from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import fitz  # PyMuPDF
import io
import json

app = FastAPI()

# Mount static files FIRST
app.mount("/static", StaticFiles(directory="static"), name="static")

# Then define API routes
@app.get("/")
async def root():
    """
    Root endpoint that serves the main page.
    """
    return {"message": "Loan Details Extractor API is running"}

@app.post("/api/extract-loan-details/")
async def extract_loan_details(image_file: UploadFile = File(...)):
    """
    Receives a PDF of a loan contract and returns extracted data as JSON.
    """
    if image_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")

    try:
        file_bytes = await image_file.read()
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

        # Extract text from all pages
        full_text = ""
        for page in pdf_document:
            full_text += page.get_text()

        # For now, just return the extracted text
        # Later we can add text processing to extract specific fields
        return JSONResponse(content={"extracted_text": full_text})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
