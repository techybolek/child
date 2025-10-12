# Texas Childcare Chatbot - RAG Implementation Plan

**Project:** Texas State Childcare Resources Chatbot
**Vector Database:** Qdrant Cloud (Already Populated)
**Status:** Implementation Ready
**Date:** October 12, 2025

---

## Executive Summary

This document provides a production-ready RAG (Retrieval-Augmented Generation) architecture for a chatbot serving Texas childcare assistance queries. The system leverages an existing Qdrant vector database containing **3,722 semantic chunks** from **42 official PDF documents** (1,321 pages) covering policies, guidelines, eligibility requirements, and application processes.

**Key Design Principles:**
- **Robust over Naive**: Multi-stage retrieval with reranking, not simple similarity search
- **Production-Ready**: Guardrails, validation, monitoring, and fallback handling
- **User-Centric**: Context-aware responses with proper citations and progressive disclosure
- **Maintainable**: Modular architecture with centralized configuration

---

## 1. Current Infrastructure (Already Built)

### Qdrant Vector Database
```
Collection: tro-child-1
URL: Qdrant Cloud instance
Total Vectors: 3,722 chunks
Embedding Model: OpenAI text-embedding-3-small
Vector Dimensions: 1,536
Distance Metric: Cosine similarity
```

### Document Corpus
```
Source: 42 PDF documents
Total Pages: 1,321
Content Types:
  - Policy documents (CCDF state plans, regulations)
  - Legislative reports (effectiveness evaluations)
  - Parent guides (eligibility, rights, application)
  - Provider guides (payment rates, desk aids)
  - Board-specific data (payment rates by region)
  - Stakeholder input reports
```

### Chunking Configuration
```python
CHUNK_SIZE = 1000              # Characters per chunk
CHUNK_OVERLAP = 200            # 20% overlap for context continuity
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]  # Hierarchical splitting
```

### Metadata Structure (Already in Qdrant)
```json
{
  "text": "The chunk content...",
  "filename": "child-care-services-guide-twc.pdf",
  "content_type": "pdf",
  "source_url": "https://www.twc.texas.gov/files/...",
  "pdf_id": "abc123...",
  "file_size_mb": 2.4,
  "total_pages": 156,
  "page": 45,
  "chunk_index": 23,
  "total_chunks": 156
}
```

---

## 2. RAG Architecture Overview

### High-Level Pipeline
```
┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────────┐    ┌──────────┐
│ User Query  │───▶│ Query        │───▶│ Hybrid     │───▶│ Context      │───▶│ LLM      │
│             │    │ Processor    │    │ Retrieval  │    │ Assembly     │    │ Response │
└─────────────┘    └──────────────┘    └────────────┘    └──────────────┘    └──────────┘
                           │                   │                   │                 │
                           ▼                   ▼                   ▼                 ▼
                    ┌─────────────┐    ┌────────────┐    ┌──────────────┐   ┌──────────┐
                    │ Intent      │    │ Reranker   │    │ Deduplication│   │ Citation │
                    │ Classifier  │    │ (Cross-    │    │ & Merging    │   │ Validator│
                    └─────────────┘    │ Encoder)   │    └──────────────┘   └──────────┘
                                       └────────────┘
```

### Component Flow
1. **Query Processing**: Parse intent, extract entities, expand query
2. **Hybrid Retrieval**: Semantic search + metadata filtering
3. **Reranking**: Score and select most relevant chunks
4. **Context Assembly**: Merge, deduplicate, format with citations
5. **Generation**: LLM with structured prompts
6. **Validation**: Verify citations, check for hallucinations

---

## 3. Module Design & Implementation

### Directory Structure
```
TX/
├── config.py                          # [EXISTING] Configuration
├── load_pdf_qdrant.py                 # [EXISTING] DB loader
├── verify_qdrant.py                   # [EXISTING] Verification
│
├── chatbot/                           # [NEW] RAG Chatbot
│   ├── __init__.py
│   ├── config_rag.py                  # RAG-specific config
│   │
│   ├── core/                          # Core retrieval components
│   │   ├── __init__.py
│   │   ├── query_processor.py         # Query understanding
│   │   ├── retriever.py               # Hybrid retrieval engine
│   │   ├── reranker.py                # Cross-encoder reranking
│   │   └── context_manager.py         # Context assembly
│   │
│   ├── generation/                    # LLM generation
│   │   ├── __init__.py
│   │   ├── prompt_builder.py          # Dynamic prompt construction
│   │   ├── generator.py               # LLM API calls
│   │   └── validators.py              # Output validation
│   │
│   ├── memory/                        # Conversation management
│   │   ├── __init__.py
│   │   └── conversation_manager.py    # Session & history
│   │
│   ├── utils/                         # Utilities
│   │   ├── __init__.py
│   │   ├── logging_config.py          # Structured logging
│   │   └── metrics.py                 # Performance tracking
│   │
│   └── chatbot.py                     # Main chatbot orchestrator
│
├── evaluation/                        # [NEW] Testing & evaluation
│   ├── test_questions.json            # Curated test set
│   ├── evaluate.py                    # Offline evaluation
│   └── benchmark.py                   # Performance benchmarks
│
├── api/                               # [NEW] REST API (optional)
│   ├── main.py                        # FastAPI app
│   └── models.py                      # Request/response models
│
└── SPECS/
    └── rag_implementation_plan.md     # [THIS FILE]
```

---

## 4. Implementation Details by Component

### 4.1 Query Processor (`chatbot/core/query_processor.py`)

**Purpose**: Transform user queries into optimized retrieval queries

**Key Features:**
```python
class QueryProcessor:
    def process(self, query: str) -> ProcessedQuery:
        """
        Process user query into structured format

        Returns:
            ProcessedQuery with:
            - intent: QueryIntent enum
            - entities: Dict of extracted entities
            - expanded_query: Query with synonyms
            - metadata_filters: Qdrant filters
        """

    def classify_intent(self, query: str) -> QueryIntent:
        """
        Classify query intent using keyword patterns

        Intents:
        - ELIGIBILITY: Income limits, requirements, qualifications
        - APPLICATION: How to apply, steps, forms, timeline
        - PAYMENT_RATES: Provider rates, copay, reimbursement
        - CONTACT: Office locations, phone numbers, hours
        - POLICY: Regulations, rules, compliance
        - GENERAL: Everything else
        """

    def extract_entities(self, query: str) -> Dict:
        """
        Extract relevant entities using regex and NER

        Entities:
        - age_group: infant, toddler, preschool, school-age
        - location: board name, county, region
        - document_type: guide, policy, form, report
        - year: 2024, 2025, BCY25, BCY26, FFY2024
        - income: dollar amounts, percentages
        """

    def expand_query(self, query: str, intent: QueryIntent) -> str:
        """
        Expand query with domain-specific synonyms

        Examples:
        - "assistance" → "financial assistance OR subsidy OR CCDF"
        - "apply" → "application OR enrollment OR registration"
        - "daycare" → "child care OR childcare"
        """
```

**Intent Classification Rules:**
```python
INTENT_PATTERNS = {
    'ELIGIBILITY': [
        r'eligib(le|ility)',
        r'qualify|qualifications',
        r'income\s+(limit|requirement|threshold)',
        r'who\s+can\s+get',
        r'do\s+i\s+qualify',
    ],
    'APPLICATION': [
        r'how\s+to\s+apply',
        r'application\s+(process|steps)',
        r'apply\s+for',
        r'enroll(ment)?',
        r'sign\s+up',
        r'what\s+documents',
    ],
    'PAYMENT_RATES': [
        r'payment\s+rates?',
        r'how\s+much\s+(do|does)',
        r'copay',
        r'reimbursement',
        r'provider\s+payment',
        r'psoc\s+(rate|chart)',
    ],
    'CONTACT': [
        r'phone\s+number',
        r'office\s+(location|hours)',
        r'contact',
        r'who\s+do\s+i\s+call',
        r'where\s+is\s+the\s+office',
    ],
    'POLICY': [
        r'polic(y|ies)',
        r'regulation|rules?',
        r'requirement',
        r'law',
        r'state\s+plan',
    ],
}
```

**Entity Extraction:**
```python
ENTITY_PATTERNS = {
    'age_group': {
        r'infant': 'infant',
        r'toddler': 'toddler',
        r'preschool': 'preschool',
        r'school[- ]age': 'school-age',
    },
    'year': {
        r'BCY\s*2?0?2?5': 'bcy25',
        r'BCY\s*2?0?2?6': 'bcy26',
        r'20(24|25|26)': lambda m: f'20{m.group(1)}',
    },
    'board': {
        r'gulf\s+coast': 'Gulf Coast',
        r'capital\s+area': 'Capital Area',
        r'dallas': 'Dallas',
        # Add all 28 workforce boards
    },
}
```

---

### 4.2 Retriever (`chatbot/core/retriever.py`)

**Purpose**: Hybrid retrieval combining semantic search and metadata filtering

**Implementation:**
```python
class HybridRetriever:
    def __init__(self, qdrant_client, embeddings):
        self.client = qdrant_client
        self.embeddings = embeddings
        self.collection_name = config.QDRANT_COLLECTION_NAME

    def retrieve(
        self,
        processed_query: ProcessedQuery,
        top_k: int = 20
    ) -> List[RetrievedChunk]:
        """
        Hybrid retrieval with semantic search + filtering

        Strategy:
        1. Generate query embedding
        2. Apply metadata filters (if entities present)
        3. Semantic search in Qdrant
        4. Return top_k results
        """

        # Generate embedding
        query_vector = self.embeddings.embed_query(
            processed_query.expanded_query
        )

        # Build metadata filters
        filters = self._build_filters(processed_query.entities)

        # Search Qdrant
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=filters,
            limit=top_k,
            score_threshold=0.3  # Minimum relevance threshold
        )

        return [
            RetrievedChunk(
                text=hit.payload['text'],
                score=hit.score,
                metadata=hit.payload,
                chunk_id=hit.id
            )
            for hit in search_results
        ]

    def _build_filters(self, entities: Dict) -> Optional[models.Filter]:
        """
        Build Qdrant filters from extracted entities

        Examples:
        - If year='2025' → filter filename contains '2025'
        - If board='Gulf Coast' → filter text contains 'Gulf Coast'
        - If document_type='eligibility' → filter filename contains 'eligibility'
        """
        conditions = []

        if 'year' in entities:
            year = entities['year']
            conditions.append(
                models.FieldCondition(
                    key="filename",
                    match=models.MatchText(text=year)
                )
            )

        if 'document_type' in entities:
            doc_type = entities['document_type']
            conditions.append(
                models.FieldCondition(
                    key="filename",
                    match=models.MatchText(text=doc_type)
                )
            )

        if not conditions:
            return None

        return models.Filter(
            must=conditions
        )
```

**Metadata Filter Examples:**
```python
# Example 1: "What are 2025 eligibility requirements?"
filters = Filter(
    must=[
        FieldCondition(key="filename", match=MatchText(text="2025")),
        FieldCondition(key="filename", match=MatchText(text="eligibility"))
    ]
)

# Example 2: "BCY26 payment rates"
filters = Filter(
    must=[
        FieldCondition(key="filename", match=MatchText(text="bcy26"))
    ]
)

# Example 3: "Texas Rising Star requirements"
filters = Filter(
    must=[
        FieldCondition(key="text", match=MatchText(text="Texas Rising Star"))
    ]
)
```

---

### 4.3 Reranker (`chatbot/core/reranker.py`)

**Purpose**: Rerank retrieved chunks using cross-encoder for better relevance

**Implementation Options:**

**Option A: Cohere Rerank API (Recommended)**
```python
import cohere

class CohereReranker:
    def __init__(self, api_key: str):
        self.client = cohere.Client(api_key)

    def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_k: int = 7
    ) -> List[RetrievedChunk]:
        """
        Rerank using Cohere API

        Advantages:
        - State-of-the-art relevance scoring
        - Fast API (< 200ms for 20 chunks)
        - No local model loading

        Cost: ~$0.002 per 1000 searches
        """

        documents = [chunk.text for chunk in chunks]

        results = self.client.rerank(
            query=query,
            documents=documents,
            top_n=top_k,
            model='rerank-english-v2.0'
        )

        # Map back to chunks with new scores
        reranked = []
        for result in results.results:
            chunk = chunks[result.index]
            chunk.rerank_score = result.relevance_score
            reranked.append(chunk)

        return reranked
```

**Option B: Local Cross-Encoder (Alternative)**
```python
from sentence_transformers import CrossEncoder

class LocalReranker:
    def __init__(self):
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_k: int = 7
    ) -> List[RetrievedChunk]:
        """
        Rerank using local cross-encoder model

        Advantages:
        - No API costs
        - Privacy (runs locally)

        Disadvantages:
        - Slower (~500ms for 20 chunks)
        - Requires model download (80MB)
        """

        pairs = [(query, chunk.text) for chunk in chunks]
        scores = self.model.predict(pairs)

        # Sort by score
        scored_chunks = list(zip(chunks, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Update scores and return top_k
        reranked = []
        for chunk, score in scored_chunks[:top_k]:
            chunk.rerank_score = float(score)
            reranked.append(chunk)

        return reranked
```

**Recommendation**: Use Cohere for production (better quality, faster), fallback to local for development/testing.

---

### 4.4 Context Manager (`chatbot/core/context_manager.py`)

**Purpose**: Assemble optimal context for LLM from retrieved chunks

**Key Features:**
```python
class ContextManager:
    def __init__(self, max_tokens: int = 6000):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

    def assemble_context(
        self,
        chunks: List[RetrievedChunk],
        processed_query: ProcessedQuery
    ) -> AssembledContext:
        """
        Assemble context with:
        1. Deduplication (remove similar chunks)
        2. Chunk merging (consecutive chunks from same doc)
        3. Prioritization (higher scores first)
        4. Token budget management
        5. Citation formatting
        """

        # 1. Deduplicate
        unique_chunks = self._deduplicate(chunks, threshold=0.95)

        # 2. Merge consecutive chunks
        merged_chunks = self._merge_consecutive(unique_chunks)

        # 3. Prioritize by intent
        prioritized = self._prioritize_by_intent(
            merged_chunks,
            processed_query.intent
        )

        # 4. Fit to token budget
        context_chunks = self._fit_to_budget(prioritized)

        # 5. Format with citations
        formatted_context = self._format_with_citations(context_chunks)

        return AssembledContext(
            text=formatted_context,
            chunks=context_chunks,
            total_tokens=self._count_tokens(formatted_context),
            citation_map=self._build_citation_map(context_chunks)
        )

    def _deduplicate(
        self,
        chunks: List[RetrievedChunk],
        threshold: float = 0.95
    ) -> List[RetrievedChunk]:
        """
        Remove near-duplicate chunks using cosine similarity

        Strategy:
        - Compare each chunk text embedding
        - If similarity > threshold, keep only higher-scored chunk
        """
        unique = []
        for chunk in chunks:
            is_duplicate = False
            for existing in unique:
                similarity = self._compute_similarity(chunk.text, existing.text)
                if similarity > threshold:
                    # Keep higher score
                    if chunk.rerank_score > existing.rerank_score:
                        unique.remove(existing)
                        unique.append(chunk)
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(chunk)
        return unique

    def _merge_consecutive(
        self,
        chunks: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        """
        Merge chunks that are consecutive pages from same document

        Example:
        Chunk 1: filename='guide.pdf', page=12, chunk_index=45
        Chunk 2: filename='guide.pdf', page=13, chunk_index=46
        → Merge into single context block
        """
        merged = []
        i = 0
        while i < len(chunks):
            current = chunks[i]
            merge_group = [current]

            # Look for consecutive chunks
            j = i + 1
            while j < len(chunks):
                next_chunk = chunks[j]
                if self._are_consecutive(current, next_chunk):
                    merge_group.append(next_chunk)
                    j += 1
                else:
                    break

            # Create merged chunk
            if len(merge_group) > 1:
                merged_chunk = self._create_merged_chunk(merge_group)
                merged.append(merged_chunk)
                i = j
            else:
                merged.append(current)
                i += 1

        return merged

    def _prioritize_by_intent(
        self,
        chunks: List[RetrievedChunk],
        intent: QueryIntent
    ) -> List[RetrievedChunk]:
        """
        Boost priority of certain document types based on query intent

        Rules:
        - ELIGIBILITY intent → Boost "eligibility", "income", "requirements" docs
        - APPLICATION intent → Boost "application", "guide", "parent" docs
        - PAYMENT_RATES intent → Boost "payment", "rates", "bcy", "psoc" docs
        - POLICY intent → Boost "state-plan", "regulation", "policy" docs
        """

        priority_keywords = INTENT_PRIORITY_MAP.get(intent, [])

        for chunk in chunks:
            filename = chunk.metadata.get('filename', '').lower()
            # Boost score if filename matches priority keywords
            for keyword in priority_keywords:
                if keyword in filename:
                    chunk.priority_boost = 1.2
                    break

        # Sort by boosted score
        chunks.sort(
            key=lambda c: c.rerank_score * getattr(c, 'priority_boost', 1.0),
            reverse=True
        )

        return chunks

    def _format_with_citations(
        self,
        chunks: List[RetrievedChunk]
    ) -> str:
        """
        Format context with numbered citations

        Output format:
        ---
        [Document 1: child-care-eligibility-2025.pdf, Page 12]
        To be eligible for child care assistance, families must meet income
        requirements. The maximum income is 85% of state median income...

        [Document 2: bcy26-income-limits.pdf, Page 3]
        For BCY 2026, the income limits are as follows:
        - Family of 2: $4,250/month
        - Family of 3: $5,363/month
        ...
        ---
        """

        formatted_parts = []
        for i, chunk in enumerate(chunks, 1):
            citation = self._format_citation(chunk, i)
            formatted_parts.append(f"{citation}\n{chunk.text}\n")

        return "\n".join(formatted_parts)

    def _format_citation(self, chunk: RetrievedChunk, index: int) -> str:
        """Format citation header"""
        filename = chunk.metadata.get('filename', 'Unknown')
        page = chunk.metadata.get('page', 'N/A')
        return f"[Document {index}: {filename}, Page {page}]"
```

**Priority Keywords by Intent:**
```python
INTENT_PRIORITY_MAP = {
    QueryIntent.ELIGIBILITY: [
        'eligibility', 'income', 'requirements', 'qualify',
        'state-plan', 'ccdf'
    ],
    QueryIntent.APPLICATION: [
        'application', 'guide', 'parent', 'how-to',
        'enrollment', 'register'
    ],
    QueryIntent.PAYMENT_RATES: [
        'payment', 'rates', 'bcy', 'psoc', 'reimbursement',
        'copay', 'provider'
    ],
    QueryIntent.CONTACT: [
        'contact', 'office', 'phone', 'location',
        'board', 'workforce'
    ],
    QueryIntent.POLICY: [
        'state-plan', 'policy', 'regulation', 'rule',
        'compliance', 'ccdf'
    ],
}
```

---

### 4.5 Prompt Builder (`chatbot/generation/prompt_builder.py`)

**Purpose**: Build dynamic, intent-specific prompts with context

**System Prompt Template:**
```python
SYSTEM_PROMPT_TEMPLATE = """You are an expert assistant for the Texas Workforce Commission's child care assistance program. Your role is to help parents, providers, and workforce board staff understand eligibility, application processes, payment rates, and policies.

## Core Guidelines

1. ACCURACY: Only provide information explicitly stated in the provided documents
2. CITATIONS: Always cite sources using [Document X] format
3. CLARITY: Use simple, jargy-free language
4. EMPATHY: Be warm and supportive - families are often stressed
5. COMPLETENESS: If information is missing, say so and suggest next steps

## Response Format

- Start with a direct answer to the question
- Provide supporting details with citations
- Include relevant examples or calculations if applicable
- End with actionable next steps (if appropriate)
- Always cite the specific document and page number

## What NOT to do

- Never make up numbers, dates, or requirements
- Never provide legal advice
- Never discuss individual cases or PII
- Never contradict official policy documents
- If unsure, say "I don't have information on..." and suggest contacting TWC

## Intent-Specific Instructions

{intent_instructions}

## Context Documents

The following documents are relevant to the user's question. Use ONLY this information to answer.

{context}

## User Question

{question}

## Your Response

Provide a helpful, accurate response with citations:
"""

INTENT_SPECIFIC_INSTRUCTIONS = {
    QueryIntent.ELIGIBILITY: """
### Eligibility Questions

When answering eligibility questions:
1. State the basic requirements clearly
2. Provide specific income limits (with year/BCY)
3. Explain any special categories (TANF, CPS, etc.)
4. Note any geographic variations if relevant
5. Cite the exact regulation or policy

Example structure:
"To qualify for child care assistance in Texas, you must meet these requirements [Document X, Page Y]:
1. Income at or below 85% of State Median Income
2. ...

For a family of 3 in BCY 2026, the monthly income limit is $5,363 [Document Z, Page N]."
""",

    QueryIntent.APPLICATION: """
### Application Process Questions

When explaining the application process:
1. List steps in chronological order
2. Identify required documents
3. Explain where/how to apply
4. Provide realistic timeline expectations
5. Mention waitlist if applicable

Example structure:
"To apply for child care assistance [Document X, Page Y]:

Step 1: Gather required documents:
- Proof of income (last 4 pay stubs)
- ...

Step 2: Contact your local workforce board...

Timeline: Applications are typically processed within 30 days [Document Z]."
""",

    QueryIntent.PAYMENT_RATES: """
### Payment Rate Questions

When providing payment rates:
1. Specify the exact BCY (Board Contract Year)
2. Break down by age group if applicable
3. Note that rates vary by workforce board
4. Explain copay requirements if relevant
5. Cite the official rate chart

Example structure:
"For BCY 2026, the maximum provider payment rates [Document X, Page Y]:

Full-time care:
- Infant (0-17 months): $XXX/week
- Toddler (18-35 months): $XXX/week
...

Note: These are maximum rates. Actual rates may vary by workforce board and provider type."
""",
}
```

**Prompt Building:**
```python
class PromptBuilder:
    def build_prompt(
        self,
        processed_query: ProcessedQuery,
        assembled_context: AssembledContext,
        conversation_history: Optional[List[Message]] = None
    ) -> str:
        """
        Build complete prompt with:
        - System instructions
        - Intent-specific guidance
        - Context documents
        - Conversation history (if any)
        - Current question
        """

        # Get intent-specific instructions
        intent_instructions = INTENT_SPECIFIC_INSTRUCTIONS.get(
            processed_query.intent,
            ""
        )

        # Build conversation history section (if exists)
        history_section = ""
        if conversation_history:
            history_section = self._format_history(conversation_history)

        # Fill template
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            intent_instructions=intent_instructions,
            context=assembled_context.text,
            question=processed_query.original_query
        )

        # Add history if present
        if history_section:
            prompt = prompt.replace(
                "## User Question",
                f"## Conversation History\n\n{history_section}\n\n## User Question"
            )

        return prompt
```

---

### 4.6 Generator (`chatbot/generation/generator.py`)

**Purpose**: Generate responses using OpenAI API

**Implementation:**
```python
from openai import OpenAI

class ResponseGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(
        self,
        prompt: str,
        temperature: float = 0.1,  # Low temp for factual accuracy
        max_tokens: int = 1000,
        stream: bool = False
    ) -> GeneratedResponse:
        """
        Generate response from LLM

        Args:
            prompt: Complete prompt with system + context + question
            temperature: Lower = more deterministic (0.1 recommended)
            max_tokens: Max response length
            stream: Whether to stream response
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )

            if stream:
                return self._handle_stream(response)
            else:
                return GeneratedResponse(
                    text=response.choices[0].message.content,
                    finish_reason=response.choices[0].finish_reason,
                    usage=response.usage,
                    model=self.model
                )

        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise GenerationError(f"Failed to generate response: {e}")

    def _handle_stream(self, stream):
        """Handle streaming response"""
        full_text = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_text += content
                yield content

        return GeneratedResponse(text=full_text, model=self.model)
```

**Model Selection:**
```python
# Production models (ranked by quality)
MODELS = {
    'best': 'gpt-4-turbo-preview',      # Best quality, slower, $$$
    'balanced': 'gpt-4-0613',            # Good quality, moderate speed, $$
    'fast': 'gpt-3.5-turbo',             # Fast, cheaper, but less accurate
}

# Recommended: gpt-4-turbo-preview for accuracy-critical domain
```

---

### 4.7 Validators (`chatbot/generation/validators.py`)

**Purpose**: Validate generated responses for quality and safety

**Citation Validator:**
```python
class CitationValidator:
    def validate(
        self,
        response: str,
        context: AssembledContext
    ) -> ValidationResult:
        """
        Verify all factual claims have citations

        Checks:
        1. Numbers have citations (income limits, rates, dates)
        2. Policy statements have citations
        3. All [Document X] references are valid
        4. No hallucinated documents
        """

        issues = []

        # Extract all citations mentioned in response
        citation_pattern = r'\[Document (\d+)\]'
        mentioned_citations = set(re.findall(citation_pattern, response))

        # Check citations are valid
        valid_citations = set(str(i) for i in range(1, len(context.chunks) + 1))
        invalid = mentioned_citations - valid_citations
        if invalid:
            issues.append(f"Invalid citations: {invalid}")

        # Check numbers have citations
        number_pattern = r'\$[\d,]+|\d+%|\d{4}'  # Money, percentages, years
        numbers = re.findall(number_pattern, response)
        if numbers:
            # Check if nearby citation exists (within 100 chars)
            for number in numbers:
                pos = response.find(number)
                nearby = response[max(0, pos-100):pos+100]
                if '[Document' not in nearby:
                    issues.append(f"Uncited number: {number}")

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )
```

**Hallucination Detector:**
```python
class HallucinationDetector:
    def detect(
        self,
        response: str,
        context: AssembledContext
    ) -> DetectionResult:
        """
        Detect potential hallucinations

        Methods:
        1. Entailment checking (does context support claim?)
        2. Keyword presence (are key terms from response in context?)
        3. Numeric consistency (do numbers match context?)
        """

        hallucinations = []

        # 1. Extract claims from response
        claims = self._extract_claims(response)

        # 2. Check each claim against context
        for claim in claims:
            if not self._is_supported(claim, context.text):
                hallucinations.append(claim)

        # 3. Check numeric values
        response_numbers = self._extract_numbers(response)
        context_numbers = self._extract_numbers(context.text)

        for num in response_numbers:
            if num not in context_numbers:
                hallucinations.append(f"Number not in context: {num}")

        return DetectionResult(
            has_hallucinations=len(hallucinations) > 0,
            hallucinations=hallucinations,
            confidence=self._calculate_confidence(hallucinations)
        )

    def _is_supported(self, claim: str, context: str) -> bool:
        """
        Check if claim is supported by context

        Simple approach: Keyword overlap > 50%
        Advanced: Use entailment model (RoBERTa-NLI)
        """
        claim_keywords = set(claim.lower().split())
        context_keywords = set(context.lower().split())

        overlap = len(claim_keywords & context_keywords)
        return overlap / len(claim_keywords) > 0.5
```

**Policy Compliance Checker:**
```python
class PolicyComplianceChecker:
    def check(self, response: str) -> ComplianceResult:
        """
        Check response complies with policies

        Checks:
        1. No discussion of waitlist priority manipulation
        2. No legal advice
        3. No discussion of individual cases
        4. No contradictions with official policy
        5. Appropriate disclaimers for time-sensitive info
        """

        violations = []

        # Check for prohibited topics
        if self._discusses_waitlist_manipulation(response):
            violations.append("Discusses waitlist manipulation")

        if self._provides_legal_advice(response):
            violations.append("Provides legal advice")

        # Check for required disclaimers
        if self._mentions_rates(response):
            if "rates may vary" not in response.lower():
                violations.append("Missing rate variation disclaimer")

        return ComplianceResult(
            is_compliant=len(violations) == 0,
            violations=violations
        )
```

---

### 4.8 Conversation Manager (`chatbot/memory/conversation_manager.py`)

**Purpose**: Manage conversation history and context

**Implementation:**
```python
from typing import List, Optional
from datetime import datetime, timedelta

class ConversationManager:
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions = {}  # session_id -> Session
        self.timeout = timedelta(minutes=session_timeout_minutes)

    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one"""
        if session_id in self.sessions:
            session = self.sessions[session_id]

            # Check if session expired
            if datetime.now() - session.last_activity > self.timeout:
                # Reset session
                session = Session(session_id)
                self.sessions[session_id] = session
        else:
            session = Session(session_id)
            self.sessions[session_id] = session

        return session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ):
        """Add message to conversation history"""
        session = self.get_or_create_session(session_id)
        session.add_message(role, content, metadata)
        session.last_activity = datetime.now()

    def get_recent_history(
        self,
        session_id: str,
        max_turns: int = 3
    ) -> List[Message]:
        """Get recent conversation history for context"""
        session = self.get_or_create_session(session_id)
        return session.get_recent_messages(max_turns)

    def clear_session(self, session_id: str):
        """Clear session history"""
        if session_id in self.sessions:
            del self.sessions[session_id]

class Session:
    def __init__(self, session_id: str):
        self.id = session_id
        self.messages = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

    def add_message(self, role: str, content: str, metadata: dict = None):
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.messages.append(message)

    def get_recent_messages(self, max_turns: int = 3) -> List[Message]:
        """Get last N turns (user + assistant pairs)"""
        return self.messages[-(max_turns * 2):]
```

---

## 5. Main Chatbot Orchestrator (`chatbot/chatbot.py`)

**Purpose**: Coordinate all components to handle user queries

**Implementation:**
```python
class TexasChildcareChatbot:
    def __init__(self, config: RAGConfig):
        # Initialize components
        self.query_processor = QueryProcessor()
        self.retriever = HybridRetriever(
            qdrant_client=self._init_qdrant(),
            embeddings=self._init_embeddings()
        )
        self.reranker = CohereReranker(config.cohere_api_key)
        self.context_manager = ContextManager(max_tokens=6000)
        self.prompt_builder = PromptBuilder()
        self.generator = ResponseGenerator(
            api_key=config.openai_api_key,
            model=config.llm_model
        )
        self.validators = {
            'citation': CitationValidator(),
            'hallucination': HallucinationDetector(),
            'compliance': PolicyComplianceChecker()
        }
        self.conversation_manager = ConversationManager()

    def chat(
        self,
        user_query: str,
        session_id: str,
        stream: bool = False
    ) -> ChatResponse:
        """
        Main chat method - orchestrates entire RAG pipeline

        Pipeline:
        1. Process query
        2. Retrieve relevant chunks
        3. Rerank chunks
        4. Assemble context
        5. Build prompt
        6. Generate response
        7. Validate response
        8. Update conversation history
        """

        start_time = time.time()

        try:
            # Step 1: Process query
            logger.info(f"Processing query: {user_query}")
            processed_query = self.query_processor.process(user_query)
            logger.info(f"Intent: {processed_query.intent}")

            # Step 2: Retrieve chunks
            logger.info("Retrieving relevant chunks...")
            retrieved_chunks = self.retriever.retrieve(
                processed_query,
                top_k=20
            )
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

            # Check if we have relevant results
            if not retrieved_chunks:
                return self._handle_no_results(user_query, session_id)

            # Step 3: Rerank
            logger.info("Reranking chunks...")
            reranked_chunks = self.reranker.rerank(
                query=user_query,
                chunks=retrieved_chunks,
                top_k=7
            )
            logger.info(f"Selected top {len(reranked_chunks)} chunks")

            # Step 4: Assemble context
            logger.info("Assembling context...")
            assembled_context = self.context_manager.assemble_context(
                chunks=reranked_chunks,
                processed_query=processed_query
            )
            logger.info(f"Context: {assembled_context.total_tokens} tokens")

            # Step 5: Build prompt
            conversation_history = self.conversation_manager.get_recent_history(
                session_id,
                max_turns=3
            )
            prompt = self.prompt_builder.build_prompt(
                processed_query=processed_query,
                assembled_context=assembled_context,
                conversation_history=conversation_history
            )

            # Step 6: Generate response
            logger.info("Generating response...")
            generated_response = self.generator.generate(
                prompt=prompt,
                stream=stream
            )

            # Step 7: Validate response
            validation_results = self._validate_response(
                generated_response.text,
                assembled_context
            )

            if not validation_results['citation'].is_valid:
                logger.warning(f"Citation issues: {validation_results['citation'].issues}")

            # Step 8: Update conversation history
            self.conversation_manager.add_message(
                session_id=session_id,
                role="user",
                content=user_query
            )
            self.conversation_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=generated_response.text,
                metadata={
                    'intent': processed_query.intent.value,
                    'sources': [c.metadata for c in reranked_chunks]
                }
            )

            # Build response
            response_time = time.time() - start_time

            return ChatResponse(
                answer=generated_response.text,
                sources=self._format_sources(reranked_chunks),
                intent=processed_query.intent,
                confidence=self._calculate_confidence(reranked_chunks),
                validation_results=validation_results,
                response_time_seconds=response_time,
                session_id=session_id
            )

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return self._handle_error(user_query, session_id, e)

    def _validate_response(
        self,
        response: str,
        context: AssembledContext
    ) -> dict:
        """Run all validators"""
        return {
            'citation': self.validators['citation'].validate(response, context),
            'hallucination': self.validators['hallucination'].detect(response, context),
            'compliance': self.validators['compliance'].check(response)
        }

    def _format_sources(self, chunks: List[RetrievedChunk]) -> List[dict]:
        """Format source citations for response"""
        return [
            {
                'document': chunk.metadata.get('filename'),
                'page': chunk.metadata.get('page'),
                'score': chunk.rerank_score,
                'url': chunk.metadata.get('source_url', '')
            }
            for chunk in chunks
        ]

    def _handle_no_results(self, query: str, session_id: str) -> ChatResponse:
        """Handle case when no relevant documents found"""
        fallback_response = (
            "I couldn't find specific information about that in my current documents. "
            "For the most accurate and up-to-date information, I recommend:\n\n"
            "1. Contacting your local Texas Workforce Board\n"
            "2. Calling the TWC Child Care Services hotline: 1-800-862-5252\n"
            "3. Visiting: https://childcare.twc.texas.gov/\n\n"
            "Is there anything else I can help you with?"
        )

        return ChatResponse(
            answer=fallback_response,
            sources=[],
            intent=QueryIntent.GENERAL,
            confidence=0.0,
            validation_results={},
            session_id=session_id
        )
```

---

## 6. Configuration (`chatbot/config_rag.py`)

**Centralized RAG configuration:**
```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class RAGConfig:
    # API Keys
    openai_api_key: str = os.getenv('OPENAI_API_KEY')
    qdrant_api_url: str = os.getenv('QDRANT_API_URL')
    qdrant_api_key: str = os.getenv('QDRANT_API_KEY')
    cohere_api_key: Optional[str] = os.getenv('COHERE_API_KEY')  # Optional

    # Qdrant settings
    collection_name: str = 'tro-child-1'
    embedding_model: str = 'text-embedding-3-small'

    # Retrieval settings
    retrieval_top_k: int = 20
    rerank_top_k: int = 7
    min_retrieval_score: float = 0.3

    # Context settings
    max_context_tokens: int = 6000
    chunk_merge_threshold: float = 0.95  # Similarity threshold for dedup

    # Generation settings
    llm_model: str = 'gpt-4-turbo-preview'  # or 'gpt-4-0613', 'gpt-3.5-turbo'
    temperature: float = 0.1  # Low for factual accuracy
    max_response_tokens: int = 1000

    # Conversation settings
    session_timeout_minutes: int = 30
    max_history_turns: int = 3

    # Validation settings
    enable_citation_validation: bool = True
    enable_hallucination_detection: bool = True
    enable_compliance_check: bool = True

    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour

    # Logging
    log_level: str = 'INFO'
    log_file: str = 'chatbot/logs/chatbot.log'

# Create default config
default_config = RAGConfig()
```

---

## 7. Usage Examples

### Basic Usage
```python
from chatbot import TexasChildcareChatbot
from chatbot.config_rag import default_config

# Initialize chatbot
chatbot = TexasChildcareChatbot(default_config)

# Single query
response = chatbot.chat(
    user_query="What are the income limits for a family of 3?",
    session_id="user-123"
)

print(response.answer)
print("\nSources:")
for source in response.sources:
    print(f"- {source['document']}, Page {source['page']}")
```

### Streaming Response
```python
response = chatbot.chat(
    user_query="How do I apply for child care assistance?",
    session_id="user-123",
    stream=True
)

# Stream response chunks
for chunk in response.answer:
    print(chunk, end='', flush=True)
```

### Conversation
```python
session_id = "user-123"

# First question
response1 = chatbot.chat(
    "What is Texas Rising Star?",
    session_id=session_id
)

# Follow-up question (uses conversation history)
response2 = chatbot.chat(
    "How do providers get certified?",
    session_id=session_id
)
```

---

## 8. Evaluation Strategy

### Offline Evaluation (Pre-Launch)

**Test Set Creation:**
```json
{
  "test_questions": [
    {
      "id": 1,
      "question": "What is the income limit for a family of 3 in BCY 2026?",
      "intent": "ELIGIBILITY",
      "expected_answer": "For BCY 2026, the monthly income limit for a family of 3 is $5,363.",
      "required_sources": ["bcy-26-income-eligibility-and-maximum-psoc-twc.pdf"],
      "critical_numbers": ["$5,363", "family of 3", "BCY 2026"]
    },
    {
      "id": 2,
      "question": "How do I apply for child care assistance?",
      "intent": "APPLICATION",
      "expected_steps": [
        "Contact local workforce board",
        "Gather required documents",
        "Submit application",
        "Wait for determination"
      ]
    }
  ]
}
```

**Evaluation Script:**
```python
from evaluation import RAGEvaluator

evaluator = RAGEvaluator(chatbot, test_set='evaluation/test_questions.json')

results = evaluator.evaluate()

print(f"Retrieval Recall@5: {results.retrieval_recall}")
print(f"Citation Accuracy: {results.citation_accuracy}")
print(f"Factual Correctness: {results.factual_correctness}")
print(f"Response Quality: {results.response_quality}")
```

**Metrics:**
- **Retrieval Recall@k**: % of questions where correct document is in top-k
- **Citation Accuracy**: % of responses with correct citations
- **Factual Correctness**: % of responses factually accurate (human eval)
- **Response Quality**: Human rating 1-5 for helpfulness

**Target Metrics:**
- Retrieval Recall@5: > 85%
- Citation Accuracy: > 95%
- Factual Correctness: > 90%
- Response Quality: > 4.0/5.0

---

## 9. Deployment Options

### Option A: REST API (Recommended)
```python
# api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Texas Childcare Chatbot API")

chatbot = TexasChildcareChatbot(default_config)

class ChatRequest(BaseModel):
    query: str
    session_id: str
    stream: bool = False

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    intent: str
    confidence: float
    response_time: float

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = chatbot.chat(
            user_query=request.query,
            session_id=request.session_id,
            stream=request.stream
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run: uvicorn api.main:app --reload
```

### Option B: Streamlit Interface
```python
# app.py
import streamlit as st
from chatbot import TexasChildcareChatbot

st.title("Texas Childcare Assistant")

# Initialize chatbot
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = TexasChildcareChatbot(default_config)
    st.session_state.messages = []

# Display conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Ask about Texas childcare assistance"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get response
    response = st.session_state.chatbot.chat(
        user_query=prompt,
        session_id=st.session_state.get('session_id', 'default')
    )

    # Add assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": response.answer
    })

    # Show sources in sidebar
    with st.sidebar:
        st.subheader("Sources")
        for source in response.sources:
            st.caption(f"{source['document']}, Page {source['page']}")

# Run: streamlit run app.py
```

---

## 10. Monitoring & Observability

### Key Metrics to Track
```python
# chatbot/utils/metrics.py

class MetricsCollector:
    def track_query(self, query_data: dict):
        """
        Track query metrics:
        - Query text
        - Intent classification
        - Retrieval scores
        - Rerank scores
        - Generation time
        - Total response time
        - Validation results
        """

    def track_user_feedback(self, feedback: dict):
        """
        Track user feedback:
        - Thumbs up/down
        - Specific issue reports
        - Session ID for analysis
        """

    def generate_dashboard_data(self):
        """
        Generate data for monitoring dashboard:
        - Queries per hour/day
        - Intent distribution
        - Average response time
        - Error rate
        - Low-confidence queries
        - User satisfaction score
        """
```

### Logging Structure
```python
# Structured JSON logging
{
  "timestamp": "2025-10-12T10:30:45Z",
  "session_id": "user-123",
  "query": "What are BCY 2026 rates?",
  "intent": "PAYMENT_RATES",
  "retrieval": {
    "top_k": 20,
    "chunks_retrieved": 18,
    "avg_score": 0.72
  },
  "reranking": {
    "top_k": 7,
    "avg_score": 0.85
  },
  "generation": {
    "model": "gpt-4-turbo-preview",
    "tokens_used": 1243,
    "time_ms": 2340
  },
  "validation": {
    "citation_valid": true,
    "hallucination_detected": false,
    "compliance_passed": true
  },
  "total_time_ms": 3120
}
```

---

## 11. Next Steps & Phased Implementation

### Phase 1: MVP (Week 1-2)
**Goal:** Basic working RAG chatbot

Tasks:
1. Set up project structure
2. Implement core components:
   - Query Processor (basic intent classification)
   - Retriever (semantic search only)
   - Context Manager (basic assembly)
   - Prompt Builder (simple prompts)
   - Generator (OpenAI API)
3. Build simple CLI interface
4. Test with 10 sample questions

**Success Criteria:**
- Answers 8/10 test questions correctly
- Response time < 10 seconds
- All responses have citations

---

### Phase 2: Robust RAG (Week 3-4)
**Goal:** Add advanced retrieval and validation

Tasks:
1. Implement reranker (Cohere API)
2. Add metadata filtering
3. Implement validators (citation, hallucination, compliance)
4. Add conversation memory
5. Create evaluation framework
6. Test with 50 questions

**Success Criteria:**
- Retrieval recall@5 > 85%
- Citation accuracy > 95%
- Response time < 5 seconds

---

### Phase 3: Production Ready (Week 5-6)
**Goal:** Production hardening and deployment

Tasks:
1. Build REST API (FastAPI)
2. Add caching layer (Redis)
3. Implement monitoring and logging
4. Create Streamlit interface
5. Write documentation
6. Deploy to staging environment
7. User acceptance testing

**Success Criteria:**
- 99% uptime
- Response time p95 < 5 seconds
- User satisfaction > 4.0/5.0

---

### Phase 4: Optimization (Ongoing)
**Goal:** Continuous improvement

Tasks:
1. Analyze failed queries
2. A/B test prompt variations
3. Fine-tune retrieval parameters
4. Add new document types
5. Improve conversation handling
6. Expand test coverage

---

## 12. Cost Estimation

### Per-Query Costs

**Embeddings (Query):**
- Model: text-embedding-3-small
- Cost: ~$0.00002 per query
- Volume: 1,000 queries/day = $0.02/day

**Reranking (Cohere):**
- Cost: ~$0.002 per search (20 chunks)
- Volume: 1,000 queries/day = $2.00/day

**Generation (OpenAI GPT-4):**
- Input: ~7,000 tokens (context + prompt)
- Output: ~500 tokens (response)
- Cost: ~$0.15 per query
- Volume: 1,000 queries/day = $150/day

**Total: ~$152/day or ~$4,560/month** (1,000 queries/day)

### Cost Optimization Strategies
1. **Caching**: Cache common questions → 30% cost reduction
2. **GPT-3.5 for simple queries**: → 90% cost reduction on those queries
3. **Local reranker**: Eliminate Cohere costs → $2/day savings
4. **Batch processing**: Process multiple queries in parallel

**Optimized Cost: ~$85/day or ~$2,550/month**

---

## 13. Dependencies Update

**Add to `requirements.txt`:**
```txt
# RAG Chatbot dependencies

# Reranking
cohere>=4.0.0                   # Cohere Rerank API (optional)
sentence-transformers>=2.2.0    # Local cross-encoder (alternative)

# API framework (optional)
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0

# Monitoring
tiktoken>=0.5.0                 # Token counting
redis>=5.0.0                    # Caching (optional)

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0

# UI (optional)
streamlit>=1.28.0
```

---

## 14. Key Success Factors

### Technical Excellence
1. **High retrieval quality**: Hybrid search + reranking ensures relevant results
2. **Accurate citations**: Every claim traced to source document
3. **Validation layers**: Multiple checks prevent hallucinations
4. **Fast response times**: < 5 seconds for 95% of queries

### User Experience
1. **Empathetic tone**: Warm, supportive language for stressed families
2. **Clear answers**: Direct, jargon-free explanations
3. **Actionable next steps**: Guidance on what to do next
4. **Conversation continuity**: Remembers context across turns

### Operational Reliability
1. **Error handling**: Graceful fallbacks for failures
2. **Monitoring**: Track performance and issues proactively
3. **Evaluation**: Continuous testing and improvement
4. **Cost efficiency**: Optimize API usage without sacrificing quality

---

## 15. Conclusion

This implementation plan provides a **production-ready, robust RAG architecture** for the Texas Childcare chatbot, leveraging your existing Qdrant database with 3,722 semantic chunks.

**Key Differentiators:**
- Multi-stage retrieval (semantic + reranking)
- Intent-aware processing
- Comprehensive validation
- Conversation memory
- Production monitoring

**Implementation Timeline:** 6 weeks to production deployment

**Expected Performance:**
- Accuracy: > 90%
- Response time: < 5 seconds
- User satisfaction: > 4.0/5.0
- Cost: ~$2,550/month (1,000 queries/day)

**Next Action:** Begin Phase 1 implementation, starting with core components.

---

## Appendix: File Checklist

### Files to Create
```
✅ chatbot/config_rag.py
✅ chatbot/core/query_processor.py
✅ chatbot/core/retriever.py
✅ chatbot/core/reranker.py
✅ chatbot/core/context_manager.py
✅ chatbot/generation/prompt_builder.py
✅ chatbot/generation/generator.py
✅ chatbot/generation/validators.py
✅ chatbot/memory/conversation_manager.py
✅ chatbot/chatbot.py
✅ evaluation/test_questions.json
✅ evaluation/evaluate.py
✅ api/main.py (optional)
✅ app.py (optional Streamlit)
```

### Existing Files (Keep)
```
✓ config.py
✓ load_pdf_qdrant.py
✓ verify_qdrant.py
✓ requirements.txt (update)
```

---

**Document Status:** Complete and Ready for Implementation
**Author:** TX Project Team
**Last Updated:** October 12, 2025
