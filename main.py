from fastapi import FastAPI, UploadFile, File, HTTPException
import fitz  # PyMuPDF
import io

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

        first_page = pdf_document[0]
        text = first_page.get_text()

        return {"extracted_text": text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction error: {str(e)}")
