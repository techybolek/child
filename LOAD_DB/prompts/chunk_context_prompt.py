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
    previous_chunk_context: str = None,
    previous_chunk_text_snippet: str = None,
) -> str:
    """
    Build a prompt for generating chunk-level context.

    Args:
        document_context: The document-level context from Tier 2
        chunk_text: The actual chunk text
        previous_chunk_context: Optional context from the previous chunk for continuity
        previous_chunk_text_snippet: Optional snippet from end of previous chunk

    Returns:
        Formatted prompt string for GROQ API
    """
    prompt = f"""Document context: {document_context}

"""

    # Include previous chunk information if available
    if previous_chunk_context:
        prompt += f"""PREVIOUS CHUNK CONTEXT (for continuity):
{previous_chunk_context}
"""
        if previous_chunk_text_snippet:
            prompt += f"""
PREVIOUS CHUNK TEXT (last 200 chars):
{previous_chunk_text_snippet}

"""
        prompt += """CRITICAL INSTRUCTIONS:
1. This chunk likely CONTINUES from the previous chunk
2. Look at the ACTUAL DATA VALUES in this chunk's body (income numbers, amounts, percentages)
3. IGNORE section headers at the END of the chunk - they mark the NEXT section, not this one
4. Identify family size, table type, and income ranges from the chunk's PRIMARY CONTENT, not from end-of-chunk markers
5. Cross-reference with previous context to confirm continuity and correct family size

"""

    prompt += f"""Here is the chunk we want to situate within the overall document:
{chunk_text}

---

Give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval.
Focus on: table type, family size (if applicable), income ranges covered, and what specific data this chunk contains.
Answer only with the succinct context and nothing else."""

    return prompt
