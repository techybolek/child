# Kendra Mode Rearchitecture Plan

## Objective

Rearchitect `KendraHandler` to use Kendra only for retrieval, then pass chunks to the existing RAG pipeline's generator. This normalizes answer generation across all evaluation modes (hybrid, dense, kendra) for fair comparison.

## Current State vs Target State

### Current Architecture
```
Kendra Mode: Kendra retrieval → Bedrock Titan generation (generic prompt)
Hybrid Mode: Qdrant hybrid retrieval → GROQ reranking → GROQ/OpenAI generation (specialized prompt)
Dense Mode:  Qdrant dense retrieval → GROQ reranking → GROQ/OpenAI generation (specialized prompt)
```

### Target Architecture
```
Kendra Mode: Kendra retrieval (with built-in reranking) → GROQ/OpenAI generation (specialized prompt)
Hybrid Mode: Qdrant hybrid retrieval → GROQ reranking → GROQ/OpenAI generation (specialized prompt)
Dense Mode:  Qdrant dense retrieval → GROQ reranking → GROQ/OpenAI generation (specialized prompt)
```

## Rationale

### Why Skip Reranking for Kendra?
- Kendra already performs semantic + keyword matching + ML reranking internally
- Kendra's `top_k` results are effectively pre-reranked
- Avoids redundant double-reranking (Kendra's built-in + GROQ LLM-based)

### Benefits
1. **Fair comparison**: Isolates retrieval quality by normalizing generation layer
2. **Consistent quality**: All modes use same domain-specific prompt with Texas childcare rules
3. **Reduced variables**: Only compares retrieval+reranking strategies, not generation models
4. **Cost efficiency**: No Bedrock dependency, uses existing GROQ/OpenAI setup

## Implementation Plan

### File: `chatbot/handlers/kendra_handler.py`

#### Changes Required

**1. Remove (Lines to Delete)**
- Line 3: `from langchain_aws import ChatBedrockConverse` → No longer using Bedrock
- Line 4: `from langchain_core.prompts import ChatPromptTemplate` → No manual prompts
- Line 5: `from langchain_core.output_parsers import StrOutputParser` → No LangChain chains
- Line 6: `from langchain_core.runnables import RunnablePassthrough` → No LangChain chains
- Lines 25-29: `self.llm = ChatBedrockConverse(...)` → Replaced by ResponseGenerator
- Lines 31-41: `self.prompt = ChatPromptTemplate.from_template(...)` → Using RESPONSE_GENERATION_PROMPT
- Lines 43-49: `_format_docs()` method → Replaced by `_convert_kendra_docs_to_chunks()`
- Lines 92-94: LangChain chain construction and invocation → Using `generator.generate()`

**2. Add (New Imports)**
```python
from ..generator import ResponseGenerator
from .. import config
```

**3. Modify `__init__()` Method**

Replace Bedrock LLM initialization with ResponseGenerator:

```python
def __init__(self):
    """Initialize Kendra retriever and ResponseGenerator"""
    # Kendra retriever (unchanged)
    self.retriever = AmazonKendraRetriever(
        index_id=config.KENDRA_INDEX_ID,
        region_name=config.KENDRA_REGION,
        top_k=config.KENDRA_TOP_K,
        min_score_confidence=0.0
    )

    # Response generator (NEW - replaces Bedrock LLM)
    effective_provider = config.LLM_PROVIDER
    generator_api_key = (
        config.GROQ_API_KEY if effective_provider == 'groq'
        else config.OPENAI_API_KEY
    )
    self.generator = ResponseGenerator(
        api_key=generator_api_key,
        provider=effective_provider,
        model=config.LLM_MODEL
    )
```

**4. Add New Method: `_convert_kendra_docs_to_chunks()`**

Replace `_format_docs()` with document format converter:

```python
def _convert_kendra_docs_to_chunks(self, kendra_docs) -> list:
    """Convert AmazonKendraRetriever documents to ResponseGenerator format

    Args:
        kendra_docs: List of LangChain Document objects from Kendra

    Returns:
        List of chunk dictionaries compatible with ResponseGenerator
    """
    chunks = []
    for doc in kendra_docs:
        chunk = {
            # Required fields for generator
            'text': doc.page_content,
            'filename': doc.metadata.get('source') or doc.metadata.get('title', 'Unknown'),
            'page': doc.metadata.get('page', 'N/A'),
            'source_url': doc.metadata.get('source_uri') or doc.metadata.get('document_uri', ''),

            # Optional context fields (Kendra doesn't provide these)
            'master_context': None,
            'document_context': None,
            'chunk_context': None,
        }
        chunks.append(chunk)
    return chunks
```

**5. Rewrite `handle()` Method**

Replace LangChain chain with generator pipeline:

```python
def handle(self, query: str, debug: bool = False) -> dict:
    """Run Kendra retrieval + ResponseGenerator pipeline"""
    debug_data = {}

    # Step 1: Retrieve from Kendra (includes built-in reranking)
    kendra_docs = self.retriever.invoke(query)

    if not kendra_docs:
        return {
            'answer': "I couldn't find information about that. Try calling 1-800-862-5252.",
            'sources': [],
            'response_type': 'information',
            'action_items': []
        }

    # Store retrieved docs for debug
    if debug:
        debug_data['retrieved_chunks'] = [
            {
                'doc': d.metadata.get('source', d.metadata.get('title', '')),
                'page': d.metadata.get('page', ''),
                'score': d.metadata.get('score', 0),
                'text': d.page_content[:500] + '...' if len(d.page_content) > 500 else d.page_content,
                'source_url': d.metadata.get('source_uri', ''),
            }
            for d in kendra_docs
        ]

    # Step 2: Convert Kendra docs to generator-compatible chunks
    chunks = self._convert_kendra_docs_to_chunks(kendra_docs)

    # Step 3: Generate answer using ResponseGenerator (not Bedrock)
    result = self.generator.generate(query, chunks)

    # Step 4: Extract cited sources from answer
    cited_sources = self._extract_cited_sources(result['answer'], chunks)

    response = {
        'answer': result['answer'],
        'sources': cited_sources,
        'response_type': 'information',
        'action_items': []
    }

    if debug:
        response['debug_info'] = debug_data

    return response
```

**6. Update `_extract_cited_sources()` Method**

Update to work with chunk dictionaries instead of Kendra docs:

```python
def _extract_cited_sources(self, answer: str, chunks: list) -> list:
    """Extract only the sources that were actually cited in the answer

    Args:
        answer: Generated answer text with [Doc N] citations
        chunks: List of chunk dictionaries used for generation

    Returns:
        List of cited source dictionaries
    """
    import re

    # Find all [Doc N] citations in the answer
    cited_doc_nums = set(re.findall(r'\[Doc\s*(\d+):', answer))

    # Map citation numbers to chunk metadata
    cited_sources = []
    for doc_num in sorted(cited_doc_nums, key=int):
        idx = int(doc_num) - 1  # Convert to 0-based index
        if 0 <= idx < len(chunks):
            chunk = chunks[idx]
            cited_sources.append({
                'doc': chunk['filename'],
                'page': chunk['page'],
                'url': chunk['source_url']
            })

    # If no citations found, return all sources
    if not cited_sources:
        return [
            {
                'doc': chunk['filename'],
                'page': chunk['page'],
                'url': chunk['source_url']
            }
            for chunk in chunks
        ]

    return cited_sources
```

**7. Remove `_map_sources()` Method**

This method is no longer needed since we're using chunk dictionaries directly.

### Configuration Changes

**File: `chatbot/config.py`**

No changes required - already has:
- `LLM_PROVIDER` (defaults to 'groq')
- `LLM_MODEL` (model name)
- `GROQ_API_KEY` and `OPENAI_API_KEY`
- `KENDRA_INDEX_ID`, `KENDRA_REGION`, `KENDRA_TOP_K`

### Evaluation System Updates

**File: `evaluation/kendra_evaluator.py`**

Verify that KendraEvaluator correctly instantiates the updated KendraHandler. No changes should be needed if it's just calling `handler.handle(query)`.

### Testing Changes

**File: `AMAZON_EXPERIMENT/kendra_test.py`**

This example script demonstrates the old architecture. Consider updating it to show the new pattern, or mark it as deprecated.

## Document Format Mapping

### Kendra Output → Generator Input

| Kendra Field | Generator Field | Mapping |
|--------------|----------------|---------|
| `doc.page_content` | `chunk['text']` | Direct copy |
| `doc.metadata['source']` or `metadata['title']` | `chunk['filename']` | Fallback to 'Unknown' |
| `doc.metadata['page']` | `chunk['page']` | Fallback to 'N/A' |
| `doc.metadata['source_uri']` or `metadata['document_uri']` | `chunk['source_url']` | Fallback to empty string |
| N/A | `chunk['master_context']` | Set to None |
| N/A | `chunk['document_context']` | Set to None |
| N/A | `chunk['chunk_context']` | Set to None |

## Prompt Changes

### Before (Generic Kendra Prompt)
```
Answer the question based on the following context.
If the context doesn't contain enough information, say so clearly.
Include specific details and cite sources using [Doc N] format.

Context: {context}
Question: {question}
```

### After (Specialized RAG Prompt)
Uses `chatbot/prompts/response_generation_prompt.py`:
- Texas childcare expert persona
- Abbreviations glossary (BCY, PSoC, TWC, CCDF)
- Exact income limits with year/BCY
- Ordered application steps
- Outcome types (employment rates + wage data)
- Table year column positioning rules
- [Doc N: filename, Page X] citation format

## Pipeline Comparison Table

| Mode | Retrieval | Reranking | Generation Model | Generation Prompt |
|------|-----------|-----------|------------------|-------------------|
| **Before** |
| hybrid | Qdrant RRF | GROQ LLM | GROQ/OpenAI | Specialized |
| dense | Qdrant semantic | GROQ LLM | GROQ/OpenAI | Specialized |
| kendra | Kendra | Kendra built-in | Bedrock Titan | Generic |
| **After** |
| hybrid | Qdrant RRF | GROQ LLM | GROQ/OpenAI | Specialized |
| dense | Qdrant semantic | GROQ LLM | GROQ/OpenAI | Specialized |
| kendra | Kendra | Kendra built-in | GROQ/OpenAI | Specialized ✓ |

## Implementation Steps

1. **Backup current file**
   ```bash
   cp chatbot/handlers/kendra_handler.py chatbot/handlers/kendra_handler.py.backup
   ```

2. **Update imports** (remove LangChain, add ResponseGenerator)

3. **Rewrite `__init__()`** (remove Bedrock, add generator)

4. **Add `_convert_kendra_docs_to_chunks()`** method

5. **Rewrite `handle()`** method (replace chain with generator.generate())

6. **Update `_extract_cited_sources()`** (work with chunks not docs)

7. **Remove `_map_sources()` and `_format_docs()` methods**

8. **Test with single query**
   ```python
   from chatbot.handlers.kendra_handler import KendraHandler
   handler = KendraHandler()
   result = handler.handle("What is PSoC?", debug=True)
   print(result['answer'])
   ```

9. **Run evaluation**
   ```bash
   python -m evaluation.run_evaluation --mode kendra --limit 5
   ```

10. **Compare results** with hybrid/dense modes

## Validation Checklist

- [ ] KendraHandler imports ResponseGenerator successfully
- [ ] Generator uses GROQ/OpenAI (not Bedrock)
- [ ] Chunks have correct format (text, filename, page, source_url)
- [ ] Answer includes [Doc N: filename, Page X] citations
- [ ] Specialized prompt rules applied (abbreviations, income limits, etc.)
- [ ] Debug mode captures retrieved chunks correctly
- [ ] Citation extraction works with new chunk format
- [ ] No LangChain chain dependencies remain
- [ ] Evaluation runs without errors
- [ ] Answers match quality of hybrid/dense modes

## Expected Outcomes

### Performance Impact
- **Latency**: Slightly lower (GROQ faster than Bedrock Titan)
- **Cost**: Lower (GROQ free tier vs Bedrock pricing)
- **Quality**: Higher (specialized prompt vs generic)

### Evaluation Insights
After implementation, comparison will reveal:
1. **Retrieval quality**: Kendra vs Qdrant (isolated variable)
2. **Reranking impact**: Kendra built-in vs GROQ LLM-based
3. **Cost-benefit**: AWS managed service vs self-hosted Qdrant

## Rollback Plan

If issues arise:
```bash
cp chatbot/handlers/kendra_handler.py.backup chatbot/handlers/kendra_handler.py
```

Restore original Bedrock-based implementation.

## Future Enhancements

### Optional: Add Contextual Embeddings Support
If Kendra supports custom metadata:
- Inject master_context, document_context, chunk_context
- Requires uploading PDFs with context metadata to Kendra index

### Optional: Provider Override
Allow evaluation to specify generator provider:
```python
handler = KendraHandler(provider='openai')  # Override default GROQ
```

Match RAGHandler's flexible provider pattern.

## Critical Files Summary

**Modified:**
- `chatbot/handlers/kendra_handler.py` (complete rewrite)

**Referenced (no changes):**
- `chatbot/generator.py` (reused)
- `chatbot/config.py` (reused)
- `chatbot/prompts/response_generation_prompt.py` (reused)
- `evaluation/kendra_evaluator.py` (verify compatibility)

**Deprecated:**
- `AMAZON_EXPERIMENT/kendra_test.py` (shows old architecture)
