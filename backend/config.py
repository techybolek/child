"""
Backend API Configuration
"""
import os
from typing import List

# CORS settings
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",  # Next.js development
    "http://127.0.0.1:3000",
    # Add production frontend URL here when deployed
    # "https://yourdomain.com",
]

# API settings
API_TITLE = "Texas Childcare Chatbot API"
API_DESCRIPTION = "REST API for Texas childcare assistance chatbot with RAG pipeline"
API_VERSION = "1.0.0"

# Server settings
HOST = "0.0.0.0"
PORT = 8000
RELOAD = True  # Set to False in production
