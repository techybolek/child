"""
Document-level context generation prompt.

Used to generate 100-150 token summaries for each PDF that capture:
- Document purpose and scope
- Key programs/policies covered
- Target audience
- Key metrics/thresholds
- Document type
"""


def build_document_context_prompt(
    document_title: str,
    total_pages: int,
    first_2000_chars: str,
) -> str:
    """
    Build a prompt for generating document-level context.

    Args:
        document_title: Filename of the document
        total_pages: Total number of pages
        first_2000_chars: First ~2000 characters of document content

    Returns:
        Formatted prompt string for GROQ API
    """
    prompt = f"""You are analyzing a Texas Workforce Commission document.

Document: {document_title}
Pages: {total_pages}

Document excerpt:
{first_2000_chars}

---

Give a short succinct context (2-3 sentences) describing what this document covers. Answer only with the succinct context and nothing else."""
    return prompt
