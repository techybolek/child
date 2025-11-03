"""
Tier 2: Document-Level Context (generated once per PDF)
"""


def build_document_context_prompt(master_context, document_title, source_url, total_pages, first_2000_chars):
    """
    Generate a prompt for creating document-level context.
    
    Args:
        master_context: Static master context from Tier 1
        document_title: PDF filename
        source_url: Source URL of the document
        total_pages: Total pages in the PDF
        first_2000_chars: First 2000 characters of the PDF content
    
    Returns:
        Formatted prompt string for GROQ API
    """
    return f"""MASTER CONTEXT:
{master_context}

---

You are analyzing a Texas Workforce Commission document. Given the master context above, analyze this document excerpt.

DOCUMENT METADATA:
- Filename: {document_title}
- Source: {source_url}
- Total Pages: {total_pages}

DOCUMENT EXCERPT (first ~2000 chars):
{first_2000_chars}

---

Give a short succinct context (2-3 sentences) describing what this document covers. Answer only with the succinct context and nothing else."""