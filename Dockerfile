FROM python:3.11-slim

WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY gmail_client.py .
COPY supabase_client.py .
COPY parse_pdf.py .

# Expose the port for the application
EXPOSE 80

# Run the application with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
