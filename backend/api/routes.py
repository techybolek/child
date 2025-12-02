"""
API route definitions for Texas Childcare Chatbot
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from typing import Dict, Any, List
import os
from groq import Groq

from .models import ChatRequest, ChatResponse, HealthResponse, Source, ActionItem, ModelsResponse, Model, DefaultModels
from services.chatbot_service import ChatbotService

router = APIRouter()

# Cache for conversational chatbot instances, keyed by session_id
# Each session gets its own chatbot instance to preserve conversation memory
_conversational_chatbots: Dict[str, Any] = {}


def _get_chatbot_config():
    """Lazy import of chatbot config to avoid sys.path pollution at module level."""
    import sys
    from pathlib import Path
    parent_dir = Path(__file__).resolve().parent.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from chatbot import config as chatbot_config
    return chatbot_config


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
async def get_available_models(provider: str = 'groq') -> Dict[str, Any]:
    """
    Get available models for the specified provider

    Args:
        provider: 'groq' or 'openai' (default: 'groq')

    Returns:
        List of available models grouped by use case
    """
    try:
        if provider == 'openai':
            # Return static list of OpenAI models
            # New 5-series models recently released by OpenAI are included
            openai_models = [
                Model(id='gpt-4o-mini', name='gpt-4o-mini'),
                Model(id='gpt-5-mini', name='gpt-5-mini'),
                Model(id='gpt-5-nano', name='gpt-5-nano'),
                Model(id='gpt-5', name='gpt-5'),
            ]

            # OpenAI-specific defaults
            defaults = DefaultModels(
                generator='gpt-4o-mini',
                reranker='gpt-4o-mini',
                classifier='gpt-4o-mini'
            )

            return {
                "provider": "openai",
                "generators": openai_models,
                "rerankers": openai_models,
                "classifiers": openai_models,
                "defaults": defaults
            }

        else:  # provider == 'groq'
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
                Model(id=model.id, name=model.id)
                for model in models_response.data
                if 'whisper' not in model.id.lower()
            ]

            # Sort models alphabetically
            text_models.sort(key=lambda m: m.id)

            # Groq-specific defaults from config
            chatbot_config = _get_chatbot_config()
            defaults = DefaultModels(
                generator=chatbot_config.LLM_MODEL,
                reranker=chatbot_config.RERANKER_MODEL,
                classifier=chatbot_config.INTENT_CLASSIFIER_MODEL
            )

            # For GROQ, all text models can be used for all purposes
            return {
                "provider": "groq",
                "generators": text_models,
                "rerankers": text_models,
                "classifiers": text_models,
                "defaults": defaults
            }

    except Exception as e:
        print(f"Error fetching models: {str(e)}")
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

        # Log the incoming query
        print(f"[Chat] Query: {request.question}")

        # Generate session ID if not provided (needed for conversational mode)
        session_id = request.session_id or str(uuid.uuid4())

        # Validate retrieval_mode if provided
        if request.retrieval_mode and request.retrieval_mode not in ('dense', 'hybrid', 'kendra'):
            raise HTTPException(
                status_code=400,
                detail="Invalid retrieval_mode. Must be: dense, hybrid, kendra"
            )

        # Determine if we need a custom chatbot instance
        # Custom instance needed for: model overrides, provider overrides, retrieval mode, or conversational mode
        needs_custom_instance = (
            request.llm_model or
            request.reranker_model or
            request.intent_model or
            request.provider or
            request.retrieval_mode or
            request.conversational_mode
        )

        if needs_custom_instance:
            start_time = time.time()

            if request.conversational_mode:
                # For conversational mode, reuse cached chatbot to preserve memory
                if session_id in _conversational_chatbots:
                    chatbot = _conversational_chatbots[session_id]
                    print(f"[Chat] Reusing cached chatbot for session: {session_id}")
                else:
                    # Create new chatbot and cache it
                    chatbot = TexasChildcareChatbot(
                        llm_model=request.llm_model,
                        reranker_model=request.reranker_model,
                        intent_model=request.intent_model,
                        provider=request.provider,
                        retrieval_mode=request.retrieval_mode,
                        conversational_mode=True
                    )
                    _conversational_chatbots[session_id] = chatbot
                    print(f"[Chat] Created new chatbot for session: {session_id}")

                result = chatbot.ask(request.question, thread_id=session_id)
            else:
                # Non-conversational custom instance (model/retrieval overrides only)
                chatbot = TexasChildcareChatbot(
                    llm_model=request.llm_model,
                    reranker_model=request.reranker_model,
                    intent_model=request.intent_model,
                    provider=request.provider,
                    retrieval_mode=request.retrieval_mode,
                    conversational_mode=False
                )
                result = chatbot.ask(request.question)

            processing_time = time.time() - start_time
            result['processing_time'] = round(processing_time, 2)
        else:
            # Use singleton service (stateless mode only)
            service = ChatbotService.get_instance()
            result = service.ask(request.question)

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

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, etc.) as-is
        raise
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
