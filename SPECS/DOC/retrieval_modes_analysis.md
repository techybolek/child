# Retrieval Modes Analysis: Dense, Hybrid, Kendra, and OpenAI

## Executive Summary

The Texas Childcare RAG system supports 4 distinct retrieval modes for evaluation:
1. **Dense** - Qdrant semantic search with OpenAI embeddings
2. **Hybrid** - Qdrant dense + sparse vectors with RRF fusion
3. **Kendra** - AWS Kendra managed search + Bedrock Titan
4. **OpenAI** - Agentic approach with FileSearch tool + gpt-5-nano

**Key Finding**: OpenAI stands out as fundamentally different because it uses an **agentic architecture** where the LLM autonomously decides when and how to search, versus the other modes which use **deterministic pipelines** with fixed retrieval stages.

---

## Mode 1: Dense Retrieval (Qdrant)

### Architecture
```
Query → OpenAI Embeddings → Qdrant Cosine Search → Top-30 Chunks →
LLM Reranking → Top-7 Chunks → Generate Answer with Citations
```

### Key Characteristics
- **Retriever**: `QdrantRetriever` (chatbot/retriever.py)
- **Collection**: `tro-child-hybrid-v1` (uses only dense vectors)
- **Embeddings**: OpenAI `text-embedding-3-small` (1536-dim)
- **Search**: Cosine similarity with named vector syntax: `("dense", query_vector)`
- **Top-K**: Retrieves 30 chunks, reranks to 7
- **Scoring**: Cosine similarity (0.3-1.0 after threshold filtering)

### Pipeline Stages
1. **Retrieval**: Semantic search via OpenAI embeddings
2. **Reranking**: LLM judge (GROQ/OpenAI) scores relevance 0-10
3. **Generation**: Template-based prompt with [Doc N] citations
4. **Context Injection**: Master + document + chunk contexts

### Strengths
- Captures semantic meaning and conceptual relationships
- Fast retrieval (direct vector search)
- Full transparency (debug mode shows all steps)
- Explicit reranking control (adaptive or fixed top-k)

### Weaknesses
- May miss exact keyword matches (e.g., "BCY-26", specific dollar amounts)
- No keyword fallback mechanism

---

## Mode 2: Hybrid Retrieval (Qdrant)

### Architecture
```
Query → [Dense Vector + Sparse Vector] →
Prefetch Top-100 Dense + Top-100 Sparse →
RRF Fusion → Top-30 Combined →
LLM Reranking → Top-7 Chunks →
Generate Answer with Citations
```

### Key Characteristics
- **Retriever**: `QdrantHybridRetriever` (chatbot/hybrid_retriever.py)
- **Collection**: `tro-child-hybrid-v1` (dual vectors: dense + sparse)
- **Dense**: OpenAI embeddings (1536-dim)
- **Sparse**: BM25 tokenization with hashing (30,000 vocab size)
- **Fusion**: Reciprocal Rank Fusion (RRF) with k=60
- **Search**: Qdrant `query_points()` with dual Prefetch + Fusion

### Pipeline Stages
1. **Dual Embedding**:
   - Dense: OpenAI semantic vector
   - Sparse: BM25 keyword vector (preserves "$4,106", "85%", "BCY-26")
2. **Dual Prefetch**: Top-100 from each vector type
3. **RRF Fusion**: Combine rankings using formula: `1/(60+rank_dense) + 1/(60+rank_sparse)`
4. **Reranking**: Same LLM judge as dense mode
5. **Generation**: Same as dense mode

### RRF Formula
```python
RRF_Score = 1/(k + rank_dense) + 1/(k + rank_sparse)
# k = 60 (default)
# Balances both semantic and keyword contributions equally
```

### Sparse Vector Generation
```python
# Tokenization preserves domain terms:
"$4,106" → "dollar_4106"
"85%" → "85percent"
"family of 5" → ["family", "of", "num5"]
"BCY-26" → ["bcy", "26"]

# Hash to 30,000 vocab indices with term frequencies
# Example: [145, 2847, 8291] with values [1.0, 2.0, 1.0]
```

### Strengths
- Combines semantic understanding + exact keyword matching
- Better for queries with specific terms (IDs, amounts, percentages)
- Automatic fallback to dense-only if RRF fails
- Same transparency as dense mode

### Weaknesses
- Slightly higher latency (dual search + fusion)
- More complex to debug (two retrieval streams)

---

## Mode 3: Kendra (AWS)

### Architecture
```
Query → AWS Kendra Retrieval (black-box) → Top-5 Docs →
Generate Answer with Bedrock Titan + Citations
```

### Key Characteristics
- **Retriever**: `AmazonKendraRetriever` (LangChain AWS integration)
- **Index**: `4aee3b7a-0217-4ce5-a0a2-b737cda375d9` (us-east-1)
- **Generator**: AWS Bedrock `openai.gpt-oss-20b-1:0` (GPT-OSS 20B)
- **Top-K**: Only 5 documents (much smaller than 30)
- **Scoring**: Kendra's proprietary relevance scores

### Pipeline Stages
1. **Retrieval**: Kendra native search (proprietary algorithm)
2. **Generation**: Bedrock Titan with simple prompt template
3. **Citation Extraction**: Regex-based [Doc N] parsing

### Key Differences from Qdrant Modes
- **NO Reranking Step**: Skips the entire reranking stage
- **Smaller Batch**: Retrieves only 5 docs vs 30
- **Simpler Context**: No master/document/chunk context injection
- **Fixed Model**: Locked to Bedrock Titan (no GROQ/OpenAI options)
- **AWS-Specific**: Requires AWS credentials and infrastructure

### Strengths
- Managed service (AWS handles scaling, reliability)
- Proprietary Kendra search may capture unique patterns
- Simpler pipeline (fewer moving parts)

### Weaknesses
- Black-box retrieval (no debug visibility into scoring)
- No reranking quality control
- Smaller context window (5 vs 7 final chunks)
- AWS vendor lock-in
- Higher operational complexity (two AWS services: Kendra + Bedrock)

---

## Mode 4: OpenAI Agent (DISTINCT ARCHITECTURE)

### Architecture
```
Query → OpenAI Agent (gpt-5-nano) →
Agent Reasoning → FileSearch Tool Call →
OpenAI Vector Store Search →
Agent Synthesizes Answer + Citations
```

### Key Characteristics
- **Agent**: `agent1.py` in `OAI_EXPERIMENT/`
- **Model**: `gpt-5-nano` with reasoning tokens (low effort)
- **Tool**: OpenAI FileSearch with vector store `vs_69210129c50c81919a906d0576237ff5`
- **Retrieval**: Managed by OpenAI (black-box)
- **Reasoning**: Extended thinking via reasoning token support
- **Autonomy**: Agent decides when/how to search

### Pipeline Stages
1. **Agent Initialization**: FileSearch tool connected to pre-loaded vector store
2. **Reasoning**: Agent thinks about query using reasoning tokens
3. **Tool Calling**: Agent autonomously calls FileSearch when needed
4. **Synthesis**: Agent combines retrieved snippets into structured response
5. **Parsing**: Evaluator extracts ANSWER: and SOURCES: sections

### Agentic Features
```python
# Agent configuration
ModelSettings(
    store=True,                          # Conversation memory
    reasoning=Reasoning(
        effort="low",                    # Extended thinking enabled
        summary="auto"                   # Auto-summarize reasoning
    )
)

# FileSearch tool (managed by OpenAI)
FileSearchTool(
    vector_store_ids=["vs_69210129c50c81919a906d0576237ff5"]
)
```

### How It Stands Out

#### 1. **Agentic vs. Deterministic**
- **OpenAI**: LLM autonomously decides what to search and how
- **Dense/Hybrid/Kendra**: Fixed pipeline where each step is predetermined

#### 2. **Reasoning Token Support**
- **OpenAI**: Has native reasoning tokens for extended thinking
- **Dense/Hybrid/Kendra**: Standard completion tokens only

#### 3. **Conversation Context**
- **OpenAI**: Maintains conversation history across tool calls
- **Dense/Hybrid/Kendra**: Stateless (each query independent)

#### 4. **Managed Infrastructure**
- **OpenAI**: Vector store + FileSearch managed by OpenAI
- **Dense/Hybrid**: Self-hosted Qdrant requires maintenance
- **Kendra**: AWS-managed but requires infrastructure setup

#### 5. **Multi-Step Reasoning**
- **OpenAI**: Can perform internal reasoning before searching
- **Dense/Hybrid/Kendra**: Single-pass retrieval, no internal reasoning

#### 6. **Transparency Trade-off**
- **OpenAI**: Black-box tool (can't see retrieval details)
- **Dense/Hybrid/Kendra**: Full pipeline visibility (debug logs)

### Response Format
```
ANSWER:
To qualify for Texas childcare assistance, you must be a Texas resident...

SOURCES:
- child-care-services-guide-twc.pdf
- bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
```

**Limitation**: No page numbers provided (only document names)

### Strengths
- Autonomous decision-making (agent thinks through problems)
- Reasoning token support (extended thinking)
- Managed service (production-grade reliability)
- Natural conversation flow
- Built-in citation handling

### Weaknesses
- Black-box retrieval (no debug visibility)
- Higher latency (reasoning + tool calling overhead)
- Expensive (reasoning tokens + API calls)
- Dense-only (no hybrid keyword support)
- No page-level citations
- Tight OpenAI ecosystem coupling

---

## Comparative Summary

### Architecture Paradigms

| Aspect | Dense/Hybrid | Kendra | OpenAI |
|--------|--------------|--------|--------|
| **Paradigm** | Deterministic RAG Pipeline | Simplified RAG Pipeline | Agentic Tool-Based |
| **Retrieval Control** | Explicit (Python code) | Explicit (AWS API) | Autonomous (Agent decision) |
| **Pipeline Stages** | 3 (Retrieve→Rerank→Generate) | 2 (Retrieve→Generate) | 1 (Agent handles all) |
| **Transparency** | High (full debug logs) | Medium (no reranking) | Low (black-box tool) |
| **Reasoning** | None | None | Extended thinking |
| **Autonomy** | None | None | High |

### Retrieval Characteristics

| Aspect | Dense | Hybrid | Kendra | OpenAI |
|--------|-------|--------|--------|--------|
| **Vector Type** | Dense only | Dense + Sparse | Proprietary | Dense only |
| **Top-K Retrieved** | 30 | 30 | 5 | Unknown |
| **Top-K Final** | 7 (after rerank) | 7 (after rerank) | 5 (no rerank) | Unknown |
| **Fusion Method** | N/A | RRF (k=60) | N/A | N/A |
| **Keyword Matching** | Poor | Excellent | Unknown | Poor |
| **Semantic Search** | Excellent | Excellent | Good | Excellent |

### Operational Characteristics

| Aspect | Dense | Hybrid | Kendra | OpenAI |
|--------|-------|--------|--------|--------|
| **Latency** | Low (~2-3s) | Low (~2-3s) | Medium (~3-4s) | High (~5-8s) |
| **Cost per Query** | Low | Low | Medium | High |
| **Infrastructure** | Qdrant (self/cloud) | Qdrant (self/cloud) | AWS (managed) | OpenAI (managed) |
| **Debug Visibility** | Full | Full | Medium | Low |
| **Configuration** | High | High | Medium | Low |
| **Page Citations** | Yes | Yes | Yes | No |

---

## Key Insight: Why OpenAI Stands Out

The OpenAI implementation is **architecturally distinct** because it represents a **paradigm shift from pipelines to agents**:

### Traditional RAG (Dense/Hybrid/Kendra)
```python
# Deterministic pipeline
chunks = retrieve(query)       # Fixed retrieval
ranked = rerank(chunks)        # Fixed reranking (if present)
answer = generate(ranked)      # Fixed generation
return answer
```

### Agentic RAG (OpenAI)
```python
# Agent decides what to do
agent = Agent(tools=[FileSearch])
agent.think(query)             # Reasoning tokens
if agent.needs_info():         # Autonomous decision
    docs = agent.use_tool(FileSearch)
    agent.synthesize(docs)     # Multi-step reasoning
return agent.response
```

The agent can:
1. **Reason about the query** before searching
2. **Decide when to search** (may not search at all for simple questions)
3. **Perform multi-step retrieval** (search multiple times if needed)
4. **Synthesize across tool calls** (maintain conversation context)

This is fundamentally different from the linear "retrieve → rerank → generate" pipeline of traditional RAG.

---

## Evaluation Integration

All four modes integrate through the **adapter pattern** to ensure fair comparison:

### Common Interface
```python
class BaseEvaluator:
    def query(self, question: str, debug: bool = False) -> dict:
        # Returns standardized format
        return {
            'answer': str,
            'sources': list,
            'response_type': str,
            'response_time': float
        }
```

### Mode-Specific Evaluators
- **Dense/Hybrid**: `ChatbotEvaluator` → `RAGHandler(retrieval_mode='dense'|'hybrid')`
- **Kendra**: `KendraEvaluator` → `KendraHandler`
- **OpenAI**: `OpenAIAgentEvaluator` → `agent1.run_workflow()`

### Output Isolation
```
results/
├── dense/           # Dense-only mode results
├── hybrid/          # Hybrid mode results
├── kendra/          # Kendra mode results
└── openai/          # OpenAI agent results
```

Each mode writes to isolated directories, enabling parallel evaluation without conflicts.

---

## Critical Files Reference

### Dense/Hybrid Implementation
- `chatbot/retriever.py` - Dense retrieval (QdrantRetriever)
- `chatbot/hybrid_retriever.py` - Hybrid retrieval (QdrantHybridRetriever)
- `chatbot/sparse_embedder.py` - BM25 tokenization for sparse vectors
- `chatbot/reranker.py` - LLM-based reranking
- `chatbot/generator.py` - Answer generation with context injection
- `chatbot/handlers/rag_handler.py` - Pipeline orchestration

### Kendra Implementation
- `chatbot/handlers/kendra_handler.py` - Kendra retrieval + Bedrock generation
- `evaluation/kendra_evaluator.py` - Kendra evaluator adapter

### OpenAI Implementation
- `OAI_EXPERIMENT/agent1.py` - Agent definition + FileSearch tool
- `evaluation/openai_evaluator.py` - OpenAI agent evaluator adapter

### Evaluation Framework
- `evaluation/run_evaluation.py` - Entry point (mode selection)
- `evaluation/batch_evaluator.py` - Core evaluation logic
- `evaluation/evaluator.py` - Dense/Hybrid evaluator
- `evaluation/judge.py` - LLM-based scoring
- `evaluation/config.py` - Mode configuration

---

## Conclusion

The four retrieval modes represent distinct points in the **control vs. autonomy spectrum**:

1. **Dense** - Maximum control, semantic-only
2. **Hybrid** - Maximum control, semantic + keyword
3. **Kendra** - Managed service, moderate control
4. **OpenAI** - Agentic approach, maximum autonomy

**OpenAI stands out** because it's the only mode that uses an **agentic architecture** where the LLM autonomously reasons about queries and decides when/how to search, rather than following a fixed retrieval pipeline. This comes at the cost of transparency and higher latency, but enables more sophisticated multi-step reasoning and conversational capabilities.
