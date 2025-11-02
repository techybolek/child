"""
Chunk-level context generation prompt.

Used to generate 50-100 token contexts for each chunk that capture:
- Main topic/subject matter
- Specific programs, amounts, family sizes, percentages
- What makes this chunk unique
- What queries this chunk would answer
"""


def build_chunk_context_prompt(
    document_context: str,
    chunk_text: str,
) -> str:
    """
    Build a prompt for generating chunk-level context.

    Args:
        document_context: The document-level context from Tier 2
        chunk_text: The actual chunk text

    Returns:
        Formatted prompt string for GROQ API
    """
    prompt = f"""Document context: {document_context}

Here is the chunk we want to situate within the overall document:
{chunk_text}

---

Give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval. Answer only with the succinct context and nothing else."""
    return prompt
