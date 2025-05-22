FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y libmupdf-dev

# Set work directory
WORKDIR /app



# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Expose static files
COPY ./static ./static

# Start app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
