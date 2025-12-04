# Conversational Intelligence Benchmarks

Manual benchmark tests comparing conversational capabilities across RAG systems.

## Overview

These tests evaluate multi-turn conversational intelligence by running the same test scenarios against different systems:
- **Custom RAG** - LangGraph pipeline with Qdrant vector store
- **OpenAI Agent** - OpenAI Agent with FileSearch tool

## Running Tests

From project root:

```bash
# Custom RAG chatbot
python tests/manual/conversational_benchmarks/run_rag.py

# OpenAI Agent Handler
python tests/manual/conversational_benchmarks/run_openai.py
```

## Test Scenarios

| ID | Name | Description |
|----|------|-------------|
| test_2 | Multi-Hop Reasoning | Synthesis across turns with calculation |
| test_2b | Multi-Hop Reasoning (Direct) | Same as above without explicit cues |
| test_3 | Negation & Filtering | Filter by negation, rank results |
| test_4 | Correction Handling | Clean pivot on user correction |
| test_5 | Topic Switch & Return | Context stack management |
| test_6 | Comparative Reasoning | Compare entities with evolving constraints |
| test_7 | Hypothetical Application | Apply rules to specific scenario |
| test_8 | Temporal Process Reasoning | Track process sequence across turns |

## Results

Results are saved to timestamped directories:

```
results/conversational_benchmarks/
├── rag/
│   └── RUN_YYYYMMDD_HHMMSS/
│       ├── results.json    # Full JSON output
│       └── report.txt      # Human-readable report
└── openai/
    └── RUN_YYYYMMDD_HHMMSS/
        ├── results.json
        └── report.txt
```

## Output Format

Each test result includes:
- Test metadata (id, name, description)
- Per-turn details:
  - User query
  - Reformulated query (RAG only)
  - Assistant response
  - Sources retrieved
  - Response time
- Success criteria for manual evaluation

## Notes

- These tests are **excluded from pytest** (not auto-discovered)
- Results require **manual review** against success criteria
- No LLM-as-a-judge scoring - outputs are for human evaluation
