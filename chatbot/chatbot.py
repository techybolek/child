from .retriever import QdrantRetriever
from .reranker import LLMJudgeReranker
from .generator import ResponseGenerator
from . import config


class TexasChildcareChatbot:
    def __init__(self):
        self.retriever = QdrantRetriever()
        self.reranker = LLMJudgeReranker(config.OPENAI_API_KEY)
        self.generator = ResponseGenerator(config.OPENAI_API_KEY)

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
