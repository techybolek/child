"""OpenAI Agent handler using OpenAI Agents SDK with FileSearchTool"""

import asyncio
import re
import uuid

from agents import Agent, FileSearchTool, ModelSettings, Runner, RunConfig, TResponseInputItem
from openai.types.shared.reasoning import Reasoning

from .base import BaseHandler
from .. import config


class OpenAIAgentHandler(BaseHandler):
    """Handles queries using OpenAI Agents SDK with FileSearchTool for RAG"""

    def __init__(self, model: str | None = None):
        """Initialize FileSearchTool and Agent

        Args:
            model: Optional model override (defaults to config.OPENAI_AGENT_MODEL)
        """
        if not config.OPENAI_VECTOR_STORE_ID:
            raise ValueError("OPENAI_VECTOR_STORE_ID environment variable is required")

        # Use provided model or fall back to config
        self.model = model or config.OPENAI_AGENT_MODEL

        self.file_search = FileSearchTool(
            vector_store_ids=[config.OPENAI_VECTOR_STORE_ID]
        )

        self.agent = Agent(
            name="Tx Childcare RAG",
            instructions=self._get_instructions,
            model=self.model,
            tools=[self.file_search],
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(effort="low", summary="auto")
            )
        )

        # Thread-scoped conversation storage
        self._conversations: dict[str, list[TResponseInputItem]] = {}

    def _get_instructions(self, run_context, _agent) -> str:
        """Dynamic instructions with query injected"""
        query = run_context.context.query
        return f"""Concisely answer user questions about Texas childcare assistance programs using information retrieved from the vector store. Focus on providing clear, accurate, and relevant information tailored to the user's query. If information is not found, state this rather than speculating. Ensure that all reasoning (i.e., summarizing or interpreting relevant information from the vector store) is performed before you provide your final answer.

- Use the vector store to retrieve relevant facts or passages.
- Condense the information into a brief, direct response that fully addresses the question.
- If a question is ambiguous, politely ask for clarification.
- If pertinent information is not available, state "No information found in the vector store for this question."

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

User query: {query}"""

    def _parse_response(self, output_text: str) -> tuple[str, list]:
        """Parse structured response into answer and sources

        Args:
            output_text: Raw output from agent with ANSWER/SOURCES sections

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
                            'pages': [],  # OpenAI doesn't provide page numbers
                            'url': ''
                        })

        return answer, sources

    async def _run_agent(self, query: str, thread_id: str | None = None) -> dict:
        """Run the agent asynchronously

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity

        Returns:
            Agent result dictionary with output_text, thread_id, turn_count
        """
        # Create context object for dynamic instructions
        class QueryContext:
            def __init__(self, q: str):
                self.query = q

        # Generate thread_id if not provided
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        # Load existing conversation history or start fresh
        conversation_history = self._conversations.get(thread_id, [])

        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": [{"type": "input_text", "text": query}]
        })

        result = await Runner.run(
            self.agent,
            input=conversation_history,
            run_config=RunConfig(trace_metadata={"__trace_source__": "chatbot-handler"}),
            context=QueryContext(query)
        )

        # Accumulate agent response into history (KEY for multi-turn)
        conversation_history.extend([item.to_input_item() for item in result.new_items])

        # Save updated history
        self._conversations[thread_id] = conversation_history

        # Count user turns
        turn_count = sum(1 for item in conversation_history if item.get("role") == "user")

        return {
            "output_text": result.final_output_as(str),
            "thread_id": thread_id,
            "turn_count": turn_count
        }

    async def handle_async(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict:
        """Run OpenAI Agent pipeline (async version for FastAPI)

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity
            debug: Whether to include debug information

        Returns:
            Response dict with answer, sources, response_type, action_items, thread_id, turn_count
        """
        try:
            # Run async workflow directly
            result = await self._run_agent(query, thread_id)

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
                    'model': self.model,
                    'vector_store_id': config.OPENAI_VECTOR_STORE_ID
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
        """Run OpenAI Agent pipeline (sync version - for CLI/evaluation use)

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity
            debug: Whether to include debug information

        Returns:
            Response dict with answer, sources, response_type, action_items, thread_id, turn_count
        """
        try:
            # Run async workflow from sync context
            result = asyncio.run(self._run_agent(query, thread_id))

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
                    'model': self.model,
                    'vector_store_id': config.OPENAI_VECTOR_STORE_ID
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
        history = self._conversations.get(thread_id, [])
        result = []
        for item in history:
            role = item.get("role", "unknown")
            content_list = item.get("content", [])
            # Extract text content, handling various formats
            if isinstance(content_list, list) and content_list:
                first_content = content_list[0]
                if isinstance(first_content, dict):
                    text = first_content.get("text", "")
                else:
                    text = str(first_content)
            elif isinstance(content_list, str):
                text = content_list
            else:
                text = ""
            result.append({"role": role, "content": text})
        return result

    def clear_conversation(self, thread_id: str) -> None:
        """Clear conversation history for a thread"""
        self._conversations.pop(thread_id, None)
