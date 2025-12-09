# Kendra Retrieval Mode

```mermaid
flowchart TD
    A[User Query] --> B{Reformulate?}

    B -->|Yes| C[Reformulate Query]
    B -->|No| D[Classify Intent]
    C --> D

    D --> E{Intent?}

    E -->|location_search| F[Template Response +<br/>Texas HHS Link]
    F --> Z[Response]

    E -->|information| G[Kendra Hybrid<br/>Search + Rerank]
    AWS[(AWS Kendra<br/>Index)] <--> G

    G --> J[Generate Response]
    MEM[Message History] --> C
    MEM --> J

    J --> Z

    style A fill:#e1f5fe
    style Z fill:#c8e6c9
    style AWS fill:#ff9900,stroke:#232f3e,stroke-width:3px,color:#fff
    style MEM fill:#e8f5e9
    style C fill:#ffcdd2,stroke:#e53935,stroke-width:2px
    style D fill:#ffcdd2,stroke:#e53935,stroke-width:2px
    style J fill:#ffcdd2,stroke:#e53935,stroke-width:2px
    style G fill:#ffcdd2,stroke:#e53935,stroke-width:2px
```

**Note:** Kendra mode uses built-in semantic reranking (no separate LLM reranker needed).
