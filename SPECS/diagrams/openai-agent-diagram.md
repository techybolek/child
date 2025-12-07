# OpenAI Agent Mode

```mermaid
flowchart TD
    A[User Query] --> B[OpenAI Agent<br/>with FileSearchTool]

    B <--> VS[(OpenAI<br/>Vector Store)]

    B --> Z[Response]

    HIST[Conversation History] --> B

    style A fill:#e1f5fe
    style Z fill:#c8e6c9
    style VS fill:#10a37f,stroke:#0d8c6d,stroke-width:3px,color:#fff
    style B fill:#10a37f,stroke:#0d8c6d,stroke-width:2px,color:#fff
    style HIST fill:#e8f5e9
```

**Note:** OpenAI Agent mode bypasses the LangGraph pipeline entirely. The OpenAI Agents SDK handles retrieval and generation in a single call using FileSearchTool with the OpenAI Vector Store.
