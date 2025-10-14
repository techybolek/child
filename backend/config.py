"""
Backend API Configuration
"""
import os
from typing import List

# CORS settings
# Allow frontend URL from environment variable or use defaults
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",  # Next.js development
    "http://127.0.0.1:3000",
    "https://tx-childcare-frontend-usozgowdxq-uc.a.run.app",  # Production frontend
]

# Add custom frontend URL if provided
if FRONTEND_URL and FRONTEND_URL not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_URL)

# Regex pattern to allow all Cloud Run domains
CORS_ORIGIN_REGEX = r"https://.*\.run\.app"

# API settings
API_TITLE = "Texas Childcare Chatbot API"
API_DESCRIPTION = "REST API for Texas childcare assistance chatbot with RAG pipeline"
API_VERSION = "1.0.0"

# Server settings
HOST = "0.0.0.0"
PORT = 8000
RELOAD = True  # Set to False in production
