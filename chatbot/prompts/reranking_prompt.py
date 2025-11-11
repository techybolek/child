"""Reranking prompt for scoring chunk relevance"""

RERANKING_PROMPT = """You are scoring chunks from Texas childcare policy documents for relevance to a user question.

Question: {query}

{chunks_text}

Scoring criteria (0-10):
- 10: Contains specific data directly answering the question (numbers, dollar amounts, counts, dates)
- 7-9: Highly relevant explanation or partial answer
- 4-6: Related topic but missing key details
- 1-3: Tangentially related or different time period
- 0: Unrelated

IMPORTANT:
- Prioritize chunks matching temporal markers (FY'XX, BCY XX, specific years in the question)
- Value specific data over general explanations
- Recognize that tables/data often continue across adjacent chunks

Return compact JSON: {{"chunk_0": <score>, "chunk_1": <score>, ...}}"""
