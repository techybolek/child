import json
import re
from groq import Groq
from . import config

JUDGE_PROMPT = """Evaluate this chatbot answer. Return ONLY one JSON object, nothing else.

Question: {question}

Expected: {expected_answer}

Chatbot: {chatbot_answer}

Sources: {sources}

Score (0-5 for accuracy/completeness/citations, 0-3 for coherence):
- Factual Accuracy: same facts as expected?
- Completeness: all key points covered?
- Citation Quality: sources relevant?
- Coherence: clear and structured?

Return ONLY this JSON (no repetition, no extra text):
{{
    "accuracy": <0-5>,
    "completeness": <0-5>,
    "citation_quality": <0-5>,
    "coherence": <0-3>,
    "reasoning": "<one sentence>"
}}
"""

JUDGE_PROMPT_NO_CITATIONS = """Evaluate this chatbot answer. Return ONLY one JSON object, nothing else.

Question: {question}

Expected: {expected_answer}

Chatbot: {chatbot_answer}

Sources: {sources}

Score (0-5 for accuracy/completeness, 0-3 for coherence):
- Factual Accuracy: same facts as expected?
- Completeness: all key points covered?
- Coherence: clear and structured?

NOTE: Citation quality is NOT being evaluated. Sources are shown for reference only.

Return ONLY this JSON (no repetition, no extra text):
{{
    "accuracy": <0-5>,
    "completeness": <0-5>,
    "coherence": <0-3>,
    "reasoning": "<one sentence>"
}}
"""


class LLMJudge:
    def __init__(self):
        self.client = Groq(api_key=config.JUDGE_API_KEY)
        self.model = config.JUDGE_MODEL

    def evaluate(self, question: str, expected_answer: str, chatbot_answer: str, sources: list, debug: bool = False) -> dict:
        """Evaluate chatbot response using LLM judge"""

        # Format sources (handle both 'pages' list and 'page' single value)
        def format_source(s):
            pages = s.get('pages', [s.get('page', 'N/A')])
            pages_str = ', '.join(str(p) for p in pages) if isinstance(pages, list) else str(pages)
            return f"- {s['doc']}, Page(s) {pages_str}"
        sources_str = "\n".join([format_source(s) for s in sources]) if sources else "None"

        # Choose prompt based on citation scoring setting
        if config.DISABLE_CITATION_SCORING:
            prompt_template = JUDGE_PROMPT_NO_CITATIONS
        else:
            prompt_template = JUDGE_PROMPT

        # Build prompt
        prompt = prompt_template.format(
            question=question,
            expected_answer=expected_answer,
            chatbot_answer=chatbot_answer,
            sources=sources_str
        )

        # Call LLM with sufficient tokens to prevent truncation
        print("  [Judge] Calling LLM judge API...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500,  # Increased from 500 to prevent truncation artifacts
                timeout=30  # 30 second timeout
            )
            print(f"  [Judge] Response received ({len(response.choices[0].message.content)} chars)")
        except Exception as e:
            print(f"  [Judge] API call failed: {type(e).__name__}: {str(e)}")
            raise

        # Capture raw reasoning for debug (available for reasoning models like gpt-oss)
        raw_reasoning = None
        if debug:
            # Check message level first (OpenAI/GROQ structure)
            if hasattr(response.choices[0].message, 'reasoning'):
                raw_reasoning = response.choices[0].message.reasoning
            # If not found, check top level (alternative structure)
            if not raw_reasoning and hasattr(response, 'reasoning'):
                raw_reasoning = response.reasoning

        # Parse JSON response
        content = response.choices[0].message.content

        # Clean up chat template tokens
        content = content.replace('<|start_header_id|>', '').replace('<|end_header_id|>', '')
        content = content.replace('assistant', '')

        # Remove repetitive patterns (handles "sources sources" and "word-word word-word")
        content = re.sub(r'(\b\w+[-\w]*\b)(\s+\1){2,}', r'\1', content)

        # Remove lines that are purely repetitive
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            words = line.split()
            if len(words) > 0 and len(set(words)) / len(words) > 0.3:  # Keep if >30% unique words
                cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)

        # Extract JSON from response (handle markdown code blocks)
        if '```json' in content:
            json_str = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            json_str = content.split('```')[1].split('```')[0].strip()
        else:
            json_str = content.strip()

        # Extract ONLY the first complete JSON object
        # Find the first '{' and then find its matching '}'
        start_idx = json_str.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in response")

        # Count braces to find the matching closing brace
        brace_count = 0
        end_idx = -1
        for i in range(start_idx, len(json_str)):
            if json_str[i] == '{':
                brace_count += 1
            elif json_str[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break

        if end_idx == -1:
            # Fallback: use rfind
            end_idx = json_str.rfind('}')

        if end_idx > start_idx:
            json_str = json_str[start_idx:end_idx + 1]

        # Clean control characters that break JSON parsing
        # Replace newlines, tabs, etc. inside JSON strings with spaces
        json_str = json_str.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        # Normalize multiple spaces
        json_str = re.sub(r'\s+', ' ', json_str)

        # Parse JSON
        try:
            scores = json.loads(json_str)
        except json.JSONDecodeError:
            # If parsing fails, print debug info and re-raise
            print(f"\n[ERROR] Failed to parse JSON from LLM judge")
            print(f"Content length: {len(content)} chars")
            print(f"Extracted JSON:\n{json_str}\n")
            raise

        # Add null citation_quality if disabled
        if config.DISABLE_CITATION_SCORING:
            scores['citation_quality'] = None

        # Calculate composite score
        if config.DISABLE_CITATION_SCORING:
            # Normalized weights when citations disabled (divide by 0.9)
            composite = (
                scores['accuracy'] * (config.WEIGHTS['accuracy'] / 0.9) +
                scores['completeness'] * (config.WEIGHTS['completeness'] / 0.9) +
                scores['coherence'] * (config.WEIGHTS['coherence'] / 0.9)
            )
            # Max score without citations: 5*0.556 + 5*0.333 + 3*0.111 = 4.778
            max_score = (5 * (config.WEIGHTS['accuracy'] / 0.9) +
                        5 * (config.WEIGHTS['completeness'] / 0.9) +
                        3 * (config.WEIGHTS['coherence'] / 0.9))
        else:
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

        # Add raw reasoning if debug mode and reasoning available
        if debug and raw_reasoning:
            scores['raw_reasoning'] = raw_reasoning

        return scores
