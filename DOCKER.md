# Docker Deployment Guide

Texas Child Care Solutions - Containerized Backend & Frontend

## Overview

This guide covers Docker deployment for local development and GCP Cloud Run production deployment. The Docker setup provides full feature parity with local development, including:

- Multiple LLM providers (GROQ, OpenAI)
- Retrieval modes (hybrid, dense)
- Conversational mode with query reformulation
- Evaluation system support for external RAG systems

## Prerequisites

- Docker Desktop installed (with WSL 2 integration on Windows)
- API keys: Qdrant, OpenAI, and/or GROQ
- For GCP deployment: `gcloud` CLI installed and authenticated

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your actual API keys
nano .env  # or use your preferred editor

# 3. Build images
docker compose build

# 4. Start services
docker compose up -d

# 5. Verify deployment
./test_docker.sh
```

Access the application:
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Local Development

### Environment Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual values:
   ```bash
   # Required
   QDRANT_API_URL=https://your-instance.cloud.qdrant.io
   QDRANT_API_KEY=your-key
   OPENAI_API_KEY=your-openai-key
   GROQ_API_KEY=your-groq-key

   # Optional overrides
   RETRIEVAL_MODE=hybrid    # or "dense" (default)
   LLM_PROVIDER=groq        # or "openai"
   ```

### Build and Run

```bash
# Build images
docker compose build

# Start in foreground (see logs)
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f
docker compose logs -f backend   # backend only
docker compose logs -f frontend  # frontend only
```

### Testing

Run the automated test suite:
```bash
./test_docker.sh
```

Manual testing:
```bash
# Health check
curl http://localhost:8000/api/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the income limit for CCAP?"}'
```

### Container Management

```bash
# View status
docker compose ps

# Restart services
docker compose restart
docker compose restart backend

# Stop services
docker compose stop

# Stop and remove containers
docker compose down

# Rebuild after code changes
docker compose up --build
```

## GCP Cloud Run Deployment

### Prerequisites

1. Install and authenticate gcloud CLI:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. Enable required APIs:
   ```bash
   gcloud services enable containerregistry.googleapis.com
   gcloud services enable run.googleapis.com
   ```

### Build and Push Images

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Build and tag backend image
docker build -t gcr.io/YOUR_PROJECT_ID/tx-childcare-backend:latest \
  -f backend/Dockerfile .

# Build frontend (with production API URL)
docker build -t gcr.io/YOUR_PROJECT_ID/tx-childcare-frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL=https://YOUR_BACKEND_URL \
  ./frontend

# Push images
docker push gcr.io/YOUR_PROJECT_ID/tx-childcare-backend:latest
docker push gcr.io/YOUR_PROJECT_ID/tx-childcare-frontend:latest
```

### Deploy Backend to Cloud Run

```bash
gcloud run deploy tx-childcare-backend \
  --image gcr.io/YOUR_PROJECT_ID/tx-childcare-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "QDRANT_API_URL=YOUR_QDRANT_URL" \
  --set-env-vars "QDRANT_API_KEY=YOUR_QDRANT_KEY" \
  --set-env-vars "OPENAI_API_KEY=YOUR_OPENAI_KEY" \
  --set-env-vars "GROQ_API_KEY=YOUR_GROQ_KEY" \
  --set-env-vars "LLM_PROVIDER=groq" \
  --set-env-vars "RETRIEVAL_MODE=dense" \
  --set-env-vars "CONVERSATIONAL_MODE=true" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300
```

Note the deployed backend URL (e.g., `https://tx-childcare-backend-xxxxx.run.app`).

### Deploy Frontend to Cloud Run

Rebuild frontend with the backend URL:
```bash
# Rebuild with production API URL
docker build -t gcr.io/YOUR_PROJECT_ID/tx-childcare-frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL=https://tx-childcare-backend-xxxxx.run.app \
  ./frontend

docker push gcr.io/YOUR_PROJECT_ID/tx-childcare-frontend:latest

# Deploy frontend
gcloud run deploy tx-childcare-frontend \
  --image gcr.io/YOUR_PROJECT_ID/tx-childcare-frontend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1
```

### AWS Credentials for Evaluation Modes

For Bedrock KB and Kendra evaluation modes, configure AWS credentials:

**Option 1**: Set environment variables in Cloud Run:
```bash
--set-env-vars "AWS_ACCESS_KEY_ID=YOUR_KEY" \
--set-env-vars "AWS_SECRET_ACCESS_KEY=YOUR_SECRET"
```

**Option 2**: Use a service account with Workload Identity (recommended for production).

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QDRANT_API_URL` | Yes | - | Qdrant Cloud instance URL |
| `QDRANT_API_KEY` | Yes | - | Qdrant API key |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key (required for embeddings) |
| `GROQ_API_KEY` | Yes* | - | GROQ API key (*required if using GROQ provider) |
| `LLM_PROVIDER` | No | `groq` | LLM provider: `groq` or `openai` |
| `RERANKER_PROVIDER` | No | `groq` | Reranker provider: `groq` or `openai` |
| `INTENT_CLASSIFIER_PROVIDER` | No | `groq` | Intent classifier provider |
| `REFORMULATOR_PROVIDER` | No | `groq` | Query reformulator provider |
| `RETRIEVAL_MODE` | No | `dense` | Retrieval mode: `dense` or `hybrid` |
| `CONVERSATIONAL_MODE` | No | `true` | Enable conversation memory |
| `OPENAI_VECTOR_STORE_ID` | No | - | OpenAI vector store (for evaluation) |
| `VERTEX_PROJECT_ID` | No | - | GCP project ID (for Vertex evaluation) |
| `VERTEX_CORPUS_NAME` | No | - | Vertex RAG corpus name |
| `BEDROCK_KB_ID` | No | - | AWS Bedrock KB ID (for evaluation) |
| `KENDRA_INDEX_ID` | No | - | AWS Kendra index ID (for evaluation) |

## Architecture

```
                     ┌─────────────────────────────────────────┐
                     │             Docker Network              │
                     │                                         │
   localhost:3000    │  ┌──────────────┐   ┌──────────────┐   │
        │            │  │   Frontend   │   │   Backend    │   │
        └────────────┼──│   Next.js    │──▶│   FastAPI    │   │
                     │  │   Port 3000  │   │   Port 8000  │   │
                     │  └──────────────┘   └──────┬───────┘   │
   localhost:8000    │                            │           │
        │            └────────────────────────────┼───────────┘
        └─────────────────────────────────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                    ┌─────▼─────┐          ┌──────▼──────┐         ┌──────▼──────┐
                    │  Qdrant   │          │ GROQ/OpenAI │         │  AWS/GCP    │
                    │  (Vector  │          │   (LLM)     │         │ (Optional)  │
                    │    DB)    │          │             │         │             │
                    └───────────┘          └─────────────┘         └─────────────┘
```

## Container Details

### Backend Container
- **Base**: Python 3.11 slim
- **Modules**: `backend/` + `chatbot/`
- **Health check**: `/api/health` every 30s
- **Restart policy**: `unless-stopped`

### Frontend Container
- **Base**: Node 20 alpine (multi-stage build)
- **Build**: Next.js 15 standalone output
- **User**: Non-root (`nextjs:nodejs`)
- **Depends on**: Backend health check

## Troubleshooting

### Backend fails to start

1. Verify environment variables:
   ```bash
   docker compose config | grep -A 50 environment
   ```

2. Check logs:
   ```bash
   docker compose logs backend
   ```

3. Common issues:
   - Missing API keys in `.env`
   - Invalid Qdrant URL/credentials
   - Port 8000 already in use

### Frontend can't connect to backend

1. Verify backend is healthy:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. Check Docker network:
   ```bash
   docker compose exec frontend wget -qO- http://backend:8000/api/health
   ```

### Chat queries fail

1. Check Qdrant connection:
   ```bash
   docker compose logs backend | grep -i qdrant
   ```

2. Verify API keys are correct
3. Test with simple query

### Docker not found in WSL

1. Open Docker Desktop Settings
2. Resources → WSL Integration
3. Enable integration for your distro
4. Restart WSL: `wsl --shutdown`

## Docker Commands Reference

```bash
# Build
docker compose build                    # Build all images
docker compose build backend            # Build specific service

# Run
docker compose up                       # Start foreground
docker compose up -d                    # Start background
docker compose up --build               # Rebuild and start

# Logs
docker compose logs -f                  # Follow all logs
docker compose logs -f backend          # Follow specific service

# Status
docker compose ps                       # List containers
docker compose config                   # Validate config

# Stop
docker compose stop                     # Stop containers
docker compose down                     # Stop and remove
docker compose down -v                  # Remove with volumes

# Restart
docker compose restart                  # Restart all
docker compose restart backend          # Restart specific
```
