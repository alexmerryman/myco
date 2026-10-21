# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py config.py inat_api.py inat_auth.py ./
COPY viewer/ viewer/
COPY uploader/ uploader/
COPY templates/ templates/

# Create templates directory if it doesn't exist
RUN mkdir -p templates

# Expose port
EXPOSE 8080

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]