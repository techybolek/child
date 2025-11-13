"""Reranking prompt for scoring chunk relevance"""

RERANKING_PROMPT = """You are scoring chunks from Texas childcare policy documents for relevance to a user question.

Context: These are Texas childcare policy documents containing workforce development data,
program evaluations, and statistical reports. Policy questions often use broad terms (like
"outcomes", "impact", "performance") that encompass multiple specific metrics and data types.

Question: {query}

{chunks_text}

Evaluation approach:
1. Identify the core topic and what types of data would answer the question
2. Consider related concepts and component metrics (e.g., "employment outcomes" includes
   employment status, wages, earnings, retention - these are all equally important outcome types)
3. Score based on how the chunk contributes to answering, not just term matching

Scoring criteria (0-10):
- 9-10: Contains specific data directly addressing the question
  (includes component metrics that fall within the question's scope)
- 7-8: Highly relevant, addresses major aspects of the question
- 5-6: Addresses the topic but partial/incomplete for the specific question
- 3-4: Related topic but wrong specificity (e.g., wrong year, wrong breakdown)
- 1-2: Tangentially related or very weak relevance
- 0: Unrelated topic

IMPORTANT:
- Think semantically: consider whether chunks provide data that contributes to answering
  the question, even if using different terminology (e.g., "wages" can address "employment
  outcomes" questions; "enrollment data" can address "participation" questions)
- Component data (e.g., "$100M + $50M") can answer questions about total amounts
- Temporal markers matter (FY'XX, BCY XX, specific years)
- Spatial/categorical breakdowns matter (by region, by demographic, by board area)
- Tables often span multiple chunks - score each chunk's contribution

Return compact JSON: {{"chunk_0": <score>, "chunk_1": <score>, ...}}"""
