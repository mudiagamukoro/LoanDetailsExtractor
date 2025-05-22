from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import fitz  # PyMuPDF

app = FastAPI()

# Serve static assets like index.html, style.css, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/extract-loan-details/")
async def extract_loan_details(image_file: UploadFile = File(...)):
    if image_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        file_bytes = await image_file.read()
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

        first_page = pdf_document[0]
        text = first_page.get_text()

        return {"extracted_text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction error: {str(e)}")
