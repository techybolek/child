"""
API route definitions for Texas Childcare Chatbot
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from typing import Dict, Any

from .models import ChatRequest, ChatResponse, HealthResponse, Source, ActionItem
from services.chatbot_service import ChatbotService


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint

    Returns:
        Health status including chatbot initialization state
    """
    try:
        service = ChatbotService.get_instance()
        return {
            "status": "ok",
            "chatbot_initialized": service.is_initialized(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "error",
            "chatbot_initialized": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Chat endpoint - ask the chatbot a question

    Args:
        request: ChatRequest with question and optional session_id

    Returns:
        ChatResponse with answer, sources, processing time, session ID, and timestamp

    Raises:
        HTTPException: If chatbot fails to generate response
    """
    try:
        # Get chatbot service instance
        service = ChatbotService.get_instance()

        # Get response from chatbot
        result = service.ask(request.question)

        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Convert sources to Source models
        sources = [
            Source(
                doc=source['doc'],
                page=source['page'],
                url=source['url']
            )
            for source in result['sources']
        ]

        # Convert action_items to ActionItem models
        action_items = [
            ActionItem(
                type=item['type'],
                url=item['url'],
                label=item['label'],
                description=item.get('description')
            )
            for item in result.get('action_items', [])
        ]

        # Return formatted response
        return {
            "answer": result['answer'],
            "sources": sources,
            "response_type": result.get('response_type', 'information'),
            "action_items": action_items,
            "processing_time": result['processing_time'],
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        # Log the error (in production, use proper logging)
        print(f"Error in chat endpoint: {str(e)}")

        # Return HTTP 500 with error details
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to generate response. Please try again.",
                "error_type": type(e).__name__
            }
        )
