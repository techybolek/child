# Google Cloud Platform Deployment Guide

Texas Childcare Chatbot - Production Deployment on GCP Cloud Run

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Management](#management)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

## Overview

This guide covers deploying the Texas Childcare Chatbot to Google Cloud Platform using:
- **Cloud Run**: Serverless container hosting with auto-scaling
- **Artifact Registry**: Docker image storage
- **Secret Manager**: Secure API key storage

### Why Cloud Run?

✅ **Serverless** - No infrastructure management
✅ **Auto-scaling** - Scales to zero when idle, up to 10 instances under load
✅ **Cost-effective** - Pay only for actual usage (~$5-10/month for low traffic)
✅ **HTTPS included** - Automatic SSL certificates
✅ **Easy deployment** - One command to build, push, and deploy

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                     │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           Artifact Registry (cohort-1)                │  │
│  │  ┌──────────────────┐  ┌───────────────────┐         │  │
│  │  │  backend:latest  │  │  frontend:latest  │         │  │
│  │  └──────────────────┘  └───────────────────┘         │  │
│  └──────────────┬────────────────────┬───────────────────┘  │
│                 │                    │                       │
│  ┌──────────────▼────────┐  ┌────────▼───────────────────┐  │
│  │   Cloud Run Backend   │  │   Cloud Run Frontend       │  │
│  │   (FastAPI + RAG)     │  │   (Next.js 15)             │  │
│  │   Port: 8000          │  │   Port: 3000               │  │
│  │   HTTPS Auto-enabled  │  │   HTTPS Auto-enabled       │  │
│  └───────────┬───────────┘  └────────────────────────────┘  │
│              │                                                │
│  ┌───────────▼───────────┐                                   │
│  │   Secret Manager      │                                   │
│  │  • qdrant-api-key     │                                   │
│  │  • openai-api-key     │                                   │
│  │  • groq-api-key       │                                   │
│  └───────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐     ┌──────▼──────┐    ┌─────▼────┐
   │  Qdrant  │     │   OpenAI    │    │   GROQ   │
   │ (Vector  │     │ (Embeddings)│    │  (LLM)   │
   │   DB)    │     │             │    │          │
   └──────────┘     └─────────────┘    └──────────┘
      External          External          External
```

## Prerequisites

### Required Tools

1. **Google Cloud SDK (gcloud)**
   ```bash
   # Install gcloud CLI
   # Visit: https://cloud.google.com/sdk/docs/install

   # Verify installation
   gcloud --version
   ```

2. **Docker**
   ```bash
   # Install Docker
   # Visit: https://docs.docker.com/get-docker/

   # Verify installation
   docker --version
   ```

### Required Accounts & API Keys

1. **Google Cloud Account**
   - GCP project: `docker-app-20250605` (pre-configured)
   - Billing enabled (free tier sufficient for low traffic)

2. **External Services**
   - **Qdrant** (vector database): Get API URL and key from [cloud.qdrant.io](https://cloud.qdrant.io)
   - **OpenAI** (embeddings): Get API key from [platform.openai.com](https://platform.openai.com)
   - **GROQ** (LLM, optional but recommended): Get API key from [console.groq.com](https://console.groq.com)

### GCP Configuration

The project uses the following GCP settings (defined in `gcp_config.sh`):
```bash
PROJECT_ID="docker-app-20250605"
LOCATION="us-central1"
REPOSITORY="cohort-1"
```

## Quick Start

### First-Time Deployment (5 minutes)

```bash
# 1. Navigate to GCP directory
cd GCP

# 2. Login to Google Cloud
gcloud auth login

# 3. One-time GCP setup (enables APIs, creates registry)
./setup_gcp.sh

# 4. Set your API keys securely
./set_secrets.sh
# Follow prompts to enter:
# - Qdrant API Key
# - OpenAI API Key
# - GROQ API Key (optional)

# 5. Ensure .env.docker has QDRANT_API_URL
# Edit ../env.docker and add:
# QDRANT_API_URL=https://your-qdrant-instance.cloud.qdrant.io

# 6. Deploy the application
./deploy.sh
```

That's it! The script will output your application URLs.

### Subsequent Deployments (2 minutes)

After the first setup, redeployment is simple:

```bash
cd GCP
./deploy.sh
```

## Detailed Setup

### Step 1: GCP Authentication

```bash
# Login to Google Cloud
gcloud auth login

# This opens a browser for authentication
# Select your Google account
# Grant permissions

# Verify authentication
gcloud auth list
```

### Step 2: One-Time GCP Setup

The `setup_gcp.sh` script performs the following:

```bash
cd GCP
./setup_gcp.sh
```

What it does:
1. ✅ Sets active GCP project
2. ✅ Enables required APIs:
   - Cloud Run (container hosting)
   - Artifact Registry (Docker image storage)
   - Secret Manager (API key storage)
   - Cloud Build (image building)
3. ✅ Creates Artifact Registry repository
4. ✅ Configures Docker authentication
5. ✅ Creates placeholder secrets

**Expected output:**
```
==================================================
GCP Setup for Texas Childcare Chatbot
==================================================
Project ID: docker-app-20250605
Location: us-central1
Repository: cohort-1

✓ gcloud CLI found
✓ gcloud authenticated
✓ APIs enabled
✓ Repository 'cohort-1' created
✓ Docker authentication configured
✓ Service account permissions configured

Next steps:
1. Set your API keys: ./set_secrets.sh
2. Deploy the application: ./deploy.sh
```

### Step 3: Configure API Keys

The `set_secrets.sh` script stores your API keys securely in GCP Secret Manager:

```bash
./set_secrets.sh
```

**Interactive prompts:**
```
Qdrant API Key
Enter Qdrant API Key: [paste your key]
✓ Secret 'qdrant-api-key' updated

OpenAI API Key
Enter OpenAI API Key: [paste your key]
✓ Secret 'openai-api-key' updated

GROQ API Key (optional)
Enter GROQ API Key: [paste your key or 'skip']
✓ Secret 'groq-api-key' updated
```

The script can auto-detect values from `../.env.docker` if present.

### Step 4: Set QDRANT_API_URL

Create or edit `.env.docker` in the project root:

```bash
cd ..
cp .env.docker.example .env.docker
nano .env.docker
```

Add your Qdrant URL:
```bash
QDRANT_API_URL=https://your-qdrant-instance.cloud.qdrant.io
```

This is a non-sensitive URL, so it's stored as a direct environment variable (not in Secret Manager).

## Deployment

### Deploy Script (`deploy.sh`)

The deployment script handles the complete deployment pipeline:

```bash
cd GCP
./deploy.sh
```

**What it does:**

1. **Build Docker Images** (~3-5 minutes)
   - Builds backend (FastAPI + chatbot)
   - Builds frontend (Next.js 15)
   - Tags for Artifact Registry

2. **Push to Artifact Registry** (~2-3 minutes)
   - Uploads backend image
   - Uploads frontend image

3. **Deploy Backend to Cloud Run** (~1-2 minutes)
   - Creates/updates Cloud Run service
   - Configures environment variables
   - Attaches secrets from Secret Manager
   - Enables public access (unauthenticated)
   - Sets resource limits (1 CPU, 1GB RAM)

4. **Deploy Frontend to Cloud Run** (~1-2 minutes)
   - Creates/updates Cloud Run service
   - Configures backend URL
   - Sets resource limits (1 CPU, 512MB RAM)

**Total time:** ~7-10 minutes

**Expected output:**
```
==================================================
Deploying Texas Childcare Chatbot to GCP
==================================================

✓ Prerequisites verified

Building backend image...
✓ Backend image built

Building frontend image...
✓ Frontend image built

Pushing backend image...
✓ Backend image pushed

Pushing frontend image...
✓ Frontend image pushed

Deploying backend service...
✓ Backend deployed
  URL: https://tx-childcare-backend-abc123-uc.a.run.app

Deploying frontend service...
✓ Frontend deployed
  URL: https://tx-childcare-frontend-xyz789-uc.a.run.app

==================================================
✅ Deployment Complete!
==================================================

🌐 Application URLs:
   Frontend:  https://tx-childcare-frontend-xyz789-uc.a.run.app
   Backend:   https://tx-childcare-backend-abc123-uc.a.run.app
   API Docs:  https://tx-childcare-backend-abc123-uc.a.run.app/docs
```

### Testing the Deployment

```bash
# Get backend URL from deployment output
BACKEND_URL="https://tx-childcare-backend-abc123-uc.a.run.app"

# Test health endpoint
curl ${BACKEND_URL}/api/health

# Expected response:
# {
#   "status": "ok",
#   "chatbot_initialized": true,
#   "timestamp": "2025-10-13T12:00:00Z"
# }

# Test chatbot query
curl -X POST ${BACKEND_URL}/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is CCAP?"}'

# Test frontend (open in browser)
open https://tx-childcare-frontend-xyz789-uc.a.run.app
```

## Configuration

### Cloud Run Service Configuration

**Backend Service:**
```yaml
Service Name: tx-childcare-backend
Region: us-central1
Container Port: 8000
Memory: 1 GB
CPU: 1 vCPU
Min Instances: 0 (scales to zero)
Max Instances: 10
Timeout: 300s (5 minutes)
Authentication: Allow unauthenticated
```

**Frontend Service:**
```yaml
Service Name: tx-childcare-frontend
Region: us-central1
Container Port: 3000
Memory: 512 MB
CPU: 1 vCPU
Min Instances: 0 (scales to zero)
Max Instances: 10
Timeout: 300s
Authentication: Allow unauthenticated
```

### Environment Variables

**Backend:**
- `QDRANT_API_URL` - Qdrant instance URL (from .env.docker)
- `QDRANT_API_KEY` - Secret from Secret Manager
- `OPENAI_API_KEY` - Secret from Secret Manager
- `GROQ_API_KEY` - Secret from Secret Manager
- `LLM_PROVIDER=groq` - Default LLM provider
- `RERANKER_PROVIDER=groq` - Default reranker provider
- `INTENT_CLASSIFIER_PROVIDER=groq` - Default intent classifier

**Frontend:**
- `NEXT_PUBLIC_API_URL` - Backend URL (auto-configured)
- `NODE_ENV=production` - Production mode

### Updating Environment Variables

**Update non-secret variables:**
```bash
gcloud run services update tx-childcare-backend \
  --region=us-central1 \
  --update-env-vars="LLM_PROVIDER=openai"
```

**Update secrets:**
```bash
cd GCP
./set_secrets.sh
# Then redeploy
./deploy.sh
```

## Management

### Viewing Service Status

```bash
# List all Cloud Run services
gcloud run services list --region=us-central1

# Describe specific service
gcloud run services describe tx-childcare-backend --region=us-central1
```

### Viewing Logs

```bash
# Backend logs (live stream)
gcloud run services logs tail tx-childcare-backend --region=us-central1

# Frontend logs (live stream)
gcloud run services logs tail tx-childcare-frontend --region=us-central1

# Or view in Cloud Console:
# https://console.cloud.google.com/run
```

### Monitoring

**Cloud Console:**
- Navigate to [Cloud Run Console](https://console.cloud.google.com/run)
- Select service (backend or frontend)
- View metrics:
  - Request count
  - Request latency
  - Instance count
  - Memory usage
  - CPU utilization

**CLI:**
```bash
# Get service metrics
gcloud run services describe tx-childcare-backend \
  --region=us-central1 \
  --format="get(status.conditions)"
```

### Rollback to Previous Version

Cloud Run keeps previous revisions:

```bash
# List revisions
gcloud run revisions list \
  --service=tx-childcare-backend \
  --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic tx-childcare-backend \
  --region=us-central1 \
  --to-revisions=tx-childcare-backend-00005-abc=100
```

### Scaling Configuration

**Update min/max instances:**
```bash
gcloud run services update tx-childcare-backend \
  --region=us-central1 \
  --min-instances=1 \
  --max-instances=20
```

**Note:** Setting `--min-instances=1` keeps one instance always warm (faster cold starts but higher cost).

### Delete Services

```bash
# Delete specific service
gcloud run services delete tx-childcare-backend --region=us-central1

# Delete all services
gcloud run services delete tx-childcare-backend --region=us-central1
gcloud run services delete tx-childcare-frontend --region=us-central1
```

## Troubleshooting

### Deployment Issues

**Problem: "gcloud: command not found"**
```bash
# Install Google Cloud SDK
# Visit: https://cloud.google.com/sdk/docs/install
```

**Problem: "Permission denied" errors**
```bash
# Re-authenticate
gcloud auth login

# Set project
gcloud config set project docker-app-20250605
```

**Problem: Docker build fails**
```bash
# Ensure Docker is running
docker ps

# On Mac/Windows, start Docker Desktop
# On Linux, start Docker daemon
sudo systemctl start docker
```

**Problem: "API not enabled" error**
```bash
# Re-run setup script
cd GCP
./setup_gcp.sh
```

### Runtime Issues

**Problem: Backend health check fails**

Check logs:
```bash
gcloud run services logs tail tx-childcare-backend --region=us-central1
```

Common causes:
- Missing/invalid Qdrant credentials
- Missing OpenAI API key
- Qdrant collection not initialized

**Problem: Frontend can't connect to backend**

Verify backend URL:
```bash
gcloud run services describe tx-childcare-frontend \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

The `NEXT_PUBLIC_API_URL` should match the backend URL.

**Problem: Chatbot queries time out**

Increase timeout:
```bash
gcloud run services update tx-childcare-backend \
  --region=us-central1 \
  --timeout=600
```

**Problem: Out of memory errors**

Increase memory:
```bash
gcloud run services update tx-childcare-backend \
  --region=us-central1 \
  --memory=2Gi
```

### Secret Management Issues

**Problem: Secrets not accessible**

Grant Secret Manager access:
```bash
PROJECT_NUMBER=$(gcloud projects describe docker-app-20250605 --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding qdrant-api-key \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

**Problem: Need to view secret value**

```bash
# View latest secret version
gcloud secrets versions access latest --secret=qdrant-api-key
```

### Image Build Issues

**Problem: Frontend build fails with "Module not found"**

Ensure `package-lock.json` exists:
```bash
cd frontend
npm install
git add package-lock.json
git commit -m "Add package-lock.json"
```

**Problem: Backend build fails with missing dependencies**

Update `backend/requirements.txt`:
```bash
cd backend
pip freeze > requirements.txt
```

## Cost Optimization

### Estimated Monthly Costs (Low Traffic)

Assumptions: 100 requests/day, average 3 seconds per request

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Run (Backend) | ~10 CPU-hours, ~10 GB-hours | $3-5 |
| Cloud Run (Frontend) | ~5 CPU-hours, ~5 GB-hours | $2-3 |
| Artifact Registry | ~500 MB storage | $0.10 |
| Secret Manager | 6 secrets, ~300 accesses | Free |
| **Total** | | **~$5-10/month** |

### Cost Optimization Tips

1. **Use Free Tier**
   - Cloud Run: 2 million requests/month free
   - Artifact Registry: 0.5 GB storage free

2. **Scale to Zero**
   ```bash
   # Ensure min-instances=0 (default)
   gcloud run services update tx-childcare-backend \
     --min-instances=0 \
     --region=us-central1
   ```

3. **Reduce Memory if Possible**
   ```bash
   # Test with lower memory
   gcloud run services update tx-childcare-frontend \
     --memory=256Mi \
     --region=us-central1
   ```

4. **Use GROQ for LLM Calls**
   - GROQ offers free tier with faster responses
   - OpenAI charges per token

5. **Monitor Usage**
   - View billing: [Cloud Console Billing](https://console.cloud.google.com/billing)
   - Set up budget alerts

6. **Delete Unused Revisions**
   ```bash
   # List revisions
   gcloud run revisions list --service=tx-childcare-backend --region=us-central1

   # Delete old revisions
   gcloud run revisions delete tx-childcare-backend-00001-abc --region=us-central1
   ```

### Estimated Costs for Higher Traffic

| Traffic Level | Requests/Day | Est. Monthly Cost |
|---------------|--------------|-------------------|
| Low | 100 | $5-10 |
| Medium | 1,000 | $15-25 |
| High | 10,000 | $50-100 |
| Very High | 100,000 | $300-500 |

## Custom Domain (Optional)

To use a custom domain (e.g., `chatbot.yourdomain.com`):

1. **Verify domain ownership:**
   ```bash
   gcloud domains verify yourdomain.com
   ```

2. **Map domain to Cloud Run:**
   ```bash
   gcloud run domain-mappings create \
     --service=tx-childcare-frontend \
     --domain=chatbot.yourdomain.com \
     --region=us-central1
   ```

3. **Update DNS records** with the provided values

## CI/CD Integration (Future Enhancement)

For automated deployment on git push, consider GitHub Actions:

```yaml
# .github/workflows/deploy-gcp.yml
name: Deploy to GCP

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: docker-app-20250605
      - name: Deploy
        run: |
          cd GCP
          ./deploy.sh
```

## Support & Resources

- **GCP Documentation**: https://cloud.google.com/run/docs
- **Artifact Registry**: https://cloud.google.com/artifact-registry/docs
- **Secret Manager**: https://cloud.google.com/secret-manager/docs
- **Project Docs**: See `../CLAUDE.md` for architecture details
- **Local Docker Guide**: See `../DOCKER_DEPLOYMENT.md`

## Quick Reference

### Essential Commands

```bash
# Deploy/redeploy
cd GCP && ./deploy.sh

# Update secrets
cd GCP && ./set_secrets.sh

# View logs
gcloud run services logs tail tx-childcare-backend --region=us-central1

# Test health
curl https://[backend-url]/api/health

# List services
gcloud run services list --region=us-central1

# Delete service
gcloud run services delete tx-childcare-backend --region=us-central1
```

### File Locations

- **Scripts**: `GCP/*.sh`
- **Config**: `GCP/gcp_config.sh`
- **Docs**: `GCP/DEPLOYMENT_GUIDE.md` (this file)
- **Environment**: `.env.docker` (project root)
- **Backend Dockerfile**: `backend/Dockerfile`
- **Frontend Dockerfile**: `frontend/Dockerfile`
