# Texas Childcare Chatbot - Simple RAG Prototype Implementation

**Project:** Texas State Childcare Resources Chatbot
**Database:** Qdrant Cloud (3,722 chunks from 42 PDFs, already loaded)
**Approach:** Simple, pragmatic RAG PRototype - no over-engineering
**Date:** October 12, 2025

---

## What This Actually Does

This is a straightforward RAG chatbot:

1. **User asks a question** about Texas childcare assistance
2. **Semantic search** in Qdrant finds relevant document chunks
3. **Reranker** improves result quality
4. **LLM** (GPT-4) generates answer with citations
5. **Return response** with source documents

**Not hybrid search.** Not multi-agent. Not enterprise-scale. Just basic RAG that works.

---

## Current Infrastructure (Already Built)

### Qdrant Vector Database
```
Collection: tro-child-1
Chunks: 3,722 (from 42 PDFs, 1,321 pages)
Embeddings: OpenAI text-embedding-3-small (1,536 dimensions)
Distance: Cosine similarity
```

### Document Types
- Policy documents (CCDF state plans, regulations)
- Parent guides (eligibility, rights, application)
- Provider guides (payment rates, desk aids)
- Legislative reports
- Board-specific rate charts

### Metadata (in each chunk)
```json
{
  "text": "chunk content...",
  "filename": "child-care-services-guide-twc.pdf",
  "page": 45,
  "source_url": "https://www.twc.texas.gov/...",
  "chunk_index": 23,
  "total_chunks": 156
}
```

---

## Architecture (Keep It Simple)

```
User Query
    ↓
Qdrant Search (semantic similarity)
    ↓
LLM Judge Reranker (scores relevance 0-10)
    ↓
Context Assembly (format with citations)
    ↓
GPT-4 Generation
    ↓
Response
```

That's it. No query processing. No intent classification. No conversation memory.

---

## Implementation

### Minimal Directory Structure

```
TX/
├── chatbot/
│   ├── config.py              # Configuration
│   ├── retriever.py           # Qdrant search
│   ├── reranker.py            # Reranking
│   ├── generator.py           # LLM generation
│   └── chatbot.py             # Main orchestrator
│
├── test_chatbot.py            # Simple test script
└── requirements.txt           # Dependencies
```

## Component 1: Retriever

**Purpose:** Search Qdrant for relevant chunks

```python
# chatbot/retriever.py
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
import config

class QdrantRetriever:
    def __init__(self):
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            model='text-embedding-3-small'
        )
        self.collection = 'tro-child-1'

    def search(self, query: str, top_k: int = 20):
        """Search Qdrant for relevant chunks"""
        # Embed query
        query_vector = self.embeddings.embed_query(query)

        # Search
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=0.3  # Filter low-relevance results
        )

        # Return as simple dicts
        return [
            {
                'text': hit.payload['text'],
                'score': hit.score,
                'filename': hit.payload.get('filename', ''),
                'page': hit.payload.get('page', 'N/A'),
                'source_url': hit.payload.get('source_url', '')
            }
            for hit in results
        ]
```

**That's it.** No metadata filtering (add later if needed). No query expansion. Just search.

---

## Component 2: Reranker

```python
# chatbot/reranker.py
from openai import OpenAI
import json

class LLMJudgeReranker:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def rerank(self, query: str, chunks: list, top_k: int = 7):
        """Rerank using LLM relevance scoring"""

        # Build prompt
        chunks_text = "\n\n".join([
            f"CHUNK {i}:\n{chunk['text'][:300]}..."
            for i, chunk in enumerate(chunks)
        ])

        prompt = f"""Score how relevant each chunk is to this question (0-10):

Question: {query}

{chunks_text}

Return JSON: {{"chunk_0": <score>, "chunk_1": <score>, ...}}"""

        # Get scores
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # Cheap and fast
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        scores = json.loads(response.choices[0].message.content)

        # Update scores
        for i, chunk in enumerate(chunks):
            chunk['final_score'] = scores.get(f"chunk_{i}", 0) / 10.0

        # Sort and return top_k
        chunks.sort(key=lambda c: c['final_score'], reverse=True)
        return chunks[:top_k]
```


## Component 3: Generator

**Purpose:** Call GPT-4 to generate answer

```python
# chatbot/generator.py
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

DOCUMENTS:
{context}

QUESTION: {query}

ANSWER (with citations):"""

        # Generate
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Low for accuracy
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
```

---

## Component 4: Main Chatbot

**Purpose:** Orchestrate everything

```python
# chatbot/chatbot.py
from retriever import QdrantRetriever
from reranker import LLMJudgeReranker  # or BM25Reranker, or None
from generator import ResponseGenerator
import config

class TexasChildcareChatbot:
    def __init__(self):
        self.retriever = QdrantRetriever()
        self.reranker = LLMJudgeReranker(config.OPENAI_API_KEY)  # or None to skip
        self.generator = ResponseGenerator(config.OPENAI_API_KEY)

    def ask(self, question: str):
        """Ask a question, get an answer"""

        # Step 1: Search Qdrant
        print("Searching...")
        chunks = self.retriever.search(question, top_k=20)

        if not chunks:
            return {
                'answer': "I couldn't find information about that. Try calling 1-800-862-5252.",
                'sources': []
            }

        # Step 2: Rerank
        if self.reranker:
            print("Reranking...")
            chunks = self.reranker.rerank(question, chunks, top_k=7)
        else:
            chunks = chunks[:7]

        # Step 3: Generate answer
        print("Generating answer...")
        result = self.generator.generate(question, chunks)

        # Step 4: Return response
        return {
            'answer': result['answer'],
            'sources': [
                {'doc': c['filename'], 'page': c['page'], 'url': c['source_url']}
                for c in chunks
            ]
        }
```

---

## Configuration

```python
# chatbot/config.py
import os

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Qdrant settings
COLLECTION_NAME = 'tro-child-1'
EMBEDDING_MODEL = 'text-embedding-3-small'

# Retrieval settings
RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 7
MIN_SCORE_THRESHOLD = 0.3

# Generation settings
LLM_MODEL = 'gpt-4-turbo-preview'
TEMPERATURE = 0.1
MAX_TOKENS = 1000
```

---

## Usage

### Simple Test Script

```python
# test_chatbot.py
from chatbot import TexasChildcareChatbot

chatbot = TexasChildcareChatbot()

# Ask a question
response = chatbot.ask("What are the income limits for a family of 3 in BCY 2026?")

print("ANSWER:")
print(response['answer'])

print("\nSOURCES:")
for source in response['sources']:
    print(f"- {source['doc']}, Page {source['page']}")
```

Run: `python test_chatbot.py`

---

## Dependencies

Add to `requirements.txt`:

```txt
# RAG Chatbot (minimal)
tiktoken>=0.5.0            # Token counting (optional)

```

Already have (from load_pdf_qdrant.py):
- langchain-openai
- langchain-community
- qdrant-client
- openai

**Note:** LLM Judge reranker needs no extra dependencies (uses OpenAI API you already have).

---


## Test Set

Create `test_questions.json`:

```json
[
  {
    "question": "What is the income limit for a family of 3 in BCY 2026?",
    "expected_docs": ["bcy-26-income-eligibility"],
    "expected_answer_contains": ["$5,363", "family of 3"]
  },
  {
    "question": "How do I apply for child care assistance?",
    "expected_docs": ["parent", "guide", "application"],
    "expected_steps": ["workforce board", "documents", "apply"]
  }
]
```

### Evaluation Script

```python
# evaluate.py
import json
from chatbot import TexasChildcareChatbot

chatbot = TexasChildcareChatbot()

with open('test_questions.json') as f:
    tests = json.load(f)

correct = 0
for test in tests:
    response = chatbot.ask(test['question'])

    # Check if expected docs in sources
    source_filenames = [s['doc'].lower() for s in response['sources']]
    has_expected_doc = any(
        expected in ''.join(source_filenames)
        for expected in test.get('expected_docs', [])
    )

    # Check if answer contains key terms
    answer_lower = response['answer'].lower()
    has_expected_terms = all(
        term.lower() in answer_lower
        for term in test.get('expected_answer_contains', [])
    )

    if has_expected_doc and has_expected_terms:
        correct += 1
        print(f"✓ {test['question'][:50]}")
    else:
        print(f"✗ {test['question'][:50]}")

print(f"\nScore: {correct}/{len(tests)} ({100*correct/len(tests):.0f}%)")
```

**Target:** >70% for MVP, >85% for Phase 2

---

## Example: Complete MVP

Here's what a complete MVP looks like (all files):

### File 1: `chatbot/config.py`
```python
import os
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
COLLECTION_NAME = 'tro-child-1'
```

### File 2: `chatbot/retriever.py`
(See Component 1 above)

### File 3: `chatbot/reranker.py`
(See Component 2, Option A - LLM Judge Reranker)

### File 4: `chatbot/generator.py`
(See Component 3 above)

### File 5: `chatbot/chatbot.py`
(See Component 4 above)

### File 6: `test_chatbot.py`
(See Usage section above)

**Total:** ~200 lines of code for working RAG chatbot with reranking

---


## Prompt Engineering Tips

Your prompt quality matters more than architecture complexity.

**Good Prompt:**
```
You are an expert on Texas childcare assistance.

Answer using ONLY the provided documents. Cite sources as [Doc X].

Key rules:
- State income limits with exact amounts and year/BCY
- For application questions, list steps in order
- If info missing, say "I don't have information on..."
- Never make up numbers or dates

DOCUMENTS:
[context here]

QUESTION: [query here]

ANSWER with citations:
```

**Bad Prompt:**
```
Answer this question about Texas childcare: [query]

Context: [context]
```

Spend time on prompts. It's the highest-leverage work.

---

## Next Steps

1. **Build MVP with LLM Judge reranker** - 2-3 days
2. **Test with 10 questions** - 1 day
3. **If quality good (>70%):** Add 50 more test questions, refine prompt
4. **If quality poor (<70%):** Adjust retrieval parameters, add metadata filtering

---