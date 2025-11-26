"""Kendra handler for queries using Amazon Kendra retrieval + Bedrock Titan generation"""

from langchain_aws import AmazonKendraRetriever, ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .base import BaseHandler
from .. import config


class KendraHandler(BaseHandler):
    """Handles queries using Amazon Kendra for retrieval and Bedrock Titan for generation"""

    def __init__(self):
        """Initialize Kendra retriever and Bedrock LLM"""
        # Initialize Kendra retriever
        self.retriever = AmazonKendraRetriever(
            index_id=config.KENDRA_INDEX_ID,
            region_name=config.KENDRA_REGION,
            top_k=config.KENDRA_TOP_K,
            min_score_confidence=0.0
        )

        # Initialize Bedrock LLM (Titan)
        self.llm = ChatBedrockConverse(
            model_id=config.BEDROCK_MODEL,
            region_name=config.KENDRA_REGION
        )

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template("""Answer the question based on the following context.
If the context doesn't contain enough information to answer the question, say so clearly.
Include specific details and cite your sources using [Doc N] format where N is the document number.

Context:
{context}

Question: {question}

Answer:""")

    def _format_docs(self, docs):
        """Format documents for context with doc numbers"""
        formatted = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', doc.metadata.get('title', 'Unknown'))
            formatted.append(f"[Doc {i}] (Source: {source})\n{doc.page_content}")
        return "\n\n".join(formatted)

    def _map_sources(self, docs) -> list:
        """Map Kendra metadata to standard source format"""
        sources = []
        for doc in docs:
            meta = doc.metadata
            sources.append({
                'doc': meta.get('source', meta.get('title', 'Unknown')),
                'page': meta.get('page', None),
                'url': meta.get('source_uri', meta.get('document_uri', ''))
            })
        return sources

    def handle(self, query: str, debug: bool = False) -> dict:
        """Run Kendra retrieval + Bedrock generation pipeline"""
        debug_data = {}

        # Step 1: Retrieve from Kendra
        docs = self.retriever.invoke(query)

        if not docs:
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
                for d in docs
            ]

        # Step 2: Generate answer using Bedrock
        context = self._format_docs(docs)
        chain = self.prompt | self.llm | StrOutputParser()
        answer = chain.invoke({"context": context, "question": query})

        # Step 3: Extract cited sources
        sources = self._extract_cited_sources(answer, docs)

        response = {
            'answer': answer,
            'sources': sources,
            'response_type': 'information',
            'action_items': []
        }

        if debug:
            response['debug_info'] = debug_data

        return response

    def _extract_cited_sources(self, answer: str, docs: list) -> list:
        """Extract only the sources that were actually cited in the answer"""
        import re

        # Find all [Doc N] citations in the answer
        cited_doc_nums = set(re.findall(r'\[Doc\s*(\d+)\]', answer))

        # Map citation numbers to doc metadata
        cited_sources = []
        for doc_num in sorted(cited_doc_nums, key=int):
            idx = int(doc_num) - 1  # Convert to 0-based index
            if 0 <= idx < len(docs):
                meta = docs[idx].metadata
                cited_sources.append({
                    'doc': meta.get('source', meta.get('title', 'Unknown')),
                    'page': meta.get('page', None),
                    'url': meta.get('source_uri', meta.get('document_uri', ''))
                })

        # If no citations found, return all sources
        if not cited_sources:
            return self._map_sources(docs)

        return cited_sources
