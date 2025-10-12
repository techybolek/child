from .retriever import QdrantRetriever
from .reranker import LLMJudgeReranker
from .generator import ResponseGenerator
from . import config


class TexasChildcareChatbot:
    def __init__(self):
        self.retriever = QdrantRetriever()

        # Initialize reranker with configured provider
        reranker_api_key = config.GROQ_API_KEY if config.RERANKER_PROVIDER == 'groq' else config.OPENAI_API_KEY
        self.reranker = LLMJudgeReranker(
            api_key=reranker_api_key,
            provider=config.RERANKER_PROVIDER,
            model=config.RERANKER_MODEL
        )
        print(f"Reranker: {config.RERANKER_PROVIDER.upper()} - {config.RERANKER_MODEL}")

        # Initialize generator with configured provider
        generator_api_key = config.GROQ_API_KEY if config.LLM_PROVIDER == 'groq' else config.OPENAI_API_KEY
        self.generator = ResponseGenerator(
            api_key=generator_api_key,
            provider=config.LLM_PROVIDER,
            model=config.LLM_MODEL
        )
        print(f"Generator: {config.LLM_PROVIDER.upper()} - {config.LLM_MODEL}")

    def ask(self, question: str):
        """Ask a question, get an answer"""

        # Step 1: Search Qdrant
        print("Searching...")
        chunks = self.retriever.search(question, top_k=config.RETRIEVAL_TOP_K)

        if not chunks:
            return {
                'answer': "I couldn't find information about that. Try calling 1-800-862-5252.",
                'sources': []
            }

        # Step 2: Rerank
        if self.reranker:
            print("Reranking...")
            chunks = self.reranker.rerank(question, chunks, top_k=config.RERANK_TOP_K)
        else:
            chunks = chunks[:config.RERANK_TOP_K]

        # Step 3: Generate answer
        print("Generating answer...")
        result = self.generator.generate(question, chunks)

        # Step 4: Return response
        return {
            'answer': result['answer'],
            'sources': [
                {'doc': c['filename'], 'page': c['page'], 'url': c['source_url']}
                for c in chunks
            ]
        }
