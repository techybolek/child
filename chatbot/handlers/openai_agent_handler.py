"""OpenAI Agent handler using OpenAI Agents SDK with FileSearchTool"""

import asyncio
import re

from agents import Agent, FileSearchTool, ModelSettings, Runner, RunConfig, TResponseInputItem
from openai.types.shared.reasoning import Reasoning

from .base import BaseHandler
from .. import config


class OpenAIAgentHandler(BaseHandler):
    """Handles queries using OpenAI Agents SDK with FileSearchTool for RAG"""

    def __init__(self):
        """Initialize FileSearchTool and Agent"""
        if not config.OPENAI_VECTOR_STORE_ID:
            raise ValueError("OPENAI_VECTOR_STORE_ID environment variable is required")

        self.file_search = FileSearchTool(
            vector_store_ids=[config.OPENAI_VECTOR_STORE_ID]
        )

        self.agent = Agent(
            name="Tx Childcare RAG",
            instructions=self._get_instructions,
            model=config.OPENAI_AGENT_MODEL,
            tools=[self.file_search],
            model_settings=ModelSettings(
                store=True,
                reasoning=Reasoning(effort="low", summary="auto")
            )
        )

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
                            'page': 'N/A',  # OpenAI doesn't provide page numbers
                            'url': ''
                        })

        return answer, sources

    async def _run_agent(self, query: str) -> dict:
        """Run the agent asynchronously

        Args:
            query: User's question

        Returns:
            Agent result dictionary with output_text
        """
        # Create context object for dynamic instructions
        class QueryContext:
            def __init__(self, q: str):
                self.query = q

        conversation_history: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": query}]
            }
        ]

        result = await Runner.run(
            self.agent,
            input=conversation_history,
            run_config=RunConfig(trace_metadata={"__trace_source__": "chatbot-handler"}),
            context=QueryContext(query)
        )

        return {"output_text": result.final_output_as(str)}

    def handle(self, query: str, debug: bool = False) -> dict:
        """Run OpenAI Agent pipeline

        Args:
            query: User's question
            debug: Whether to include debug information

        Returns:
            Response dict with answer, sources, response_type, action_items
        """
        try:
            # Run async workflow from sync context
            result = asyncio.run(self._run_agent(query))

            # Parse structured response
            answer, sources = self._parse_response(result['output_text'])

            response = {
                'answer': answer,
                'sources': sources,
                'response_type': 'information',
                'action_items': []
            }

            if debug:
                response['debug_info'] = {
                    'raw_output': result['output_text'],
                    'model': config.OPENAI_AGENT_MODEL,
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
