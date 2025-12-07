# Custom RAG Pipeline (Conversational)

```mermaid
flowchart TD
    A[User Query] --> B{Reformulate?}

    B -->|Yes| C[Reformulate Query]
    B -->|No| D[Classify Intent]
    C --> D

    D --> E{Intent?}

    E -->|location_search| F[Template Response +<br/>Texas HHS Link]
    F --> Z[Response]

    E -->|information| G[Calculate Embedding<br/>OpenAI text-embedding-3-small]
    G --> H[Semantic/Hybrid Search<br/>Top-30]
    QDB[(Qdrant DB<br/>tro-child-hybrid-v1)] <--> H

    H --> I[Rerank<br/>LLM as a Judge]

    I --> J[Generate Response]
    MEM[Message History] --> C
    MEM --> J

    J --> Z

    style A fill:#e1f5fe
    style Z fill:#c8e6c9
    style QDB fill:#fff3e0,stroke:#ff9800,stroke-width:3px
    style I fill:#fce4ec
    style J fill:#f3e5f5
    style MEM fill:#e8f5e9
```
