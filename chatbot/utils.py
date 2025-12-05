"""Shared utilities for chatbot module."""

import re


def extract_cited_sources(answer: str, chunks: list) -> list:
    """Extract, deduplicate, and consolidate cited sources from LLM answer.

    Args:
        answer: LLM response containing [Doc N] citations
        chunks: Reranked chunks list with filename, page, source_url

    Returns:
        List of consolidated source dicts with doc, pages (sorted list), url keys
    """
    # Match both standard [Doc N] and full-width【Doc N】brackets
    cited_doc_nums = set(re.findall(r'[\[【]Doc\s*(\d+)[\]】]', answer))

    # Group by document filename
    doc_pages = {}  # {filename: {'pages': set(), 'url': str}}
    for doc_num in cited_doc_nums:
        idx = int(doc_num) - 1
        if 0 <= idx < len(chunks):
            chunk = chunks[idx]
            filename = chunk['filename']
            if filename not in doc_pages:
                doc_pages[filename] = {
                    'pages': set(),
                    'url': chunk.get('source_url', '')
                }
            # Convert 0-indexed internal page to 1-indexed for display
            page = chunk['page']
            if isinstance(page, int):
                page = page + 1
            doc_pages[filename]['pages'].add(page)

    # Build consolidated sources list, sorted by filename
    sources = []
    for filename in sorted(doc_pages.keys()):
        info = doc_pages[filename]
        sources.append({
            'doc': filename,
            'pages': sorted(info['pages']),
            'url': info['url']
        })

    return sources
