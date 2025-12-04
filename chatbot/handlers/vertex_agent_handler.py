"""Vertex AI Agent handler using Gemini with RAG retrieval tool"""

import asyncio
import re
import uuid

import vertexai
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool, ChatSession

from .base import BaseHandler
from .. import config


SYSTEM_INSTRUCTION = """You are a Texas childcare assistance expert. Answer questions using ONLY information retrieved from the RAG corpus.

RULES:
- Use the retrieval tool to find relevant passages before answering
- Provide clear, accurate, concise responses (1-3 sentences)
- If information is not found in the corpus, say "I don't have information about this in my knowledge base" - do not speculate
- If a question is ambiguous, ask for clarification

DOMAIN CONTEXT:
You are answering questions about:
- Texas Workforce Commission (TWC) childcare programs
- Child Care Services (CCS) eligibility and enrollment
- Texas Rising Star quality rating system
- Parent Share of Cost calculations
- Provider requirements and reimbursement rates

Output format:
Your response MUST follow this exact structure:

ANSWER:
[Your 1-4 sentence response here]

SOURCES:
- [filename1.pdf]
- [filename2.pdf]

Rules for sources:
- List each source document filename on its own line, prefixed with "- "
- Only include files that directly contributed to your answer
- If no sources were used, write "- None"
"""


class VertexAgentHandler(BaseHandler):
    """Handles queries using Vertex AI Gemini with RAG retrieval tool"""

    _initialized = False

    def __init__(self, model: str | None = None):
        """Initialize Vertex AI RAG tool and GenerativeModel

        Args:
            model: Optional model override (defaults to config.VERTEX_AGENT_MODEL)
        """
        # Initialize Vertex AI SDK (only once)
        if not VertexAgentHandler._initialized:
            vertexai.init(
                project=config.VERTEX_PROJECT_ID,
                location=config.VERTEX_LOCATION
            )
            VertexAgentHandler._initialized = True

        self.model_name = model or config.VERTEX_AGENT_MODEL

        # Create RAG retrieval tool
        self.rag_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[rag.RagResource(rag_corpus=config.VERTEX_CORPUS_NAME)],
                    similarity_top_k=config.VERTEX_SIMILARITY_TOP_K,
                ),
            )
        )

        # Create model with tool and system instruction
        self.model = GenerativeModel(
            model_name=self.model_name,
            tools=[self.rag_tool],
            system_instruction=SYSTEM_INSTRUCTION,
        )

        # Thread-scoped chat sessions for conversation continuity
        self._sessions: dict[str, ChatSession] = {}

    def _parse_response(self, output_text: str) -> tuple[str, list]:
        """Parse structured response into answer and sources

        Args:
            output_text: Raw output from model with ANSWER/SOURCES sections

        Returns:
            Tuple of (answer_text, sources_list)
        """
        answer = output_text
        sources = []

        # Try to parse ANSWER: and SOURCES: sections
        answer_match = re.search(r'ANSWER:\s*\n(.*?)(?=\nSOURCES:|$)', output_text, re.DOTALL)
        sources_match = re.search(r'SOURCES:\s*\n(.*?)$', output_text, re.DOTALL)

        if answer_match:
            answer = answer_match.group(1).strip()

        if sources_match:
            sources_text = sources_match.group(1).strip()
            # Parse each line starting with "- "
            for line in sources_text.split('\n'):
                line = line.strip()
                if line.startswith('- ') and line != '- None':
                    doc_name = line[2:].strip()
                    # Remove brackets if present
                    doc_name = doc_name.strip('[]')
                    if doc_name:
                        sources.append({
                            'doc': doc_name,
                            'page': 'N/A',  # Vertex RAG doesn't provide page numbers
                            'url': ''
                        })

        return answer, sources

    def _get_or_create_session(self, thread_id: str) -> ChatSession:
        """Get existing chat session or create new one for thread

        Args:
            thread_id: Unique identifier for the conversation thread

        Returns:
            ChatSession for the thread
        """
        if thread_id not in self._sessions:
            self._sessions[thread_id] = self.model.start_chat()
        return self._sessions[thread_id]

    def _query_model(self, query: str, thread_id: str | None = None) -> dict:
        """Query the model (sync)

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity

        Returns:
            Dict with output_text, thread_id, turn_count
        """
        # Generate thread_id if not provided
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        # Get or create chat session for this thread
        chat = self._get_or_create_session(thread_id)

        # Send message and get response
        response = chat.send_message(query)
        output_text = response.text

        # Count turns (messages in history)
        turn_count = len(chat.history) // 2  # Each turn has user + model message

        return {
            "output_text": output_text,
            "thread_id": thread_id,
            "turn_count": turn_count
        }

    async def _query_model_async(self, query: str, thread_id: str | None = None) -> dict:
        """Query the model (async)

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity

        Returns:
            Dict with output_text, thread_id, turn_count
        """
        # Generate thread_id if not provided
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        # Get or create chat session for this thread
        chat = self._get_or_create_session(thread_id)

        # Send message asynchronously
        response = await chat.send_message_async(query)
        output_text = response.text

        # Count turns (messages in history)
        turn_count = len(chat.history) // 2

        return {
            "output_text": output_text,
            "thread_id": thread_id,
            "turn_count": turn_count
        }

    def handle(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict:
        """Run Vertex AI Agent pipeline (sync version - for CLI/evaluation use)

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity
            debug: Whether to include debug information

        Returns:
            Response dict with answer, sources, response_type, action_items, thread_id, turn_count
        """
        try:
            result = self._query_model(query, thread_id)

            # Parse structured response
            answer, sources = self._parse_response(result['output_text'])

            response = {
                'answer': answer,
                'sources': sources,
                'response_type': 'information',
                'action_items': [],
                'thread_id': result['thread_id'],
                'turn_count': result['turn_count']
            }

            if debug:
                response['debug_info'] = {
                    'raw_output': result['output_text'],
                    'model': self.model_name,
                    'corpus': config.VERTEX_CORPUS_NAME
                }

            return response

        except Exception as e:
            return {
                'answer': f"I encountered an error processing your question. Please try again or call 1-800-862-5252 for assistance. Error: {str(e)}",
                'sources': [],
                'response_type': 'error',
                'action_items': []
            }

    async def handle_async(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict:
        """Run Vertex AI Agent pipeline (async version for FastAPI)

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity
            debug: Whether to include debug information

        Returns:
            Response dict with answer, sources, response_type, action_items, thread_id, turn_count
        """
        try:
            result = await self._query_model_async(query, thread_id)

            # Parse structured response
            answer, sources = self._parse_response(result['output_text'])

            response = {
                'answer': answer,
                'sources': sources,
                'response_type': 'information',
                'action_items': [],
                'thread_id': result['thread_id'],
                'turn_count': result['turn_count']
            }

            if debug:
                response['debug_info'] = {
                    'raw_output': result['output_text'],
                    'model': self.model_name,
                    'corpus': config.VERTEX_CORPUS_NAME
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
        """Start a new conversation and return its thread_id"""
        return str(uuid.uuid4())

    def get_history(self, thread_id: str) -> list[dict]:
        """Get conversation history in simplified format

        Args:
            thread_id: Thread ID to retrieve history for

        Returns:
            List of {role, content} dicts
        """
        if thread_id not in self._sessions:
            return []

        chat = self._sessions[thread_id]
        result = []
        for content in chat.history:
            role = content.role
            # Extract text from parts
            text = ""
            if content.parts:
                text = content.parts[0].text if hasattr(content.parts[0], 'text') else str(content.parts[0])
            result.append({"role": role, "content": text})
        return result

    def clear_conversation(self, thread_id: str) -> None:
        """Clear conversation history for a thread"""
        self._sessions.pop(thread_id, None)
