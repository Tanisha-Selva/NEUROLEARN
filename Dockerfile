# Dockerfile for NeuroLearnAI (Streamlit + Backend)

FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (needed for PyPDF2 or Tesseract OCR, if you choose to enable it)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Expose port for Streamlit
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]
