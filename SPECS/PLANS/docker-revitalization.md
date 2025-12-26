# Feature: Docker Deployment Revitalization

## Feature Description
Update the existing Docker deployment configuration to achieve full feature parity with local development. This includes:
- Adding all environment variables from `chatbot/config.py` to `docker-compose.yml`
- Creating a comprehensive `.env.example` template at the project root
- Creating `DOCKER.md` documentation for local development and GCP Cloud Run deployment

The feature ensures that Docker deployments can leverage all configuration options: multiple LLM providers, retrieval modes (hybrid/dense), conversational mode, and evaluation settings for external RAG systems (OpenAI, Vertex, Bedrock, Kendra).

## Problem Statement
The Docker setup was created earlier in development and lacks many configuration options added since:
- Missing `RETRIEVAL_MODE` environment variable (hybrid vs dense retrieval)
- Missing `CONVERSATIONAL_MODE` setting
- Missing `REFORMULATOR_PROVIDER` setting
- Missing evaluation-specific variables (OpenAI Agent, Vertex AI, Bedrock KB, Kendra)
- `.env.docker.example` exists but is incomplete
- `SPECS/PLANS/DOCKER_DEPLOYMENT.md` exists but lacks GCP Cloud Run deployment instructions

Users cannot deploy via Docker with full feature parity to local development.

## Solution Statement
1. Update `docker-compose.yml` to pass all environment variables from `chatbot/config.py` to the backend container
2. Create a comprehensive `.env.example` at project root (consolidate from existing `.env.docker.example`)
3. Create `DOCKER.md` at project root with complete documentation including GCP Cloud Run deployment

## Requirements

### Functional Requirements
- `docker-compose.yml` passes all env vars from `chatbot/config.py` to backend container
- `.env.example` documents all required and optional variables with descriptions
- `DOCKER.md` provides local development setup instructions
- `DOCKER.md` provides GCP Cloud Run deployment instructions
- Backend container starts successfully with configured `.env` file
- Frontend container connects to backend and functions correctly
- Chat functionality works identically to local development

### Non-Functional Requirements
- Maintain backward compatibility with existing `.env.docker` files
- Clear documentation that new developers can follow
- No changes required to existing Dockerfiles

## Design Decisions

### 1. Environment File Location
**Decision**: Create `.env.example` at project root rather than updating `.env.docker.example`
**Rationale**: Docker Compose automatically loads `.env` from project root. Using standard naming conventions (`.env.example` → `.env`) is more intuitive than custom names.

### 2. Variable Organization
**Decision**: Group variables by category (Required, Provider Selection, Retrieval, Evaluation)
**Rationale**: Makes it easier for users to identify which variables they need based on their use case.

### 3. Documentation Structure
**Decision**: Create new `DOCKER.md` at project root rather than updating `SPECS/PLANS/DOCKER_DEPLOYMENT.md`
**Rationale**: Root-level documentation is more discoverable. The existing file is a "plan" not user documentation.

### 4. GCP Cloud Run Approach
**Decision**: Document Cloud Run deployment using `gcloud run deploy` with pre-built container images
**Rationale**: Simplest path for this prototype. Avoids complexity of Cloud Build, Artifact Registry configuration.

### 5. Frontend Build Args
**Decision**: Keep using `NEXT_PUBLIC_API_URL=http://backend:8000` for Docker Compose, document Cloud Run URL configuration separately
**Rationale**: Frontend requires API URL at build time. Docker internal networking uses service names, Cloud Run uses public URLs.

## Relevant Files
Use these files to implement the feature:

- **`docker-compose.yml`** - Main Docker Compose configuration to update with all environment variables
- **`chatbot/config.py`** - Source of truth for all chatbot environment variables to mirror in Docker
- **`backend/config.py`** - Backend API configuration (CORS settings, server config)
- **`.env.docker.example`** - Existing partial template to reference for structure
- **`backend/.env.example`** - Existing backend-specific template for reference
- **`SPECS/PLANS/DOCKER_DEPLOYMENT.md`** - Existing Docker documentation to reference for structure
- **`test_docker.sh`** - Existing test script (no changes needed, validates our work)
- **`backend/Dockerfile`** - Reference for understanding build context
- **`frontend/Dockerfile`** - Reference for understanding frontend build process

### New Files
- **`.env.example`** - New comprehensive environment template at project root
- **`DOCKER.md`** - New comprehensive Docker deployment documentation at project root

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Update docker-compose.yml with All Environment Variables

Update the backend service environment section to include all variables from `chatbot/config.py`:

- Add `RETRIEVAL_MODE` with default `dense`
- Add `CONVERSATIONAL_MODE` with default `true`
- Add `REFORMULATOR_PROVIDER` with default `groq`
- Add evaluation settings section (OpenAI Agent, Vertex AI, Bedrock KB, Kendra)
- Organize variables into logical groups with comments
- Ensure all variables use `${VAR:-default}` syntax for defaults

### Step 2: Create .env.example at Project Root

Create comprehensive environment template with:

- Header explaining purpose and usage
- **Required Variables** section:
  - `QDRANT_API_URL` - Qdrant Cloud instance URL
  - `QDRANT_API_KEY` - Qdrant API key
  - `OPENAI_API_KEY` - Required for embeddings
  - `GROQ_API_KEY` - Required if using GROQ provider
- **Provider Selection** section:
  - `LLM_PROVIDER` - groq (default) or openai
  - `RERANKER_PROVIDER` - groq (default) or openai
  - `REFORMULATOR_PROVIDER` - groq (default) or openai
  - `INTENT_CLASSIFIER_PROVIDER` - groq (default) or openai
- **Retrieval Settings** section:
  - `RETRIEVAL_MODE` - dense (default) or hybrid
  - `CONVERSATIONAL_MODE` - true (default) or false
- **Evaluation Settings** section (optional, for running evaluation modes):
  - OpenAI Agent settings
  - Vertex AI settings
  - Bedrock KB settings
  - Kendra settings

### Step 3: Create DOCKER.md Documentation

Create comprehensive documentation at project root with:

- **Overview** - What the Docker setup provides
- **Prerequisites** - Docker Desktop, API keys
- **Quick Start** - Copy env, build, run commands
- **Local Development** section:
  - Environment setup instructions
  - Build and run commands
  - Testing with `test_docker.sh`
  - Accessing services (URLs)
  - Viewing logs
- **GCP Cloud Run Deployment** section:
  - Prerequisites (gcloud CLI, project setup)
  - Building and pushing images to Container Registry
  - Deploying backend to Cloud Run
  - Deploying frontend to Cloud Run (with correct API URL)
  - Environment variable configuration in Cloud Run
  - Service URL configuration
- **Environment Variables Reference** - Complete table of all variables
- **Architecture Diagram** - Container and service relationships
- **Troubleshooting** - Common issues and solutions
- **Docker Commands Reference** - Quick command cheat sheet

### Step 4: Clean Up Redundant Files

- Delete `SPECS/PLANS/DOCKER_DEPLOYMENT.md` (superseded by root `DOCKER.md`)
- Optionally delete `.env.docker.example` if redundant with `.env.example`
- Update any references in `CLAUDE.md` if needed

### Step 5: Validate Docker Setup

Run the validation commands to confirm everything works correctly.

## Validation Commands
Execute every command to validate the feature is complete with zero regressions.

```bash
# 1. Verify docker-compose.yml is valid YAML and loads correctly
docker compose config > /dev/null && echo "docker-compose.yml is valid"

# 2. Verify .env.example exists and has all required sections
grep -q "QDRANT_API_URL" .env.example && \
grep -q "RETRIEVAL_MODE" .env.example && \
grep -q "CONVERSATIONAL_MODE" .env.example && \
grep -q "BEDROCK_KB_ID" .env.example && \
echo ".env.example has all required variables"

# 3. Verify DOCKER.md exists and has required sections
grep -q "Quick Start" DOCKER.md && \
grep -q "GCP Cloud Run" DOCKER.md && \
grep -q "Environment Variables" DOCKER.md && \
echo "DOCKER.md has all required sections"

# 4. Copy .env.example to .env and fill with actual values (manual step)
# cp .env.example .env
# Edit .env with actual API keys

# 5. Build and test Docker deployment
# docker compose build
# ./test_docker.sh

# 6. Verify backend health
# curl http://localhost:8000/api/health

# 7. Test chat endpoint with hybrid mode (requires RETRIEVAL_MODE=hybrid in .env)
# curl -X POST http://localhost:8000/api/chat \
#   -H "Content-Type: application/json" \
#   -d '{"question": "What is the income limit for CCAP?"}'
```

## Notes

- **No Dockerfile Changes Required**: Both `backend/Dockerfile` and `frontend/Dockerfile` are functional and don't need modifications.
- **AWS Credentials for Evaluation**: For Bedrock KB and Kendra evaluation modes, AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) must be configured. These are NOT included in docker-compose.yml for security - document that users should use `~/.aws/credentials` volume mount or AWS IAM roles in Cloud Run.
- **Frontend API URL at Build Time**: The frontend Next.js app bakes `NEXT_PUBLIC_API_URL` at build time. For Cloud Run, the frontend must be rebuilt with the correct backend URL.
- **GCP Service Account**: Cloud Run deployments will need a service account with appropriate permissions. Document this in the Cloud Run section.
- **Cleanup Decision**: The existing `.env.docker.example` and `SPECS/PLANS/DOCKER_DEPLOYMENT.md` can be removed once the new files are in place, as they will be redundant.
