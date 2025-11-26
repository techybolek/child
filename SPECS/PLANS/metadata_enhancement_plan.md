# Metadata Enhancement Plan for Improved Retrieval Quality

## Executive Summary

**Current Performance**: Dense retrieval achieves 51.3% pass rate (201/392 questions passed) with 127 complete failures.

**Root Cause Analysis**: The evaluation reveals that 45-55% of failures stem from **metadata-addressable issues**:
- 24 failures (12%) - Time-period confusion (retrieving BCY 2025 data for BCY 2026 questions)
- 44 failures (20%) - Document type mismatches (QPR vs guides vs calculators)
- 9-15 failures (6%) - Table vs narrative content confusion
- 13 failures (6%) - Topic-specific retrieval gaps
- 11 failures (5%) - Acronym/system name failures

**Proposed Solution**: Implement automated metadata extraction and filtering to enable pre-retrieval filtering and post-retrieval reranking boosting.

**Expected Impact**: 45-55% reduction in failures (127 → 60-70 failures), raising pass rate from 51.3% to ~70-75%.

---

## Problem Analysis

### Current Metadata State

**What's Stored (But Underutilized)**:
- `filename`, `page`, `content_type` (always "pdf")
- `source_url`, `pdf_id`, `file_size_mb`
- `chunk_index`, `total_chunks`, `total_pages`
- `has_context`, `master_context`, `document_context`, `chunk_context` (contextual mode only)
- `extractor`, `chunk_type`, `format` (Docling PDFs only)

**Critical Gap**: Metadata is stored but **never used** for filtering or ranking. Both dense and hybrid retrievers rely purely on:
- Dense: Semantic similarity
- Sparse: BM25 term frequency

Neither inspects metadata fields to prioritize relevant documents.

### Failure Pattern Examples

**1. Time-Period Failures (12% of failures)**
```
Question: "How many child care providers operated in Texas as of September 30, 2022?"
Expected: 9,604 center-based + 4,177 family child care (from FFY 2022 QPR)
Got: 6,484 subsidized providers (from different year/wrong aggregation)
Score: 7.0/100

Root Cause: Semantic search retrieves chunks from acf-218-qpr-ffy-2024 instead of
acf-218-qpr-ffy-2022 because both discuss "provider counts" similarly.

Metadata Fix: Filter to fiscal_year='2022' before retrieval.
```

**2. Document Type Failures (20% of failures)**
```
Question: "What is the Quality Progress Report (QPR) and what time period does it cover?"
Expected: "The QPR is an annual report lead agencies must submit..."
Got: "I don't have information on the Quality Progress Report..."
Score: 0.0/100

Root Cause: No retrieval despite having 3 QPR documents in database. Semantic match
failed because question is definitional, not content-based.

Metadata Fix: Tag all acf-218-qpr-* as document_type='qpr', boost retrieval.
```

**3. Table vs Narrative Failures (6% of failures)**
```
Question: "What is the annual income eligibility limit for a family of 4 in BCY 2026?"
Expected: "$92,041"
Got: "$6,443" (from wrong BCY table)
Score: 7.0/100

Root Cause: Semantic search ranked narrative chunks about eligibility higher than
the actual table containing family size 4 income data.

Metadata Fix: Tag table chunks as content_type='table', boost for numeric queries.
```

---

## Recommended Metadata Schema

### Phase 1: Critical Fields (Auto-Extractable from Filenames)

| Field | Type | Extraction Method | Example Values | Impact |
|-------|------|-------------------|----------------|--------|
| `fiscal_year` | string | Regex: `ffy-(\d{4})`, `bcy-(\d{2})` | '2022', '2023', '2024', '2025', '2026' | 12% |
| `board_contract_year` | string | Regex: `bcy-(\d{2})`, `bcy(\d{2})` | '26', '25', '24' | 10% |
| `document_type` | string | Filename patterns + keyword mapping | 'qpr', 'chart', 'guide', 'report', 'calculator', 'matrix' | 20% |
| `source_agency` | string | Suffix pattern: `-twc`, `-acc` | 'twc', 'hhs', 'acf', 'tea' | 5% |
| `topic_tags` | list[str] | Keyword extraction from filename | ['income_eligibility', 'psoc', 'payment_rates'] | 6% |

### Phase 2: Enhanced Fields (Requires Content Analysis)

| Field | Type | Extraction Method | Example Values |
|-------|------|-------------------|----------------|
| `legislative_session` | string | Content parsing: "88th Legislature" | '88th', '89th', '90th' |
| `coverage_period` | string | Content parsing: date ranges | 'October 1, 2023 - September 30, 2024' |
| `system_names` | list[str] | Acronym extraction | ['PCQC', 'WorkInTexas', 'TRS', 'TX3C'] |
| `data_tables_present` | bool | Check chunk_type='table' exists | true/false |
| `numeric_data_density` | float | Calculate numeric char ratio | 0.0-1.0 |

### Phase 3: Chunk-Level Fields (Enhance Existing Docling)

| Field | Current State | Enhancement Needed |
|-------|---------------|-------------------|
| `chunk_type` | 'table', 'narrative' (Docling only) | Expand to all PDFs: 'table', 'narrative', 'list', 'heading', 'definition' |
| `table_family_size` | Not extracted | Parse table rows: '1', '2', '3', ..., '15' |
| `smi_bracket` | Not extracted | Parse table columns: '1%', '15%', '25%', ..., '85%' |
| `section_title` | Not extracted | Extract from headings/context |

---

## Implementation Plan

### Stage 1: Metadata Extraction (LOAD_DB Pipeline)

**File**: `LOAD_DB/shared/metadata_extractor.py` (new)

```python
class MetadataExtractor:
    """Extracts metadata from PDF filenames and content"""

    def extract_from_filename(self, filename: str) -> dict:
        """Auto-extract metadata from filename patterns"""
        metadata = {}

        # Fiscal year: ffy-2024, ffy-2023
        if match := re.search(r'ffy-(\d{4})', filename, re.I):
            metadata['fiscal_year'] = match.group(1)

        # Board contract year: bcy-26, bcy26
        if match := re.search(r'bcy-?(\d{2})', filename, re.I):
            metadata['board_contract_year'] = match.group(1)
            metadata['fiscal_year'] = f"20{match.group(1)}"  # bcy-26 → 2026

        # Document type
        metadata['document_type'] = self._classify_document_type(filename)

        # Source agency
        if filename.endswith('-twc.pdf'):
            metadata['source_agency'] = 'twc'
        elif filename.endswith('-acc.pdf'):
            metadata['source_agency'] = 'acc'

        # Topic tags
        metadata['topic_tags'] = self._extract_topic_tags(filename)

        return metadata

    def _classify_document_type(self, filename: str) -> str:
        """Map filename patterns to document types"""
        patterns = {
            'qpr': r'acf-218-qpr',
            'chart': r'(chart|matrix)',
            'calculator': r'(calculator|pcqc)',
            'guide': r'guide',
            'report': r'(report|evaluation)',
            'plan': r'(plan|strategic)',
            'policy': r'policy',
        }

        for doc_type, pattern in patterns.items():
            if re.search(pattern, filename, re.I):
                return doc_type

        return 'document'  # default

    def _extract_topic_tags(self, filename: str) -> list[str]:
        """Extract topic keywords from filename"""
        topics = []

        topic_keywords = {
            'income_eligibility': r'income-eligibility',
            'psoc': r'psoc',
            'payment_rates': r'payment-rates',
            'attendance': r'attendance',
            'workforce': r'workforce',
            'emergency': r'emergency|disaster',
        }

        for topic, pattern in topic_keywords.items():
            if re.search(pattern, filename, re.I):
                topics.append(topic)

        return topics
```

**Integration Point**: `LOAD_DB/shared/pdf_processor.py → enrich_metadata()`

```python
def enrich_metadata(documents, pdf_filename, metadata_json=None, total_pages=None):
    """Enhanced with auto-extracted metadata"""

    # Existing metadata
    for doc in documents:
        doc.metadata['filename'] = pdf_filename
        doc.metadata['content_type'] = 'pdf'
        # ... existing code ...

    # NEW: Auto-extract metadata
    extractor = MetadataExtractor()
    auto_metadata = extractor.extract_from_filename(pdf_filename)

    for doc in documents:
        doc.metadata.update(auto_metadata)

    return documents
```

**Test Coverage**: 24 PDFs → Validate extraction accuracy:
- 3 QPR files → fiscal_year, document_type='qpr'
- 2 BCY files → board_contract_year, topic_tags=['income_eligibility', 'psoc']
- Calculator → document_type='calculator'

---

### Stage 2: Metadata Filtering (Retrieval Layer)

**File**: `chatbot/retriever.py` + `chatbot/hybrid_retriever.py`

**Approach**: Add optional metadata filters to search() method.

```python
class QdrantRetriever:
    def search(
        self,
        query: str,
        top_k: int = 20,
        metadata_filters: dict = None  # NEW parameter
    ):
        """Search with optional metadata filtering"""

        # Generate query embedding
        query_vector = self.embeddings.embed_query(query)

        # Build Qdrant filter
        qdrant_filter = None
        if metadata_filters:
            qdrant_filter = self._build_filter(metadata_filters)

        # Search with filter
        results = self.client.search(
            collection_name=self.collection,
            query_vector=("dense", query_vector),
            limit=top_k,
            query_filter=qdrant_filter,  # NEW
            score_threshold=config.MIN_SCORE_THRESHOLD
        )

        return self._format_results(results)

    def _build_filter(self, metadata_filters: dict):
        """Convert metadata dict to Qdrant Filter object"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        conditions = []

        if fiscal_year := metadata_filters.get('fiscal_year'):
            conditions.append(
                FieldCondition(
                    key="fiscal_year",
                    match=MatchValue(value=fiscal_year)
                )
            )

        if doc_type := metadata_filters.get('document_type'):
            conditions.append(
                FieldCondition(
                    key="document_type",
                    match=MatchValue(value=doc_type)
                )
            )

        if topic_tags := metadata_filters.get('topic_tags'):
            # Match any of the topic tags
            conditions.append(
                FieldCondition(
                    key="topic_tags",
                    match=MatchValue(any=topic_tags)
                )
            )

        return Filter(must=conditions) if conditions else None
```

---

### Stage 3: Query Analysis (Intent Router Enhancement)

**File**: `chatbot/query_analyzer.py` (new)

```python
class QueryAnalyzer:
    """Analyzes user query to extract metadata hints"""

    def extract_metadata_hints(self, query: str) -> dict:
        """Extract metadata filters from user query"""
        hints = {}

        # Fiscal year detection
        if match := re.search(r'\b(20\d{2})\b', query):
            hints['fiscal_year'] = match.group(1)

        if match := re.search(r'FFY\s*(\d{4})', query, re.I):
            hints['fiscal_year'] = match.group(1)

        # Board contract year
        if match := re.search(r'BCY\s*(\d{2})', query, re.I):
            hints['board_contract_year'] = match.group(1)

        # Document type hints
        doc_type_keywords = {
            'qpr': ['quality progress report', 'qpr'],
            'calculator': ['calculator', 'pcqc'],
            'chart': ['chart', 'table'],
        }

        for doc_type, keywords in doc_type_keywords.items():
            if any(kw.lower() in query.lower() for kw in keywords):
                hints['document_type'] = doc_type
                break

        # Topic hints
        topic_keywords = {
            'income_eligibility': ['income eligibility', 'income limit'],
            'psoc': ['parent share of cost', 'psoc'],
            'payment_rates': ['payment rate', 'provider payment'],
        }

        hints['topic_tags'] = []
        for topic, keywords in topic_keywords.items():
            if any(kw.lower() in query.lower() for kw in keywords):
                hints['topic_tags'].append(topic)

        return hints
```

**Integration**: `chatbot/handlers/rag_handler.py`

```python
class RAGHandler(BaseHandler):
    def __init__(self):
        # ... existing init ...
        self.query_analyzer = QueryAnalyzer()  # NEW

    def handle(self, query: str) -> dict:
        """Enhanced with query analysis"""

        # NEW: Extract metadata hints from query
        metadata_hints = self.query_analyzer.extract_metadata_hints(query)

        # Retrieve with metadata filtering
        chunks = self.retriever.search(
            query=query,
            top_k=config.RETRIEVAL_TOP_K,
            metadata_filters=metadata_hints  # NEW
        )

        # ... rest of existing pipeline ...
```

---

### Stage 4: Reranker Enhancement (Metadata Boosting)

**File**: `chatbot/reranker.py`

**Approach**: Boost scores for chunks with matching metadata.

```python
class Reranker:
    def rerank(
        self,
        query: str,
        chunks: list,
        top_k: int = 7,
        metadata_hints: dict = None  # NEW parameter
    ):
        """Rerank with metadata boosting"""

        # Existing LLM-based reranking
        reranked_chunks = self._llm_rerank(query, chunks)

        # NEW: Apply metadata boosting
        if metadata_hints:
            reranked_chunks = self._apply_metadata_boost(
                reranked_chunks,
                metadata_hints
            )

        return reranked_chunks[:top_k]

    def _apply_metadata_boost(self, chunks: list, metadata_hints: dict) -> list:
        """Boost scores for chunks matching metadata hints"""

        for chunk in chunks:
            boost = 1.0

            # Fiscal year match: +20% boost
            if (metadata_hints.get('fiscal_year') and
                chunk.get('fiscal_year') == metadata_hints['fiscal_year']):
                boost *= 1.2

            # Document type match: +15% boost
            if (metadata_hints.get('document_type') and
                chunk.get('document_type') == metadata_hints['document_type']):
                boost *= 1.15

            # Topic tag match: +10% boost per tag
            if topic_tags := metadata_hints.get('topic_tags'):
                chunk_topics = chunk.get('topic_tags', [])
                matching_topics = set(topic_tags) & set(chunk_topics)
                boost *= (1.0 + 0.1 * len(matching_topics))

            # Apply boost to score
            chunk['score'] = chunk['score'] * boost

        # Re-sort by boosted scores
        return sorted(chunks, key=lambda x: x['score'], reverse=True)
```

---

## Implementation Roadmap

### Week 1: Foundation (Metadata Extraction)
1. Create `LOAD_DB/shared/metadata_extractor.py`
2. Integrate with `enrich_metadata()` in pdf_processor.py
3. Test extraction on 24 PDFs
4. Validate schema matches design (check Qdrant payload)

**Deliverable**: All PDFs reload with 5 new metadata fields (fiscal_year, board_contract_year, document_type, source_agency, topic_tags)

### Week 2: Retrieval Integration (Filtering)
1. Create `chatbot/query_analyzer.py`
2. Add `metadata_filters` parameter to retriever.search()
3. Implement `_build_filter()` for Qdrant Filter objects
4. Test filtering on known failure cases

**Deliverable**: RAG handler can filter by fiscal_year and document_type

### Week 3: Reranking Enhancement (Boosting)
1. Add metadata boosting to reranker.py
2. Tune boost coefficients (fiscal_year: 1.2, doc_type: 1.15, topics: 1.1)
3. A/B test with/without boosting on evaluation set

**Deliverable**: Reranker boosts metadata-matching chunks

### Week 4: Evaluation & Tuning
1. Run full evaluation with metadata filtering enabled
2. Measure pass rate improvement (target: 51% → 70%)
3. Analyze remaining failures
4. Tune extraction patterns and boost coefficients
5. Document final metadata schema

**Deliverable**: Evaluation report comparing baseline vs metadata-enhanced retrieval

---

## Testing Strategy

### Unit Tests
- `test_metadata_extractor.py`: Validate extraction from 24 known filenames
- `test_query_analyzer.py`: Test query parsing for metadata hints
- `test_metadata_filtering.py`: Verify Qdrant filters work correctly

### Integration Tests
- Load 3 QPR PDFs, query for "FFY 2023 provider count", verify retrieval from correct year
- Load BCY-26 chart, query for "family of 4 income BCY 2026", verify table retrieval
- Test calculator queries retrieve from calculator docs, not guides

### Evaluation Tests
- Run evaluation on known failure subset (127 failed questions)
- Measure improvement: failed → passed count
- Target: 60-70 questions move from failed to passed (47-55% improvement)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Filename parsing errors | Medium | Medium | Extensive test coverage on all 24 PDFs |
| Over-filtering (no results) | Low | High | Make filters optional; fall back to no-filter if zero results |
| Boost coefficients too aggressive | Medium | Medium | A/B test multiple coefficient sets |
| Metadata extraction slows loading | Low | Low | Regex extraction is fast (~1ms per PDF) |
| Schema changes break existing queries | Low | Medium | Additive-only changes; existing fields unchanged |

---

## Success Metrics

### Primary Metric
- **Pass rate improvement**: 51.3% → 70-75% (target: +18-24 percentage points)

### Secondary Metrics
- **Failure reduction**: 127 failures → 60-70 failures (target: 50% reduction)
- **Time-period failures**: 24 → <5 (target: 80% reduction)
- **Document type failures**: 44 → <10 (target: 77% reduction)
- **Table retrieval failures**: 15 → <5 (target: 67% reduction)

### Quality Metrics
- **Precision at top-k**: Measure % of top-5 chunks from correct fiscal year
- **Metadata extraction accuracy**: >95% on fiscal_year, document_type fields
- **Loading performance**: No degradation (still <60 min for 42 PDFs in contextual mode)

---

## Alternative Approaches Considered

### 1. Full-Text Search with Metadata (Elasticsearch)
**Pros**: Best-in-class metadata filtering, faceted search
**Cons**: Requires new infrastructure, migration complexity, higher cost
**Decision**: Rejected - Qdrant already supports metadata filtering via Filter API

### 2. Separate Collections per Document Type
**Pros**: Simple isolation, easy A/B testing
**Cons**: Requires routing logic, duplicates data, harder to maintain
**Decision**: Rejected - Single collection with filters is cleaner

### 3. LLM-Based Metadata Extraction from Content
**Pros**: More accurate topic classification, extracts coverage periods
**Cons**: Slow (adds 60s per PDF), expensive, may hallucinate
**Decision**: Phase 2 enhancement - start with regex, add LLM later if needed

---

## Critical Files to Modify

### New Files
- `LOAD_DB/shared/metadata_extractor.py` - Metadata extraction logic
- `chatbot/query_analyzer.py` - Query→metadata hint extraction
- `tests/test_metadata_extractor.py` - Unit tests
- `tests/test_query_analyzer.py` - Unit tests

### Modified Files
- `LOAD_DB/shared/pdf_processor.py` - Integrate metadata_extractor in enrich_metadata()
- `chatbot/retriever.py` - Add metadata_filters parameter + _build_filter()
- `chatbot/hybrid_retriever.py` - Add metadata_filters parameter
- `chatbot/reranker.py` - Add metadata boosting
- `chatbot/handlers/rag_handler.py` - Call query_analyzer, pass hints to retriever/reranker
- `LOAD_DB/config.py` - Document new metadata fields (comments only)

---

## Rollout Plan

### Phase 1: Pilot (1 PDF)
- Extract metadata from `bcy-26-income-eligibility-and-maximum-psoc-twc.pdf`
- Test 10 known failures from this PDF
- Measure improvement

### Phase 2: Cluster Test (QPR Files)
- Extract metadata from 3 QPR files
- Test fiscal_year filtering on 20 QPR questions
- Tune boost coefficients

### Phase 3: Full Rollout (All 24 PDFs)
- Extract metadata from all PDFs
- Reload entire collection
- Run full 392-question evaluation

### Phase 4: Production
- Deploy to web backend
- Monitor query performance
- Collect user feedback
- Iterate on boost coefficients

---

## Implementation Decisions (Recommended Defaults)

### 1. Boost Coefficient Strategy: **Adaptive/Tunable (Start Moderate)**
- **Initial values**: fiscal_year=1.2, document_type=1.15, topic_tags=1.1
- **Make configurable** in chatbot/config.py for future A/B testing
- **Rationale**: Balance between impact and safety; can tune based on evaluation results

### 2. Filter Fallback Strategy: **Auto-retry with Warning**
- If metadata filter returns 0 results, automatically retry without filter
- Log a warning in debug mode: "Metadata filter for fiscal_year='2022' returned 0 results, falling back to unfiltered search"
- **Rationale**: User always gets an answer; developers can detect filter mismatches via logs

### 3. Metadata Extraction Scope: **Filename-Only (Phase 1 First)**
- Start with regex extraction from filenames (covers 80% of use cases)
- Defer content parsing (Phase 2) until Phase 1 shows measurable improvement
- **Rationale**: Faster to implement, test, and validate; iterate based on results

### 4. Evaluation Strategy: **Incremental with Checkpoints**
- Run evaluation after Stage 2 (filtering) and Stage 3 (boosting)
- Measure incremental impact to validate each component
- **Rationale**: Identifies which component provides most value; easier debugging if regression occurs

### 5. Table Chunk Enhancement: **Defer to Separate Project**
- Focus this effort on document-level metadata only
- Table-specific metadata (family_size, smi_bracket) is a distinct problem requiring different extraction logic
- **Rationale**: Keep scope manageable; can be next iteration after validating document-level metadata works
