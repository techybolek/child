"""Bedrock Knowledge Base evaluator for evaluation framework.

Uses Amazon Bedrock Knowledge Bases retrieve_and_generate API
to query a pre-configured Knowledge Base with Titan embeddings.
"""

import os
import time
import boto3

from .bedrock_model_resolver import resolve_model_arn


class BedrockKBEvaluator:
    """Evaluator that uses Amazon Bedrock Knowledge Bases for RAG."""

    def __init__(self):
        """Initialize Bedrock KB evaluator.

        Environment variables:
            BEDROCK_KB_ID: Knowledge Base ID (default: 371M2G58TV)
            BEDROCK_MODEL: Model short name (default: nova-micro)
                Amazon models (no approval needed): nova-micro, nova-lite, nova-pro
                Anthropic models (may need approval): 3-haiku, 3.5-haiku, 4-5
            AWS_REGION: AWS region (default: us-east-1)
        """
        self.kb_id = os.getenv('BEDROCK_KB_ID', '371M2G58TV')
        self.region = os.getenv('AWS_REGION', 'us-east-1')

        # Resolve model - default to Nova Micro (Amazon model, no approval needed)
        model_short = os.getenv('BEDROCK_MODEL', 'nova-micro')
        self.model_id, self.model_arn, self.model_display_name = resolve_model_arn(model_short)

        # Initialize Bedrock Agent Runtime client
        self.client = boto3.client(
            'bedrock-agent-runtime',
            region_name=self.region
        )

    def query(self, question: str, debug: bool = False) -> dict:
        """Query Bedrock Knowledge Base and return response.

        Args:
            question: The question to ask
            debug: Whether to include debug information

        Returns:
            dict with keys: answer, sources, response_type, response_time
        """
        start_time = time.time()

        response = self.client.retrieve_and_generate(
            input={'text': question},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.kb_id,
                    'modelArn': self.model_arn
                }
            }
        )

        response_time = time.time() - start_time

        # Extract answer
        answer = response.get('output', {}).get('text', '')

        # Extract sources from citations
        sources = []
        citations = response.get('citations', [])
        for citation in citations:
            for ref in citation.get('retrievedReferences', []):
                location = ref.get('location', {})
                s3_loc = location.get('s3Location', {})
                uri = s3_loc.get('uri', '')

                # Extract filename from S3 URI
                doc_name = uri.split('/')[-1] if uri else 'unknown'

                # Bedrock KB doesn't preserve page numbers
                sources.append({
                    'doc': doc_name,
                    'page': 'N/A',
                    'text': ref.get('content', {}).get('text', '')[:200]
                })

        result = {
            'answer': answer,
            'sources': sources,
            'response_type': 'rag',
            'response_time': response_time
        }

        if debug:
            result['debug_info'] = {
                'kb_id': self.kb_id,
                'model_id': self.model_id,
                'model_arn': self.model_arn,
                'num_citations': len(citations),
                'num_sources': len(sources)
            }

        return result
