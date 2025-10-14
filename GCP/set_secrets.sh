#!/bin/bash

# Secret Management Script for GCP
# Interactively sets API keys in GCP Secret Manager

set -e  # Exit on any error

# Load GCP configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
source "${SCRIPT_DIR}/gcp_config.sh"

echo "=================================================="
echo "GCP Secret Manager - API Key Configuration"
echo "=================================================="
echo "Project: ${PROJECT_ID}"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: Not logged in to gcloud. Run: gcloud auth login"
    exit 1
fi

# Set the project
gcloud config set project "${PROJECT_ID}" --quiet

echo "This script will securely store your API keys in GCP Secret Manager."
echo "You can update individual secrets or all at once."
echo ""

# Function to set a secret
set_secret() {
    local secret_name=$1
    local display_name=$2
    local env_var_name=$3

    echo "----------------------------------------"
    echo "${display_name}"
    echo "----------------------------------------"

    # Check if we can read from .env.docker
    local current_value=""
    if [ -f "${PROJECT_ROOT}/.env.docker" ]; then
        current_value=$(grep "^${env_var_name}=" "${PROJECT_ROOT}/.env.docker" 2>/dev/null | cut -d'=' -f2- || echo "")
    fi

    if [ -n "${current_value}" ] && [ "${current_value}" != "your-"*"-key" ]; then
        echo "Found value in .env.docker: ${current_value:0:20}..."
        echo -n "Use this value? [Y/n]: "
        read -r use_existing
        if [ "${use_existing}" != "n" ] && [ "${use_existing}" != "N" ]; then
            echo -n "${current_value}" | gcloud secrets versions add "${secret_name}" --data-file=-
            echo "✓ Secret '${secret_name}' updated from .env.docker"
            return
        fi
    fi

    # Prompt for manual entry
    echo -n "Enter ${display_name} (or 'skip' to skip): "
    read -r secret_value

    if [ "${secret_value}" == "skip" ]; then
        echo "⊘ Skipped"
        return
    fi

    if [ -z "${secret_value}" ]; then
        echo "⚠️  Empty value, skipping"
        return
    fi

    # Update the secret
    echo -n "${secret_value}" | gcloud secrets versions add "${secret_name}" --data-file=-
    echo "✓ Secret '${secret_name}' updated"
}

# Set each secret
set_secret "qdrant-api-key" "Qdrant API Key" "QDRANT_API_KEY"
set_secret "openai-api-key" "OpenAI API Key" "OPENAI_API_KEY"
set_secret "groq-api-key" "GROQ API Key (optional)" "GROQ_API_KEY"

echo ""
echo "=================================================="
echo "✅ Secrets Configuration Complete"
echo "=================================================="
echo ""
echo "Note: QDRANT_API_URL should be set as an environment variable"
echo "during deployment (it's non-sensitive and stored in .env.docker)"
echo ""
echo "To verify secrets:"
echo "  gcloud secrets list"
echo ""
echo "To deploy with these secrets:"
echo "  ./deploy.sh"
echo ""
