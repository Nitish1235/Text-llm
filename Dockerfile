FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy handler code
COPY handler.py .

# Set environment variables (can be overridden at runtime)
ENV MODEL_NAME=meta-llama/Meta-Llama-3-8B
ENV MODEL_REVISION=v1
ENV MODEL_BASE_URL=https://api.openai.com/v1

# Expose port (Runpod will handle this)
EXPOSE 8000

# Runpod expects the handler to be importable
# The handler function will be called by Runpod's serverless runtime
CMD ["python", "-c", "import handler; print('Handler loaded successfully')"]
