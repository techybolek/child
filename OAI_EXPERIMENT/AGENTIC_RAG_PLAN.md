# Agentic RAG Implementation Plan

## Goal
Refactor the existing LangGraph pipeline RAG into an agentic RAG where the LLM controls when and how to retrieve documents, rather than following a fixed pipeline.

## Current State (Pipeline RAG)
```
User Input → Reformulate → Classify → Retrieve → Rerank → Generate → Response
```
- Retrieval **always** happens
- Query is predetermined (user input or reformulated)
- No feedback loop - one-shot retrieval
- Model has no control over the process

## Target State (Agentic RAG)
```
User Input → LLM decides:
    ├── Call search tool? → Execute → See results → Decide again
    ├── Ask clarifying question? → Return question
    └── Answer directly? → Return answer
```
- LLM decides **if** retrieval is needed
- LLM crafts the **search query**
- LLM sees results and can **retry** with different query
- LLM controls the entire loop

## Key Components to Build

### 1. Tool Definition
Define a `search_childcare_docs` tool that wraps your existing hybrid retriever + reranker:

```python
# Tool schema for OpenAI function calling
SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_childcare_docs",
        "description": "Search Texas childcare assistance policy documents. Use this to find information about eligibility, income limits, programs (CCS, CCMS, Texas Rising Star), application processes, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - be specific and include relevant keywords"
                }
            },
            "required": ["query"]
        }
    }
}
```

### 2. Tool Executor
Function that executes the tool and returns formatted results:

```python
def execute_search_tool(query: str) -> str:
    # Use existing hybrid retriever
    chunks = hybrid_retriever.retrieve(query, top_k=30)

    # Use existing reranker
    reranked = reranker.rerank(query, chunks, top_k=7)

    # Format results for LLM consumption
    return format_chunks_for_llm(reranked)
```

### 3. Agentic Loop
The core loop that gives the LLM control:

```python
async def agentic_rag(user_input: str, conversation_history: list) -> str:
    # Add user message to history
    conversation_history.append({"role": "user", "content": user_input})

    while True:
        # Call LLM with tools available
        response = await client.chat.completions.create(
            model="gpt-4o",  # or groq model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history
            ],
            tools=[SEARCH_TOOL],
            tool_choice="auto",  # LLM decides
        )

        message = response.choices[0].message

        if message.tool_calls:
            # LLM wants to search - execute and continue loop
            conversation_history.append(message)

            for tool_call in message.tool_calls:
                result = execute_search_tool(tool_call.function.arguments["query"])
                conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        else:
            # No tool call = final answer
            conversation_history.append(message)
            return message.content
```

### 4. System Prompt
Critical for guiding the agent's behavior:

```python
SYSTEM_PROMPT = """You are a helpful assistant specializing in Texas childcare assistance programs.

You have access to a search tool to find information in policy documents. Use it when:
- User asks about eligibility, income limits, requirements
- User asks about specific programs (CCS, CCMS, Texas Rising Star, PSOC)
- User asks about application processes, deadlines, documentation
- You need factual information you don't already have from this conversation

Do NOT use the search tool when:
- User is asking for clarification on something you already explained
- User says thanks, goodbye, or other conversational messages
- You already retrieved relevant information in this conversation
- User asks you to rephrase or summarize your previous answer

When you search:
- Craft specific, keyword-rich queries
- If results are insufficient, try a different query
- Cite information from the documents

When you answer:
- Be concise (1-4 sentences)
- If information isn't found, say so clearly
- Ask clarifying questions if the query is ambiguous
"""
```

## Implementation Steps

### Step 1: Create agentic_chatbot.py
New file with:
- Tool definition
- Tool executor (wrapping hybrid_retriever + reranker)
- Agentic loop function
- System prompt

### Step 2: Create agentic_interactive.py
Interactive CLI that:
- Maintains conversation history across turns
- Calls the agentic loop
- Supports `clear` command to reset

### Step 3: Test Scenarios
Verify the agent:
1. **Retrieves when needed**: "What are the income limits?" → should search
2. **Skips retrieval when not needed**: "Thanks!" → should NOT search
3. **Handles follow-ups**: "What about for a family of 4?" → should search with expanded query
4. **Asks clarification**: "Am I eligible?" → should ask for more info
5. **Retries on bad results**: If first search fails, tries different query

## Files to Create

```
OAI_EXPERIMENT/
├── agentic_chatbot.py      # Core agentic RAG implementation
├── agentic_interactive.py  # Interactive CLI
└── AGENTIC_RAG_PLAN.md     # This plan
```

## Dependencies
- Existing: `chatbot/hybrid_retriever.py`, `chatbot/reranker.py`
- OpenAI SDK (already have) or Groq SDK
- No new dependencies needed

## Comparison: Before vs After

| Scenario | Pipeline RAG | Agentic RAG |
|----------|-------------|-------------|
| "Thanks for the help!" | Retrieves → wastes time | No retrieval → instant response |
| "What about income?" (follow-up) | Reformulates → retrieves | LLM crafts query "Texas childcare income limits eligibility" |
| "Can you explain that differently?" | Retrieves same docs | Uses existing context, no retrieval |
| Poor retrieval results | One shot, stuck with bad results | Can retry with different query |
| "Am I eligible?" (ambiguous) | Retrieves generic docs | Asks "What's your family size and income?" |

## Success Criteria
1. Agent correctly decides when to search vs not search
2. Agent formulates effective search queries
3. Multi-turn conversations work smoothly
4. Response quality matches or exceeds current pipeline
5. Fewer unnecessary retrievals = faster responses
