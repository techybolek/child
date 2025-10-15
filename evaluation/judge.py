import json
from groq import Groq
from . import config

JUDGE_PROMPT = """You are evaluating a chatbot's response to a question about Texas child care services.

Compare the chatbot's answer to the expected answer and score it on these criteria:

1. **Factual Accuracy (0-5)**: Does the chatbot answer contain the same facts as the expected answer?
2. **Completeness (0-5)**: Are all key points from the expected answer covered?
3. **Citation Quality (0-5)**: Are the sources provided relevant to the question?
4. **Coherence (0-3)**: Is the answer well-structured and clear?

IMPORTANT:
- Do NOT penalize for different formatting or wording
- Do NOT penalize for extra helpful context not in expected answer
- Focus on factual correctness and completeness

Question: {question}

Expected Answer: {expected_answer}

Chatbot Answer: {chatbot_answer}

Sources Cited: {sources}

Return your evaluation as JSON with this exact format:
{{
    "accuracy": <0-5>,
    "completeness": <0-5>,
    "citation_quality": <0-5>,
    "coherence": <0-3>,
    "reasoning": "<brief explanation>"
}}
"""


class LLMJudge:
    def __init__(self):
        self.client = Groq(api_key=config.JUDGE_API_KEY)
        self.model = config.JUDGE_MODEL

    def evaluate(self, question: str, expected_answer: str, chatbot_answer: str, sources: list) -> dict:
        """Evaluate chatbot response using LLM judge"""

        # Format sources
        sources_str = "\n".join([f"- {s['doc']}, Page {s['page']}" for s in sources]) if sources else "None"

        # Build prompt
        prompt = JUDGE_PROMPT.format(
            question=question,
            expected_answer=expected_answer,
            chatbot_answer=chatbot_answer,
            sources=sources_str
        )

        # Call LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        # Parse JSON response
        content = response.choices[0].message.content

        # Extract JSON from response (handle markdown code blocks)
        if '```json' in content:
            json_str = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            json_str = content.split('```')[1].split('```')[0].strip()
        else:
            json_str = content.strip()

        scores = json.loads(json_str)

        # Calculate composite score
        composite = (
            scores['accuracy'] * config.WEIGHTS['accuracy'] +
            scores['completeness'] * config.WEIGHTS['completeness'] +
            scores['citation_quality'] * config.WEIGHTS['citation_quality'] +
            scores['coherence'] * config.WEIGHTS['coherence']
        )

        # Normalize to 0-100 scale
        max_score = (5 * config.WEIGHTS['accuracy'] +
                     5 * config.WEIGHTS['completeness'] +
                     5 * config.WEIGHTS['citation_quality'] +
                     3 * config.WEIGHTS['coherence'])

        scores['composite_score'] = (composite / max_score) * 100

        return scores
