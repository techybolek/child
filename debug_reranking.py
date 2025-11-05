"""
Debug script to see which chunks the reranker is scoring high for Q5.
Shows what rank Chunk 999 gets after reranking.
"""

import os
import json
from openai import OpenAI
from qdrant_client import QdrantClient
from chatbot.retriever import QdrantRetriever
from chatbot.reranker import LLMJudgeReranker

# Configuration
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
COLLECTION_NAME = 'tro-child-3-contextual'

# Question
QUESTION = "What income levels correspond to each State Median Income (SMI) percentage for a family of 5?"

def main():
    print("=" * 80)
    print("DEBUG: RERANKING FOR Q5")
    print("=" * 80)

    # Initialize
    retriever = QdrantRetriever(collection_name=COLLECTION_NAME)
    reranker = LLMJudgeReranker()

    # Retrieve
    print("\n1. Retrieving top chunks...")
    retrieved_chunks = retriever.retrieve(QUESTION, top_k=40)

    # Find Chunk 999
    chunk_999_position = None
    for i, chunk in enumerate(retrieved_chunks):
        # Check if this is from bcy-26-psoc-chart-twc.pdf with the correct data
        if 'bcy-26-psoc-chart-twc.pdf' in chunk.get('filename', ''):
            text = chunk.get('text', '')
            if '$105' in text and '$8,897' in text:
                chunk_999_position = i
                print(f"\n✅ Found complete Family Size 5 chunk at position {i}")
                print(f"   File: {chunk['filename']}")
                print(f"   Retrieval score: {chunk.get('score', 'N/A')}")
                print(f"   Chunk context: {chunk.get('chunk_context', 'N/A')[:200]}...")
                break

    if not chunk_999_position:
        print("\n❌ Complete Family Size 5 chunk NOT found in top 40")
        return

    # Rerank
    print(f"\n2. Reranking top 40 chunks...")
    reranked_chunks = reranker.rerank(QUESTION, retrieved_chunks)

    # Find where Chunk 999 is after reranking
    chunk_999_reranked_position = None
    for i, chunk in enumerate(reranked_chunks):
        if 'bcy-26-psoc-chart-twc.pdf' in chunk.get('filename', ''):
            text = chunk.get('text', '')
            if '$105' in text and '$8,897' in text:
                chunk_999_reranked_position = i
                print(f"\n✅ After reranking, chunk is at position {i}")
                print(f"   Reranking score: {chunk.get('rerank_score', 'N/A')}")
                break

    if not chunk_999_reranked_position:
        print(f"\n❌ Chunk was at position {chunk_999_position} before reranking, but NOT in reranked results")
        print(f"   This means it was cut off by RERANK_TOP_K=10")
        print(f"   Need to increase RERANK_TOP_K")
        return

    # Show top 10 after reranking
    print(f"\n{'=' * 80}")
    print("TOP 10 AFTER RERANKING")
    print(f"{'=' * 80}")

    for i, chunk in enumerate(reranked_chunks[:10]):
        filename = chunk.get('filename', 'unknown')
        rerank_score = chunk.get('rerank_score', 'N/A')
        chunk_context = chunk.get('chunk_context', '')[:100]

        marker = "👉 TARGET" if (i == chunk_999_reranked_position) else ""
        print(f"\nRank {i+1}: Score={rerank_score} {marker}")
        print(f"  File: {filename}")
        print(f"  Context: {chunk_context}...")

    # Analysis
    print(f"\n{'=' * 80}")
    print("ANALYSIS")
    print(f"{'=' * 80}")

    if chunk_999_reranked_position < 10:
        print(f"\n✅ Chunk 999 IS in top 10 (rank {chunk_999_reranked_position + 1})")
        print(f"   It SHOULD reach the generator")
        print(f"\n💡 The problem might be:")
        print(f"   - Generator is choosing wrong source when multiple are available")
        print(f"   - Other chunks are ranked higher and misleading the generator")
    else:
        print(f"\n❌ Chunk 999 is at rank {chunk_999_reranked_position + 1} (outside top 10)")
        print(f"   Need to increase RERANK_TOP_K beyond 10")

    print(f"\n{'=' * 80}")

if __name__ == '__main__':
    main()
