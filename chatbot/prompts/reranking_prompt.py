"""Reranking prompt for scoring chunk relevance"""

RERANKING_PROMPT = """You are scoring chunks from Texas childcare policy documents for relevance to a user question.

Question: {query}

{chunks_text}

Scoring criteria (0-10):
- 10: Directly answers the question with specific relevant data
- 7-9: Highly relevant explanation or partial answer
- 4-6: Related topic but missing key details
- 1-3: Tangentially related or different context
- 0: Unrelated

IMPORTANT:
- Score based on whether the chunk helps answer the question, not exact wording match
- Component data (e.g., "$100M + $50M") can answer questions about total amounts
- Temporal markers matter (FY'XX, BCY XX, specific years)
- Tables/data often span multiple chunks - score each chunk's contribution

Return compact JSON: {{"chunk_0": <score>, "chunk_1": <score>, ...}}"""
