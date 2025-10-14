"""
API route definitions for Texas Childcare Chatbot
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from typing import Dict, Any, List
import os
from groq import Groq

from .models import ChatRequest, ChatResponse, HealthResponse, Source, ActionItem, ModelsResponse, GroqModel, DefaultModels
from services.chatbot_service import ChatbotService

# Import chatbot config to get default models
import sys
from pathlib import Path
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(parent_dir))
from chatbot import config as chatbot_config


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


@router.get("/models", response_model=ModelsResponse)
async def get_available_models() -> Dict[str, Any]:
    """
    Get available GROQ models

    Returns:
        List of available models grouped by use case
    """
    try:
        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY not configured"
            )

        client = Groq(api_key=groq_api_key)
        models_response = client.models.list()

        # Filter text generation models (exclude whisper/audio models)
        text_models = [
            GroqModel(id=model.id, name=model.id)
            for model in models_response.data
            if 'whisper' not in model.id.lower()
        ]

        # Sort models alphabetically
        text_models.sort(key=lambda m: m.id)

        # Get default models from config
        defaults = DefaultModels(
            generator=chatbot_config.LLM_MODEL,
            reranker=chatbot_config.RERANKER_MODEL,
            classifier=chatbot_config.INTENT_CLASSIFIER_MODEL
        )

        # For GROQ, all text models can be used for all purposes
        return {
            "generators": text_models,
            "rerankers": text_models,
            "classifiers": text_models,
            "defaults": defaults
        }

    except Exception as e:
        print(f"Error fetching GROQ models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch models: {str(e)}"
        )


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
        import sys
        import time
        from pathlib import Path

        # Add parent directory to path to import chatbot module
        parent_dir = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(parent_dir))
        from chatbot.chatbot import TexasChildcareChatbot

        # If custom models specified, create new chatbot instance
        # Otherwise use singleton
        if request.llm_model or request.reranker_model or request.intent_model:
            start_time = time.time()
            chatbot = TexasChildcareChatbot(
                llm_model=request.llm_model,
                reranker_model=request.reranker_model,
                intent_model=request.intent_model
            )
            result = chatbot.ask(request.question)
            processing_time = time.time() - start_time
            result['processing_time'] = round(processing_time, 2)
        else:
            # Use singleton service
            service = ChatbotService.get_instance()
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
