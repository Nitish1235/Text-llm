# Deployment Guide: Text/LLM Generation Service

Production deployment guide for Runpod and Modal serverless platforms using Google Cloud Storage/Artifact Registry.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables Setup](#environment-variables-setup)
3. [Google Cloud Setup](#google-cloud-setup)
4. [Deploy to Runpod](#deploy-to-runpod)
5. [Deploy to Modal](#deploy-to-modal)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts & Tools

- **Google Cloud Platform (GCP)**
  - Active GCP project
  - `gcloud` CLI installed and authenticated
  - Docker installed locally

- **Runpod**
  - Account at [runpod.io](https://www.runpod.io)
  - API key from Runpod dashboard

- **Modal**
  - Account at [modal.com](https://modal.com)
  - Modal CLI installed: `pip install modal`

- **Hugging Face**
  - Account at [huggingface.co](https://huggingface.co)
  - Access token with read permissions
  - Access to `meta-llama/Meta-Llama-3-8B` model (request access if needed)

### Required Secrets

Before deployment, prepare these values:

| Variable | Description | Example |
|----------|-------------|---------|
| `MODEL_API_KEY` | Hugging Face access token | `hf_...` |
| `MODEL_BASE_URL` | OpenAI-compatible API endpoint (see Hugging Face setup below) | `https://api.together.xyz/v1` or Inference Endpoint URL |
| `MODEL_NAME` | Hugging Face model identifier | `meta-llama/Meta-Llama-3-8B` |
| `MODEL_REVISION` | Model version tag | `v1` or commit hash |
| `API_KEY` | Your service authentication key (generate a random string) | `your-random-secret-key-here` |

**Generate API_KEY:**
```bash
# Generate a secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Environment Variables Setup

### Hugging Face Setup

#### Option 1: Using Hugging Face Inference Endpoints (Recommended)

1. **Create Inference Endpoint**:
   - Go to [Hugging Face Inference Endpoints](https://huggingface.co/inference-endpoints)
   - Create new endpoint
   - Select model: `meta-llama/Meta-Llama-3-8B`
   - Choose instance type (GPU recommended)
   - Enable **OpenAI-compatible API** option
   - Deploy endpoint

2. **Get Endpoint URL**:
   - Copy the endpoint URL (e.g., `https://xxx.us-east-1.aws.endpoints.huggingface.cloud`)
   - This becomes your `MODEL_BASE_URL`

3. **Get API Key**:
   - Use your Hugging Face access token as `MODEL_API_KEY`
   - Create token at: [Hugging Face Settings → Access Tokens](https://huggingface.co/settings/tokens)

#### Option 2: Using Third-Party OpenAI-Compatible Services

Services like **Together AI**, **Anyscale**, or **Replicate** provide OpenAI-compatible APIs for Hugging Face models:

**Together AI Example:**
```bash
MODEL_BASE_URL=https://api.together.xyz/v1
MODEL_NAME=meta-llama/Llama-3-8b-chat-hf
MODEL_API_KEY=your-together-ai-api-key
```

**Anyscale Example:**
```bash
MODEL_BASE_URL=https://api.endpoints.anyscale.com/v1
MODEL_NAME=meta-llama/Meta-Llama-3-8B-Instruct
MODEL_API_KEY=your-anyscale-api-key
```

#### Option 3: Self-Hosted TGI (Text Generation Inference)

If you're running TGI yourself:
```bash
MODEL_BASE_URL=https://your-tgi-endpoint.com/v1
MODEL_NAME=meta-llama/Meta-Llama-3-8B
MODEL_API_KEY=your-api-key
```

### Required Environment Variables

Both Runpod and Modal need these environment variables:

**For Hugging Face Inference Endpoints:**
```bash
MODEL_API_KEY=hf_your_huggingface_token
MODEL_BASE_URL=https://xxx.us-east-1.aws.endpoints.huggingface.cloud
MODEL_NAME=meta-llama/Meta-Llama-3-8B
MODEL_REVISION=v1
API_KEY=your-service-api-key
```

**For Together AI (example):**
```bash
MODEL_API_KEY=your-together-ai-api-key
MODEL_BASE_URL=https://api.together.xyz/v1
MODEL_NAME=meta-llama/Llama-3-8b-chat-hf
MODEL_REVISION=v1
API_KEY=your-service-api-key
```

**Note:** Replace with your actual Hugging Face model identifier and endpoint URL.

---

## Google Cloud Setup

### Step 1: Authenticate with GCP

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Verify project
gcloud config get-value project
```

### Step 2: Enable Required APIs

```bash
# Enable Artifact Registry API
gcloud services enable artifactregistry.googleapis.com

# Enable Container Registry API (if using GCR instead)
gcloud services enable containerregistry.googleapis.com
```

### Step 3: Create Artifact Registry Repository

```bash
# Create Docker repository in Artifact Registry
gcloud artifacts repositories create llm-text-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="LLM text generation service Docker images"

# Alternative: Use a different region
# gcloud artifacts repositories create llm-text-repo \
#   --repository-format=docker \
#   --location=us-east1
```

### Step 4: Configure Docker Authentication

```bash
# Configure Docker to use gcloud as credential helper
gcloud auth configure-docker us-central1-docker.pkg.dev

# If using different region, adjust accordingly:
# gcloud auth configure-docker us-east1-docker.pkg.dev
```

---

## Deploy to Runpod

### Step 1: Build Docker Image

From your project root directory (where `Dockerfile` and `handler.py` are located):

```bash
# Build the Docker image
docker build -t llm-text:latest .

# Verify image was created
docker images | grep llm-text
```

### Step 2: Tag Image for Artifact Registry

```bash
# Set variables
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
REPO_NAME=llm-text-repo
IMAGE_NAME=llm-text
IMAGE_TAG=latest

# Full image path
FULL_IMAGE_PATH=us-central1-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$IMAGE_TAG

# Tag the image
docker tag llm-text:latest $FULL_IMAGE_PATH

# Verify tag
docker images | grep llm-text
```

### Step 3: Push Image to Artifact Registry

```bash
# Push image to Artifact Registry
docker push $FULL_IMAGE_PATH

# Verify push succeeded
gcloud artifacts docker images list us-central1-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME
```

**Expected output:** You should see your image listed with the tag `latest`.

### Step 4: Create Runpod Serverless Endpoint

1. **Login to Runpod Dashboard**
   - Go to [runpod.io](https://www.runpod.io)
   - Navigate to **Serverless** → **Endpoints**

2. **Create New Endpoint**
   - Click **"Create Endpoint"** or **"New Endpoint"**
   - Select **"Custom Container"** or **"Docker"** option

3. **Configure Container**
   - **Container Image**: Paste your Artifact Registry image URL:
     ```
     us-central1-docker.pkg.dev/YOUR_PROJECT_ID/llm-text-repo/llm-text:latest
     ```
   - **Handler**: `handler.handler`
   - **Runtime**: Python 3.10 (or Custom)

4. **Set Environment Variables**
   In the endpoint configuration, add these environment variables:
   ```
   MODEL_API_KEY=hf_your_huggingface_token
   MODEL_BASE_URL=https://xxx.us-east-1.aws.endpoints.huggingface.cloud
   MODEL_NAME=meta-llama/Meta-Llama-3-8B
   MODEL_REVISION=v1
   API_KEY=your-service-api-key
   ```
   **Note:** Replace with your actual Hugging Face endpoint URL and model identifier.

5. **Configure Resources**
   - **CPU**: 1-2 vCPU (recommended: 2)
   - **Memory**: 2-4 GB (recommended: 4 GB)
   - **Timeout**: 60 seconds (minimum)
   - **GPU**: Not required for this service

6. **Deploy**
   - Click **"Deploy"** or **"Save"**
   - Wait for deployment to complete
   - Copy the **Endpoint ID** from the dashboard

### Step 5: Get Runpod API Key

1. Go to **Settings** → **API Keys** in Runpod dashboard
2. Generate a new API key or copy existing one
3. Save it securely (you'll need it for API calls)

---

## Deploy to Modal

### Step 1: Install Modal CLI

```bash
# Install Modal
pip install "modal>=0.62"

# Verify installation
modal --version
```

### Step 2: Authenticate with Modal

```bash
# Login to Modal (opens browser)
modal token new

# Verify authentication
modal app list
```

### Step 3: Create Modal Secret

**Option A: Using Modal Dashboard**

1. Go to [modal.com](https://modal.com) → **Secrets**
2. Click **"Create Secret"**
3. Name: `text-llm-secrets`
4. Add these key-value pairs:
   ```
   MODEL_API_KEY=hf_your_huggingface_token
   MODEL_BASE_URL=https://xxx.us-east-1.aws.endpoints.huggingface.cloud
   MODEL_NAME=meta-llama/Meta-Llama-3-8B
   MODEL_REVISION=v1
   API_KEY=your-service-api-key
   ```
   **Note:** Replace with your actual Hugging Face endpoint URL and model identifier.
5. Click **"Create"**

**Option B: Using Modal CLI**

```bash
modal secret create text-llm-secrets \
  MODEL_API_KEY=hf_your_huggingface_token \
  MODEL_BASE_URL=https://xxx.us-east-1.aws.endpoints.huggingface.cloud \
  MODEL_NAME=meta-llama/Meta-Llama-3-8B \
  MODEL_REVISION=v1 \
  API_KEY=your-service-api-key
```
**Note:** Replace with your actual Hugging Face endpoint URL and model identifier.

### Step 4: Deploy Modal App

From your project root directory:

```bash
# Deploy the app
modal deploy modal_app.py

# Expected output:
# ✓ Created objects.
# → https://YOUR_USERNAME--text-llm-generation-generate.modal.run
```

**Save the URL** - this is your Modal endpoint.

### Step 5: Verify Deployment

```bash
# List your apps
modal app list

# View app details
modal app show text-llm-generation
```

---

## Testing

### Test Runpod Endpoint

```bash
# Set variables
RUNPOD_ENDPOINT_ID="your-endpoint-id"
RUNPOD_API_KEY="your-runpod-api-key"
SERVICE_API_KEY="your-service-api-key"

# Test request
curl -X POST "https://api.runpod.io/v2/$RUNPOD_ENDPOINT_ID/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $SERVICE_API_KEY" \
  -d '{
    "input": {
      "topic": "Latest AI trends",
      "length": "20s",
      "tone": "dramatic",
      "hook_style": "shock",
      "generate_voice_script": true,
      "voice_script_style": "narration",
      "max_tokens": 100
    }
  }'
```

**Expected Response:**
```json
{
  "output": {
    "script": "...",
    "hook": "...",
    "word_count": 45,
    "estimated_duration": "20s",
    "tokens_used": 95,
    "voice_script": "...",
    "voice_word_count": 120
  }
}
```

### Test Modal Endpoint

```bash
# Set variables
MODAL_URL="https://YOUR_USERNAME--text-llm-generation-generate.modal.run"
SERVICE_API_KEY="your-service-api-key"

# Test request
curl -X POST "$MODAL_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $SERVICE_API_KEY" \
  -d '{
    "input": {
      "topic": "Latest AI trends",
      "length": "20s",
      "tone": "dramatic",
      "hook_style": "shock",
      "generate_voice_script": true,
      "voice_script_style": "narration",
      "max_tokens": 100
    }
  }'
```

**Expected Response:**
```json
{
  "script": "...",
  "hook": "...",
  "word_count": 45,
  "estimated_duration": "20s",
  "tokens_used": 95,
  "voice_script": "...",
  "voice_word_count": 120
}
```

### Test with Python

```python
import requests
import json

# Runpod
runpod_url = f"https://api.runpod.io/v2/{ENDPOINT_ID}/run"
headers = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json",
    "x-api-key": SERVICE_API_KEY
}
payload = {
    "input": {
        "topic": "Latest AI trends",
        "length": "20s",
        "tone": "dramatic",
        "hook_style": "shock",
        "generate_voice_script": True,
        "voice_script_style": "narration",
        "max_tokens": 100
    }
}
response = requests.post(runpod_url, headers=headers, json=payload)
print(json.dumps(response.json(), indent=2))

# Modal
modal_url = "https://YOUR_USERNAME--text-llm-generation-generate.modal.run"
headers = {
    "Content-Type": "application/json",
    "x-api-key": SERVICE_API_KEY
}
response = requests.post(modal_url, headers=headers, json=payload)
print(json.dumps(response.json(), indent=2))
```

---

## Troubleshooting

### Common Issues

#### 1. Docker Push Fails: Authentication Error

**Error:** `denied: Permission denied`

**Solution:**
```bash
# Re-authenticate Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# Verify authentication
gcloud auth list
```

#### 2. Runpod: Handler Not Found

**Error:** `ModuleNotFoundError: No module named 'handler'`

**Solution:**
- Verify `handler.py` is in the Docker image root directory
- Check Dockerfile `COPY handler.py .` is correct
- Rebuild and push image

#### 3. Modal: Secret Not Found

**Error:** `Secret 'text-llm-secrets' not found`

**Solution:**
```bash
# List secrets
modal secret list

# Create secret if missing
modal secret create text-llm-secrets MODEL_API_KEY=... MODEL_BASE_URL=...
```

#### 4. API Key Validation Fails

**Error:** `{"error": "Invalid API key", "code": "AUTH_ERROR"}`

**Solution:**
- Verify `API_KEY` environment variable matches the `x-api-key` header value
- Check for extra spaces or newlines in the API key
- Ensure header name is exactly `x-api-key` (case-insensitive)

#### 5. Model API Errors

**Error:** `{"error": "Model error: ...", "code": "MODEL_ERROR"}`

**Solution:**
- Verify `MODEL_API_KEY` is correct (Hugging Face token starts with `hf_`)
- Check `MODEL_BASE_URL` is accessible and correct
- Ensure model name is correct (e.g., `meta-llama/Meta-Llama-3-8B`)
- Verify you have access to the model on Hugging Face
- Check Hugging Face rate limits and quota
- For Inference Endpoints: Ensure endpoint is running and not paused
- Test endpoint directly with curl:
  ```bash
  curl https://your-endpoint-url/v1/models \
    -H "Authorization: Bearer hf_your_token"
  ```

#### 6. Token Limit Exceeded

**Error:** `Generated X tokens, exceeds limit of Y`

**Solution:**
- Ensure `max_tokens` matches the length requirement:
  - 20s = 100 tokens
  - 30s = 150 tokens
  - 45s = 225 tokens
  - 60s = 300 tokens
- Check input validation is working correctly

#### 7. Timeout Errors

**Error:** Request times out

**Solution:**
- Increase timeout in Runpod/Modal configuration
- Check model API response time
- Verify network connectivity
- Consider increasing CPU/memory allocation

### Debugging Commands

```bash
# Check Docker image contents
docker run --rm -it llm-text:latest ls -la /app

# Test handler locally
docker run --rm -e MODEL_API_KEY=... -e API_KEY=... llm-text:latest python -c "import handler; print('OK')"

# View Runpod logs
# Go to Runpod dashboard → Endpoints → Your Endpoint → Logs

# View Modal logs
modal app logs text-llm-generation

# Test Modal function locally
modal run modal_app.py::generate
```

---

## Updating Deployment

### Update Runpod

1. **Rebuild and push new image:**
   ```bash
   docker build -t llm-text:latest .
   docker tag llm-text:latest $FULL_IMAGE_PATH
   docker push $FULL_IMAGE_PATH
   ```

2. **Redeploy in Runpod dashboard** (or use API to update endpoint)

### Update Modal

```bash
# Redeploy with latest code
modal deploy modal_app.py

# Or update specific function
modal deploy modal_app.py::generate
```

---

## Cost Optimization

### Runpod
- Use **spot instances** for cost savings
- Set appropriate **idle timeout** to reduce cold starts
- Monitor usage and adjust resources

### Modal
- Modal charges per execution time
- Use **container_idle_timeout** to balance cost vs latency
- Monitor usage in Modal dashboard

### GCP Artifact Registry
- Clean up old image tags periodically
- Use lifecycle policies to auto-delete old images
- Consider using Cloud Storage for logs if needed

---

## Security Best Practices

1. **Never commit secrets** to version control
2. **Rotate API keys** regularly
3. **Use least privilege** for GCP service accounts
4. **Enable audit logging** in GCP
5. **Monitor API usage** for anomalies
6. **Use HTTPS** for all API calls
7. **Validate inputs** (already implemented in code)

---

## Support & Resources

- **Runpod Docs**: https://docs.runpod.io
- **Modal Docs**: https://modal.com/docs
- **GCP Artifact Registry**: https://cloud.google.com/artifact-registry/docs
- **Hugging Face Inference Endpoints**: https://huggingface.co/docs/inference-endpoints
- **Hugging Face Model**: https://huggingface.co/meta-llama/Meta-Llama-3-8B
- **Together AI (Alternative)**: https://www.together.ai
- **Anyscale (Alternative)**: https://www.anyscale.com

---

## Quick Reference

### Image URLs
```bash
# Format
us-central1-docker.pkg.dev/PROJECT_ID/REPO_NAME/IMAGE_NAME:TAG

# Example
us-central1-docker.pkg.dev/my-project/llm-text-repo/llm-text:latest
```

### Environment Variables Checklist
- [ ] `MODEL_API_KEY` - Hugging Face access token (hf_...)
- [ ] `MODEL_BASE_URL` - Hugging Face Inference Endpoint URL or OpenAI-compatible API URL
- [ ] `MODEL_NAME` - Hugging Face model identifier (e.g., meta-llama/Meta-Llama-3-8B)
- [ ] `MODEL_REVISION` - Model version or commit hash
- [ ] `API_KEY` - Service authentication key

### Endpoint URLs
- **Runpod**: `https://api.runpod.io/v2/{ENDPOINT_ID}/run`
- **Modal**: `https://{USERNAME}--{APP_NAME}-{FUNCTION_NAME}.modal.run`

---

**Last Updated:** 2024
**Version:** 1.0
