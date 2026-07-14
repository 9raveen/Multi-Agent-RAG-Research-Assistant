FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# HF Spaces expects the app to listen on port 7860
EXPOSE 7860

# Add health check to help HF Spaces detect when app is ready
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health', timeout=3)" || exit 1

# Use uvicorn with optimized settings for HF Spaces
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--timeout-keep-alive", "5"]