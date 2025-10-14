#!/bin/bash

# GCP Setup Script for Texas Childcare Chatbot
# This script performs one-time setup for GCP deployment
# Run this once before the first deployment

set -e  # Exit on any error

# Load GCP configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/gcp_config.sh"

echo "=================================================="
echo "GCP Setup for Texas Childcare Chatbot"
echo "=================================================="
echo "Project ID: ${PROJECT_ID}"
echo "Location: ${LOCATION}"
echo "Repository: ${REPOSITORY}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✓ gcloud CLI found"

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not logged in to gcloud"
    echo "Run: gcloud auth login"
    exit 1
fi

echo "✓ gcloud authenticated"

# Set the project
echo ""
echo "Setting active project..."
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
echo ""
echo "Enabling required GCP APIs..."
echo "(This may take a few minutes)"

gcloud services enable \
    cloudrun.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com

echo "✓ APIs enabled"

# Create Artifact Registry repository
echo ""
echo "Creating Artifact Registry repository..."

if gcloud artifacts repositories describe "${REPOSITORY}" \
    --location="${LOCATION}" &> /dev/null; then
    echo "✓ Repository '${REPOSITORY}' already exists"
else
    gcloud artifacts repositories create "${REPOSITORY}" \
        --repository-format=docker \
        --location="${LOCATION}" \
        --description="Docker images for Texas Childcare Chatbot"
    echo "✓ Repository '${REPOSITORY}' created"
fi

# Configure Docker authentication
echo ""
echo "Configuring Docker authentication..."
gcloud auth configure-docker "${LOCATION}-docker.pkg.dev" --quiet
echo "✓ Docker authentication configured"

# Grant Cloud Run Admin permissions to default service account (needed for deployment)
echo ""
echo "Configuring service account permissions..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/run.admin" \
    --quiet > /dev/null

echo "✓ Service account permissions configured"

# Create secrets placeholders (empty for now, to be filled by set_secrets.sh)
echo ""
echo "Creating secret placeholders in Secret Manager..."

create_secret_if_not_exists() {
    local secret_name=$1
    if gcloud secrets describe "${secret_name}" &> /dev/null; then
        echo "  ✓ Secret '${secret_name}' already exists"
    else
        echo -n "placeholder" | gcloud secrets create "${secret_name}" \
            --data-file=- \
            --replication-policy="automatic"
        echo "  ✓ Secret '${secret_name}' created (placeholder)"
    fi
}

create_secret_if_not_exists "qdrant-api-key"
create_secret_if_not_exists "openai-api-key"
create_secret_if_not_exists "groq-api-key"

echo ""
echo "=================================================="
echo "✅ GCP Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Set your API keys:"
echo "   ./set_secrets.sh"
echo ""
echo "2. Deploy the application:"
echo "   ./deploy.sh"
echo ""
