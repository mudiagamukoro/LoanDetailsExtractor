from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import io
import json

app = FastAPI()

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
