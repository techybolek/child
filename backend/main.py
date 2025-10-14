"""
Texas Childcare Chatbot - FastAPI Backend

A REST API server that wraps the existing RAG-based chatbot with a web-accessible interface.
Provides endpoints for asking questions and checking health status.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from api.routes import router
from api.middleware import error_handler_middleware, validation_exception_handler
from services.chatbot_service import ChatbotService
import config

# Load environment variables from .env file if it exists
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events.
    Initializes the chatbot on startup.
    """
    # Startup: Initialize chatbot singleton
    print("=" * 60)
    print("Texas Childcare Chatbot API - Starting up...")
    print("=" * 60)

    try:
        ChatbotService.get_instance()
        print("✓ Chatbot initialized successfully")
    except Exception as e:
        print(f"⚠ Warning: Failed to initialize chatbot: {str(e)}")
        print("The API will start, but chatbot queries may fail.")

    print("=" * 60)
    print(f"API ready at: http://localhost:{config.PORT}")
    print(f"Swagger docs: http://localhost:{config.PORT}/docs")
    print(f"ReDoc: http://localhost:{config.PORT}/redoc")
    print("=" * 60)

    yield

    # Shutdown
    print("Shutting down...")


# Initialize FastAPI application
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Add custom middleware
app.middleware("http")(error_handler_middleware)

# Add custom exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include API routes with /api prefix
app.include_router(router, prefix="/api", tags=["API"])


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - provides API information and links to documentation
    """
    return {
        "message": "Texas Childcare Chatbot API",
        "version": config.API_VERSION,
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "health": "/api/health",
            "chat": "/api/chat"
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD
    )
