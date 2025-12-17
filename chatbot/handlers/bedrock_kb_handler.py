"""Bedrock Knowledge Base handler using AWS Bedrock retrieve_and_generate API"""

import asyncio
import re
import uuid
import boto3

from .base import BaseHandler
from .. import config
from ..prompts import BEDROCK_AGENT_PROMPT


# Simple model resolver (only Amazon Nova models needed)
BEDROCK_MODELS = {
    'nova-micro': 'amazon.nova-micro-v1:0',
    'nova-lite': 'amazon.nova-lite-v1:0',
    'nova-pro': 'amazon.nova-pro-v1:0',
}


class BedrockKBHandler(BaseHandler):
    """Handles queries using Amazon Bedrock Knowledge Base with Nova models"""

    def __init__(self, model: str | None = None):
        """Initialize Bedrock KB handler

        Args:
            model: Optional model override (defaults to config.BEDROCK_AGENT_MODEL)
        """
        if not config.BEDROCK_KB_ID:
            raise ValueError("BEDROCK_KB_ID environment variable is required")

        # Use provided model or fall back to config
        self.model_short = model or config.BEDROCK_AGENT_MODEL

        # Resolve model to ARN
        model_id = BEDROCK_MODELS.get(self.model_short)
        if not model_id:
            available = list(BEDROCK_MODELS.keys())
            raise ValueError(f"Unknown model '{self.model_short}'. Available: {available}")

        self.model_id = model_id
        self.model_arn = f"arn:aws:bedrock:{config.AWS_REGION}::foundation-model/{model_id}"

        # Initialize Bedrock Agent Runtime client
        self.client = boto3.client(
            'bedrock-agent-runtime',
            region_name=config.AWS_REGION
        )

        # Session storage for conversation continuity
        self._sessions: dict[str, dict] = {}

    def _extract_citations(self, citations: list) -> list:
        """Extract sources from Bedrock API citations array

        Args:
            citations: Raw citations array from Bedrock retrieve_and_generate response

        Returns:
            List of source dicts with keys: doc, pages, url
        """
        sources = []
        seen_docs = set()  # Deduplicate sources

        for citation in citations:
            for ref in citation.get('retrievedReferences', []):
                location = ref.get('location', {})
                s3_loc = location.get('s3Location', {})
                uri = s3_loc.get('uri', '')

                # Extract filename from S3 URI
                doc_name = uri.split('/')[-1] if uri else ''

                # Skip empty or duplicate docs
                if not doc_name or doc_name in seen_docs:
                    continue

                seen_docs.add(doc_name)
                sources.append({
                    'doc': doc_name,
                    'pages': [],  # Bedrock KB doesn't preserve page numbers
                    'url': ''
                })

        return sources

    def _parse_response(self, output_text: str) -> str:
        """Parse LLM output to extract answer text only

        Args:
            output_text: Raw output from Bedrock LLM

        Returns:
            Answer text (stripped of ANSWER:/SOURCES: formatting if present)
        """
        # Try to extract ANSWER: section if present
        answer_match = re.search(r'ANSWER:\s*\n(.*?)(?=\nSOURCES:|$)', output_text, re.DOTALL)

        if answer_match:
            return answer_match.group(1).strip()

        # No ANSWER: section found - return full text
        return output_text.strip()

    def _query_bedrock(self, query: str, session_id: str | None = None) -> dict:
        """Query Bedrock KB with optional session for conversation continuity

        Args:
            query: User's question
            session_id: Optional session ID for conversation continuity

        Returns:
            dict with output_text, session_id, turn_count, citations
        """
        # Generate session_id if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Build request configuration
        request_config = {
            'input': {'text': query},
            'retrieveAndGenerateConfiguration': {
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': config.BEDROCK_KB_ID,
                    'modelArn': self.model_arn,
                    'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\n$output_format_instructions$\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
                        }
                    }
                }
            }
        }

        # Add Bedrock session ID if we have one mapped to this client session
        if session_id in self._sessions and 'bedrock_session_id' in self._sessions[session_id]:
            request_config['sessionId'] = self._sessions[session_id]['bedrock_session_id']

        # Call Bedrock API
        response = self.client.retrieve_and_generate(**request_config)

        # Extract Bedrock's session ID (it generates one on first call)
        bedrock_session_id = response.get('sessionId')

        # Initialize or update session tracking
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                'turn_count': 0,
                'bedrock_session_id': bedrock_session_id
            }
        elif bedrock_session_id:
            # Update bedrock session ID if we got a new one
            self._sessions[session_id]['bedrock_session_id'] = bedrock_session_id

        self._sessions[session_id]['turn_count'] += 1

        return {
            'output_text': response.get('output', {}).get('text', ''),
            'session_id': session_id,  # Return client session ID, not Bedrock's
            'turn_count': self._sessions[session_id]['turn_count'],
            'citations': response.get('citations', [])
        }

    async def handle_async(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict:
        """Run Bedrock KB pipeline (async version for FastAPI)

        Args:
            query: User's question
            thread_id: Optional session ID for conversation continuity
            debug: Whether to include debug information

        Returns:
            Response dict with answer, sources, response_type, action_items, thread_id, turn_count
        """
        try:
            # Run Bedrock query in thread pool (boto3 is sync-only)
            result = await asyncio.to_thread(self._query_bedrock, query, thread_id)

            # Parse answer from LLM output
            answer = self._parse_response(result['output_text'])

            # Extract citations from API response (not from LLM text)
            sources = self._extract_citations(result['citations'])

            response = {
                'answer': answer,
                'sources': sources,
                'response_type': 'information',
                'action_items': [],
                'thread_id': result['session_id'],
                'turn_count': result['turn_count']
            }

            if debug:
                response['debug_info'] = {
                    'raw_output': result['output_text'],
                    'model': self.model_short,
                    'model_arn': self.model_arn,
                    'kb_id': config.BEDROCK_KB_ID
                }

            return response

        except Exception as e:
            return {
                'answer': f"I encountered an error processing your question. Please try again or call 1-800-862-5252 for assistance. Error: {str(e)}",
                'sources': [],
                'response_type': 'error',
                'action_items': []
            }

    def handle(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict:
        """Run Bedrock KB pipeline (sync version - for CLI/evaluation use)

        Args:
            query: User's question
            thread_id: Optional session ID for conversation continuity
            debug: Whether to include debug information

        Returns:
            Response dict with answer, sources, response_type, action_items, thread_id, turn_count
        """
        try:
            # Run Bedrock query directly
            result = self._query_bedrock(query, thread_id)

            # Parse answer from LLM output
            answer = self._parse_response(result['output_text'])

            # Extract citations from API response (not from LLM text)
            sources = self._extract_citations(result['citations'])

            response = {
                'answer': answer,
                'sources': sources,
                'response_type': 'information',
                'action_items': [],
                'thread_id': result['session_id'],
                'turn_count': result['turn_count']
            }

            if debug:
                response['debug_info'] = {
                    'raw_output': result['output_text'],
                    'model': self.model_short,
                    'model_arn': self.model_arn,
                    'kb_id': config.BEDROCK_KB_ID
                }

            return response

        except Exception as e:
            return {
                'answer': f"I encountered an error processing your question. Please try again or call 1-800-862-5252 for assistance. Error: {str(e)}",
                'sources': [],
                'response_type': 'error',
                'action_items': []
            }

    # --- Conversation management helpers ---

    def new_conversation(self) -> str:
        """Start a new conversation and return its session ID"""
        return str(uuid.uuid4())

    def get_history(self, thread_id: str) -> list[dict]:
        """Get conversation history in simplified format

        Args:
            thread_id: Session ID to retrieve history for

        Returns:
            List of {role, content} dicts (empty for Bedrock - managed server-side)
        """
        # Bedrock manages conversation server-side
        # Return empty history as we don't have access to it
        return []

    def clear_conversation(self, thread_id: str) -> None:
        """Clear conversation history for a session"""
        self._sessions.pop(thread_id, None)
