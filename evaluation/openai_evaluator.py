import asyncio
import re
import time
import sys
from pathlib import Path

# Add OAI_EXPERIMENT to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'OAI_EXPERIMENT'))
from agent1 import run_workflow, WorkflowInput


class OpenAIAgentEvaluator:
    """Adapter to make OpenAI agent compatible with evaluation system"""

    def _parse_response(self, output_text: str) -> tuple[str, list]:
        """Parse structured response into answer and sources"""
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
                            'page': 0,  # OpenAI doesn't provide page numbers
                            'url': ''
                        })

        return answer, sources

    def query(self, question: str, debug: bool = False) -> dict:
        """Query OpenAI agent and return response in expected format"""
        start_time = time.time()

        # Call async agent from sync context
        result = asyncio.run(run_workflow(WorkflowInput(input_as_text=question)))

        response_time = time.time() - start_time

        # Parse structured response
        answer, sources = self._parse_response(result['output_text'])

        return {
            'answer': answer,
            'sources': sources,
            'response_type': 'information',
            'response_time': response_time
        }
