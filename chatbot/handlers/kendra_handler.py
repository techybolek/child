"""Kendra handler for queries using Amazon Kendra retrieval + ResponseGenerator"""

from langchain_aws import AmazonKendraRetriever

from .base import BaseHandler
from ..generator import ResponseGenerator
from .. import config


class KendraHandler(BaseHandler):
    """Handles queries using Amazon Kendra for retrieval and ResponseGenerator for generation"""

    def __init__(self):
        """Initialize Kendra retriever and ResponseGenerator"""
        # Initialize Kendra retriever
        self.retriever = AmazonKendraRetriever(
            index_id=config.KENDRA_INDEX_ID,
            region_name=config.KENDRA_REGION,
            top_k=config.KENDRA_TOP_K,
            min_score_confidence=0.0
        )

        # Initialize ResponseGenerator (replaces Bedrock LLM)
        effective_provider = config.LLM_PROVIDER
        generator_api_key = (
            config.GROQ_API_KEY if effective_provider == 'groq'
            else config.OPENAI_API_KEY
        )
        self.generator = ResponseGenerator(
            api_key=generator_api_key,
            provider=effective_provider,
            model=config.LLM_MODEL
        )

    def _convert_kendra_docs_to_chunks(self, kendra_docs) -> list:
        """Convert AmazonKendraRetriever documents to ResponseGenerator format

        Args:
            kendra_docs: List of LangChain Document objects from Kendra

        Returns:
            List of chunk dictionaries compatible with ResponseGenerator
        """
        chunks = []
        for doc in kendra_docs:
            chunk = {
                # Required fields for generator
                'text': doc.page_content,
                'filename': doc.metadata.get('source') or doc.metadata.get('title', 'Unknown'),
                'page': doc.metadata.get('page', 'N/A'),
                'source_url': doc.metadata.get('source_uri') or doc.metadata.get('document_uri', ''),

                # Optional context fields (Kendra doesn't provide these - use empty strings)
                'master_context': '',
                'document_context': '',
                'chunk_context': '',
            }
            chunks.append(chunk)
        return chunks

    def handle(self, query: str, debug: bool = False) -> dict:
        """Run Kendra retrieval + ResponseGenerator pipeline"""
        debug_data = {}

        # Step 1: Retrieve from Kendra (includes built-in reranking)
        kendra_docs = self.retriever.invoke(query)

        if not kendra_docs:
            return {
                'answer': "I couldn't find information about that. Try calling 1-800-862-5252.",
                'sources': [],
                'response_type': 'information',
                'action_items': []
            }

        # Store retrieved docs for debug
        if debug:
            debug_data['retrieved_chunks'] = [
                {
                    'doc': d.metadata.get('source', d.metadata.get('title', '')),
                    'page': d.metadata.get('page', ''),
                    'score': d.metadata.get('score', 0),
                    'text': d.page_content[:500] + '...' if len(d.page_content) > 500 else d.page_content,
                    'source_url': d.metadata.get('source_uri', ''),
                }
                for d in kendra_docs
            ]

        # Step 2: Convert Kendra docs to generator-compatible chunks
        chunks = self._convert_kendra_docs_to_chunks(kendra_docs)

        # Step 3: Generate answer using ResponseGenerator (not Bedrock)
        result = self.generator.generate(query, chunks)

        # Step 4: Extract cited sources from answer
        cited_sources = self._extract_cited_sources(result['answer'], chunks)

        response = {
            'answer': result['answer'],
            'sources': cited_sources,
            'response_type': 'information',
            'action_items': []
        }

        if debug:
            response['debug_info'] = debug_data

        return response

    def _extract_cited_sources(self, answer: str, chunks: list) -> list:
        """Extract only the sources that were actually cited in the answer

        Args:
            answer: Generated answer text with [Doc N] citations
            chunks: List of chunk dictionaries used for generation

        Returns:
            List of cited source dictionaries
        """
        import re

        # Find all [Doc N] citations in the answer
        cited_doc_nums = set(re.findall(r'\[Doc\s*(\d+):', answer))

        # Map citation numbers to chunk metadata
        cited_sources = []
        for doc_num in sorted(cited_doc_nums, key=int):
            idx = int(doc_num) - 1  # Convert to 0-based index
            if 0 <= idx < len(chunks):
                chunk = chunks[idx]
                cited_sources.append({
                    'doc': chunk['filename'],
                    'page': chunk['page'],
                    'url': chunk['source_url']
                })

        # If no citations found, return all sources
        if not cited_sources:
            return [
                {
                    'doc': chunk['filename'],
                    'page': chunk['page'],
                    'url': chunk['source_url']
                }
                for chunk in chunks
            ]

        return cited_sources
