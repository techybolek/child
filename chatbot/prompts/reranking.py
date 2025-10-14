"""Reranking prompt for scoring chunk relevance"""

RERANKING_PROMPT = """Score how relevant each chunk is to this question (0-10):

Question: {query}

{chunks_text}

Return JSON: {{"chunk_0": <score>, "chunk_1": <score>, ...}}"""
