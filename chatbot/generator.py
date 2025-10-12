from openai import OpenAI


class ResponseGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate(self, query: str, context_chunks: list):
        """Generate response with citations"""

        # Format context with citations
        context = self._format_context(context_chunks)

        # Build prompt
        prompt = f"""You are an expert on Texas childcare assistance programs.

Answer the question using ONLY the provided documents. Always cite sources using [Doc X] format.

Key rules:
- State income limits with exact amounts and year/BCY
- For application questions, list steps in order
- If info missing, say "I don't have information on..."
- Never make up numbers or dates

DOCUMENTS:
{context}

QUESTION: {query}

ANSWER (with citations):"""

        # Generate
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )

        return {
            'answer': response.choices[0].message.content,
            'usage': response.usage
        }

    def _format_context(self, chunks: list):
        """Format chunks with citation markers"""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"[Doc {i}: {chunk['filename']}, Page {chunk['page']}]\n"
                f"{chunk['text']}\n"
            )
        return "\n".join(parts)
