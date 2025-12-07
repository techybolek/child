# Vertex AI Agent Mode

```mermaid
flowchart TD
    A[User Query] --> B[Gemini Model<br/>with RAG Tool]

    B <--> VS[(Vertex AI<br/>RAG Corpus)]

    B --> Z[Response]

    HIST[Chat Session History] --> B

    style A fill:#e1f5fe
    style Z fill:#c8e6c9
    style VS fill:#4285f4,stroke:#1a73e8,stroke-width:3px,color:#fff
    style B fill:#4285f4,stroke:#1a73e8,stroke-width:2px,color:#fff
    style HIST fill:#e8f5e9
```

**Note:** Vertex AI Agent mode bypasses the LangGraph pipeline entirely. Gemini with the RAG retrieval tool handles retrieval and generation in a single call using the Vertex AI RAG Corpus.
