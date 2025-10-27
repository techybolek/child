#!/bin/bash

# GCP Deployment Script for Texas Childcare Chatbot
# Builds Docker images, pushes to Artifact Registry, and deploys to Cloud Run

set -e  # Exit on any error

# Load GCP configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
source "${SCRIPT_DIR}/gcp_config.sh"

# Derived variables
REGISTRY_URL="${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}"
BACKEND_IMAGE="${REGISTRY_URL}/backend:latest"
FRONTEND_IMAGE="${REGISTRY_URL}/frontend:latest"
BACKEND_SERVICE="tx-childcare-backend"
FRONTEND_SERVICE="tx-childcare-frontend"

echo "=================================================="
echo "Deploying Texas Childcare Chatbot to GCP"
echo "=================================================="
echo "Project: ${PROJECT_ID}"
echo "Location: ${LOCATION}"
echo "Registry: ${REGISTRY_URL}"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    exit 1
fi

# Verify gcloud authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: Not logged in to gcloud. Run: gcloud auth login"
    exit 1
fi

# Set the project
gcloud config set project "${PROJECT_ID}" --quiet

echo "✓ Prerequisites verified"
echo ""

# Build and deploy backend first
echo "=================================================="
echo "Step 1: Build & Deploy Backend"
echo "=================================================="

echo ""
echo "Building backend image..."
cd "${PROJECT_ROOT}"
docker build \
    --platform linux/amd64 \
    -f backend/Dockerfile \
    -t backend:latest \
    -t "${BACKEND_IMAGE}" \
    .
echo "✓ Backend image built"

echo ""
echo "Pushing backend image..."
docker push "${BACKEND_IMAGE}"
echo "✓ Backend image pushed"

# Check if secrets exist and have values
echo ""
echo "Checking secrets..."
for secret in "qdrant-api-key" "openai-api-key" "groq-api-key"; do
    if ! gcloud secrets versions access latest --secret="${secret}" &> /dev/null; then
        echo "⚠️  Warning: Secret '${secret}' not set or inaccessible"
        echo "   Run: ./set_secrets.sh"
    fi
done

echo ""
echo "Deploying backend service..."

# Get QDRANT_API_URL from local .env.docker if it exists
QDRANT_URL=""
if [ -f "${PROJECT_ROOT}/.env.docker" ]; then
    QDRANT_URL=$(grep "^QDRANT_API_URL=" "${PROJECT_ROOT}/.env.docker" | cut -d'=' -f2-)
fi

if [ -z "${QDRANT_URL}" ]; then
    echo "⚠️  Warning: QDRANT_API_URL not found in .env.docker"
    echo "   Using placeholder. Update after deployment with:"
    echo "   gcloud run services update ${BACKEND_SERVICE} --update-env-vars QDRANT_API_URL=<your-url> --region=${LOCATION}"
    QDRANT_URL="https://your-qdrant-instance.cloud.qdrant.io"
fi

gcloud run deploy "${BACKEND_SERVICE}" \
    --image="${BACKEND_IMAGE}" \
    --region="${LOCATION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8000 \
    --memory=1Gi \
    --cpu=1 \
    --timeout=300 \
    --min-instances=0 \
    --max-instances=10 \
    --set-env-vars="QDRANT_API_URL=${QDRANT_URL},LLM_PROVIDER=groq,RERANKER_PROVIDER=groq,INTENT_CLASSIFIER_PROVIDER=groq" \
    --set-secrets="QDRANT_API_KEY=qdrant-api-key:latest,OPENAI_API_KEY=openai-api-key:latest,GROQ_API_KEY=groq-api-key:latest" \
    --quiet

BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
    --region="${LOCATION}" \
    --format="value(status.url)")

echo "✓ Backend deployed"
echo "  URL: ${BACKEND_URL}"

# Now build and deploy frontend with actual backend URL
echo ""
echo "=================================================="
echo "Step 2: Build & Deploy Frontend"
echo "=================================================="

echo ""
echo "Building frontend image with backend URL: ${BACKEND_URL}"
cd "${PROJECT_ROOT}/frontend"
docker build \
    --platform linux/amd64 \
    --build-arg NEXT_PUBLIC_API_URL="${BACKEND_URL}" \
    -t frontend:latest \
    -t "${FRONTEND_IMAGE}" \
    .
echo "✓ Frontend image built with API_URL=${BACKEND_URL}"

echo ""
echo "Pushing frontend image..."
docker push "${FRONTEND_IMAGE}"
echo "✓ Frontend image pushed"

echo ""
echo "Deploying frontend service..."

gcloud run deploy "${FRONTEND_SERVICE}" \
    --image="${FRONTEND_IMAGE}" \
    --region="${LOCATION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=3000 \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300 \
    --min-instances=0 \
    --max-instances=10 \
    --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL},NODE_ENV=production" \
    --quiet

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
    --region="${LOCATION}" \
    --format="value(status.url)")

echo "✓ Frontend deployed"
echo "  URL: ${FRONTEND_URL}"

# Summary
echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "🌐 Application URLs:"
echo "   Frontend:  ${FRONTEND_URL}"
echo "   Backend:   ${BACKEND_URL}"
echo "   API Docs:  ${BACKEND_URL}/docs"
echo ""
echo "🧪 Test the deployment:"
echo "   curl ${BACKEND_URL}/api/health"
echo ""
echo "📊 Monitor services:"
echo "   Backend:  https://console.cloud.google.com/run/detail/${LOCATION}/${BACKEND_SERVICE}"
echo "   Frontend: https://console.cloud.google.com/run/detail/${LOCATION}/${FRONTEND_SERVICE}"
echo ""
echo "🔄 To redeploy:"
echo "   ./deploy.sh"
echo ""
