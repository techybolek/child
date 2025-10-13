# Docker Deployment Guide

Texas Childcare Chatbot - Containerized Backend & Frontend

## Prerequisites

- Docker Desktop installed with WSL 2 integration enabled
- API keys for Qdrant, OpenAI, and/or GROQ

## Quick Start

### 1. Configure Environment Variables

```bash
# Copy the example file
cp .env.docker.example .env.docker

# Edit with your actual API keys
nano .env.docker
```

Required environment variables:
- `QDRANT_API_URL` - Your Qdrant instance URL
- `QDRANT_API_KEY` - Qdrant API key
- `OPENAI_API_KEY` - OpenAI API key (required for embeddings)
- `GROQ_API_KEY` - GROQ API key (optional, recommended for faster LLM)

### 2. Build and Run

```bash
# Build images
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f
```

### 3. Run Tests (Automated)

```bash
# Run comprehensive test suite
./test_docker.sh
```

This will:
- ✓ Check Docker availability
- ✓ Build and start containers
- ✓ Test backend health endpoint
- ✓ Test chatbot functionality
- ✓ Verify frontend accessibility

### 4. Access Services

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Manual Testing

### Test Backend Health

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "chatbot_initialized": true,
  "timestamp": "2025-10-13T12:00:00Z"
}
```

### Test Chatbot Query

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the income limit for CCAP?"}'
```

Expected response:
```json
{
  "answer": "According to the documents...",
  "sources": [...],
  "response_type": "information",
  "processing_time": 3.45,
  "session_id": "...",
  "timestamp": "2025-10-13T12:00:00Z"
}
```

### Test Frontend

Open browser: http://localhost:3000

## Docker Commands

### View Container Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

### Restart Services
```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart backend
docker compose restart frontend
```

### Stop Services
```bash
# Stop containers (preserves data)
docker compose stop

# Stop and remove containers
docker compose down

# Stop and remove with volumes
docker compose down -v
```

### Rebuild After Changes
```bash
# Rebuild specific service
docker compose up --build backend

# Rebuild all
docker compose up --build
```

## Architecture

```
┌─────────────────────┐       ┌─────────────────────┐
│   Frontend          │       │   Backend           │
│   Next.js 15        │──────▶│   FastAPI           │
│   React 19          │       │   + Chatbot         │
│   Port 3000         │       │   Port 8000         │
└─────────────────────┘       └─────────────────────┘
         │                             │
         │                             │
         └──────────┬──────────────────┘
                    │
            Docker Network
                    │
         ┌──────────┴──────────┐
         │                     │
    Qdrant (external)    GROQ/OpenAI (external)
```

## Container Details

### Backend Container
- **Image**: Python 3.11 slim
- **Dependencies**: FastAPI, uvicorn, qdrant-client, openai, groq, langchain-openai
- **Includes**: backend/ + chatbot/ modules
- **Health check**: Polls /api/health every 30s
- **Restart policy**: unless-stopped

### Frontend Container
- **Image**: Node 20 alpine (multi-stage build)
- **Build**: Next.js 15 standalone output
- **User**: Non-root user (nextjs:nodejs)
- **Depends on**: Backend health check
- **Restart policy**: unless-stopped

## Troubleshooting

### Backend fails to start

1. Check environment variables:
```bash
docker compose config
```

2. View backend logs:
```bash
docker compose logs backend
```

3. Common issues:
   - Missing API keys in .env.docker
   - Invalid Qdrant URL/credentials
   - Port 8000 already in use

### Frontend can't connect to backend

1. Check network connectivity:
```bash
docker compose exec frontend ping backend
```

2. Verify backend is healthy:
```bash
curl http://localhost:8000/api/health
```

3. Check NEXT_PUBLIC_API_URL in docker-compose.yml

### Chatbot queries fail

1. Check Qdrant connection:
```bash
docker compose logs backend | grep -i qdrant
```

2. Verify API keys are set correctly
3. Test with simple query:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}'
```

### Docker not found in WSL

Enable WSL 2 integration in Docker Desktop:
1. Open Docker Desktop Settings
2. Resources → WSL Integration
3. Enable integration for your distro
4. Restart WSL: `wsl --shutdown`

## Production Considerations

For production deployment:

1. **Environment Variables**: Use Docker secrets or external secret management
2. **Reverse Proxy**: Add Nginx for SSL/TLS termination
3. **Resource Limits**: Set CPU/memory limits in docker-compose.yml
4. **Logging**: Configure centralized logging (ELK, CloudWatch, etc.)
5. **Monitoring**: Add health check endpoints and monitoring
6. **Scaling**: Use Docker Swarm or Kubernetes for multi-instance deployment

## File Structure

```
.
├── backend/
│   ├── Dockerfile              # Backend container definition
│   ├── .dockerignore           # Excluded files
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── Dockerfile              # Frontend container definition
│   └── .dockerignore           # Excluded files
├── docker-compose.yml          # Service orchestration
├── .env.docker                 # Environment variables (gitignored)
├── .env.docker.example         # Environment template
├── test_docker.sh              # Automated test script
└── DOCKER_DEPLOYMENT.md        # This file
```

## Updates and Maintenance

### Updating Dependencies

Backend:
```bash
# Edit backend/requirements.txt
# Rebuild
docker compose build backend
docker compose up -d backend
```

Frontend:
```bash
# Edit frontend/package.json
# Rebuild
docker compose build frontend
docker compose up -d frontend
```

### Pulling Latest Code

```bash
git pull
docker compose down
docker compose build
docker compose up -d
```

## Support

For issues or questions:
- Check logs: `docker compose logs -f`
- Run test script: `./test_docker.sh`
- Review CLAUDE.md for project architecture details
