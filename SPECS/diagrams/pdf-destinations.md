# PDF Destinations

```mermaid
flowchart LR
    PDF[PDF Files]

    PDF --> CUSTOM[Custom RAG<br/>Qdrant + LangGraph]
    PDF --> KENDRA[AWS Kendra Index]
    PDF --> OPENAI[OpenAI Vector Store]
    PDF --> VERTEX[Vertex RAG Corpus]
```
