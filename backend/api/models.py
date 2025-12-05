"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Union


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's question about Texas childcare assistance"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation tracking"
    )
    provider: Optional[str] = Field(
        None,
        description="Optional LLM provider: 'groq' or 'openai'"
    )
    llm_model: Optional[str] = Field(
        None,
        description="Optional model to use for generation"
    )
    reranker_model: Optional[str] = Field(
        None,
        description="Optional model to use for reranking"
    )
    intent_model: Optional[str] = Field(
        None,
        description="Optional model to use for intent classification"
    )
    retrieval_mode: Optional[str] = Field(
        None,
        description="Retrieval mode: 'dense', 'hybrid', or 'kendra'"
    )
    conversational_mode: Optional[bool] = Field(
        False,
        description="Enable conversational memory for multi-turn conversations"
    )
    mode: Optional[Literal['rag_pipeline', 'openai_agent', 'vertex_agent']] = Field(
        None,
        description="Chat mode: 'rag_pipeline' (default), 'openai_agent', or 'vertex_agent'"
    )
    openai_agent_model: Optional[str] = Field(
        None,
        description="Model for OpenAI Agent mode (e.g., 'gpt-4o-mini', 'gpt-4o')"
    )
    vertex_agent_model: Optional[str] = Field(
        None,
        description="Model for Vertex Agent mode (e.g., 'gemini-2.5-flash', 'gemini-2.5-pro')"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What are the income limits for a family of 3 in BCY 2026?",
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "provider": "groq",
                    "llm_model": "openai/gpt-oss-20b"
                }
            ]
        }
    }


class Source(BaseModel):
    """Source citation model"""
    doc: str = Field(..., description="Document filename")
    pages: List[int] = Field(..., description="Page numbers (sorted)")
    url: str = Field(..., description="Source URL")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "doc": "TWC_Income_Guidelines_2026.pdf",
                    "pages": [12, 15],
                    "url": "https://texaschildcaresolutions.org/files/TWC_Income_Guidelines_2026.pdf"
                }
            ]
        }
    }


class ActionItem(BaseModel):
    """Action item model for clickable links/buttons"""
    type: str = Field(..., description="Action type (e.g., 'link', 'button')")
    url: str = Field(..., description="URL to navigate to")
    label: str = Field(..., description="Display label for the action")
    description: Optional[str] = Field(None, description="Optional description")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "link",
                    "url": "https://childcare.hhs.texas.gov/Public/ChildCareSearch",
                    "label": "Search for Childcare Facilities",
                    "description": "Official Texas HHS facility search tool"
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    answer: str = Field(..., description="Generated answer from the chatbot")
    sources: List[Source] = Field(..., description="Source citations used for the answer")
    response_type: str = Field(default='information', description="Response type (information, location_search, etc.)")
    action_items: List[ActionItem] = Field(default=[], description="Optional action items (links, buttons)")
    processing_time: float = Field(..., description="Processing time in seconds")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    timestamp: str = Field(..., description="Response timestamp in ISO 8601 format")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "For BCY 2026, a family of 3 has the following income limits...",
                    "sources": [
                        {
                            "doc": "TWC_Income_Guidelines_2026.pdf",
                            "pages": [12, 15],
                            "url": "https://texaschildcaresolutions.org/files/TWC_Income_Guidelines_2026.pdf"
                        }
                    ],
                    "processing_time": 3.24,
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2025-10-12T15:30:05Z"
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str = Field(..., description="Service status (ok or error)")
    chatbot_initialized: bool = Field(..., description="Whether chatbot is initialized")
    timestamp: str = Field(..., description="Check timestamp in ISO 8601 format")
    error: Optional[str] = Field(None, description="Error message if status is error")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "ok",
                    "chatbot_initialized": True,
                    "timestamp": "2025-10-12T15:30:00Z"
                }
            ]
        }
    }


class Model(BaseModel):
    """LLM model information"""
    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model display name")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "openai/gpt-oss-20b",
                    "name": "openai/gpt-oss-20b"
                }
            ]
        }
    }


class DefaultModels(BaseModel):
    """Default models being used"""
    generator: str = Field(..., description="Default generator model")
    reranker: str = Field(..., description="Default reranker model")
    classifier: str = Field(..., description="Default classifier model")


class ModelsResponse(BaseModel):
    """Response model for available models endpoint"""
    provider: str = Field(..., description="Provider for these models: 'groq' or 'openai'")
    generators: List[Model] = Field(..., description="Models available for text generation")
    rerankers: List[Model] = Field(..., description="Models available for reranking")
    classifiers: List[Model] = Field(..., description="Models available for intent classification")
    defaults: DefaultModels = Field(..., description="Current default models from config")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "provider": "groq",
                    "generators": [{"id": "openai/gpt-oss-20b", "name": "openai/gpt-oss-20b"}],
                    "rerankers": [{"id": "openai/gpt-oss-120b", "name": "openai/gpt-oss-120b"}],
                    "classifiers": [{"id": "openai/gpt-oss-20b", "name": "openai/gpt-oss-20b"}],
                    "defaults": {
                        "generator": "openai/gpt-oss-20b",
                        "reranker": "openai/gpt-oss-120b",
                        "classifier": "openai/gpt-oss-20b"
                    }
                }
            ]
        }
    }
