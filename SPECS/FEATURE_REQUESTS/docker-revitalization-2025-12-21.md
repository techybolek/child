# Feature Request: Docker Deployment Revitalization

**Date:** 2025-12-21
**Status:** Refined

## Overview
Update the existing Docker deployment configuration to reflect all current environment variables, configuration options, and provide complete documentation for local development and GCP deployment.

## Problem Statement
The Docker setup was created earlier in development. Since then, many new configuration options have been added (multiple LLM providers, retrieval modes, conversational mode, etc.) that are not reflected in `docker-compose.yml`. Users cannot deploy via Docker with feature parity to local development.

## Users & Stakeholders
- Primary Users: Developers deploying to GCP, local Docker testing
- Permissions: None required (prototype)

## Functional Requirements

1. **Update `docker-compose.yml`** - Add ALL environment variables from `chatbot/config.py` to ensure Docker deployment matches local behavior exactly
2. **Create `.env.example`** - Template file with all required and optional environment variables with descriptions
3. **Create `DOCKER.md`** - Comprehensive documentation covering:
   - Local Docker development setup
   - GCP Cloud Run deployment instructions
   - Environment variable reference

## Acceptance Criteria

- [ ] `docker-compose.yml` includes all environment variables from `chatbot/config.py`
- [ ] `docker compose up` works out-of-the-box with a properly configured `.env` file
- [ ] `.env.example` documents all variables with descriptions and default values
- [ ] `DOCKER.md` contains local development instructions
- [ ] `DOCKER.md` contains GCP Cloud Run deployment instructions
- [ ] Backend container starts and passes health check
- [ ] Frontend container starts and connects to backend
- [ ] Chat functionality works identically to local development

## Environment Variables to Add

### Required (no defaults)
```
QDRANT_API_URL
QDRANT_API_KEY
OPENAI_API_KEY
GROQ_API_KEY
```

### Optional with Defaults (from chatbot/config.py)
```
# Provider Selection
LLM_PROVIDER=groq
RERANKER_PROVIDER=groq
REFORMULATOR_PROVIDER=groq
INTENT_CLASSIFIER_PROVIDER=groq

# Retrieval
RETRIEVAL_MODE=dense
CONVERSATIONAL_MODE=true

# OpenAI Agent (evaluation)
OPENAI_VECTOR_STORE_ID=vs_69210129c50c81919a906d0576237ff5
OPENAI_AGENT_MODEL=gpt-5-nano

# Vertex AI (evaluation)
VERTEX_PROJECT_ID=docker-app-20250605
VERTEX_LOCATION=us-west1
VERTEX_CORPUS_NAME=projects/112470053465/locations/us-west1/ragCorpora/2305843009213693952
VERTEX_AGENT_MODEL=gemini-2.5-flash

# Bedrock KB (evaluation)
BEDROCK_KB_ID=371M2G58TV
BEDROCK_MODEL=nova-pro
AWS_REGION=us-east-1
```

## Technical Requirements

- **Containers**: Backend (Python 3.11) + Frontend (Node 20 Alpine)
- **External Dependencies**: Qdrant Cloud (no local Qdrant container)
- **Target Platform**: GCP Cloud Run
- **Networking**: Internal Docker network for backend-frontend communication

## Files to Modify/Create

| File | Action |
|------|--------|
| `docker-compose.yml` | Update - add all env vars |
| `.env.example` | Create - template with descriptions |
| `DOCKER.md` | Create - deployment documentation |

## Out of Scope

- LOAD_DB scripts containerization
- Evaluation tools containerization
- Local Qdrant container for dev/testing
- Docker secrets / advanced secret management
- CI/CD pipeline configuration
- Kubernetes/Helm charts

## Success Metrics

- `docker compose up` successfully starts both services
- Chat queries return responses identical to local development
- New developer can deploy to GCP following DOCKER.md instructions

## Notes

- Existing Dockerfiles are functional - no changes needed
- Frontend already configured for standalone output
- Health checks already in place
