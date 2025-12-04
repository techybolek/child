import vertexai
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool

# Configuration
PROJECT_ID = "docker-app-20250605"
LOCATION = "us-west1"
CORPUS_NAME = "projects/112470053465/locations/us-west1/ragCorpora/2305843009213693952"

SYSTEM_INSTRUCTION = """You are a Texas childcare assistance expert. Answer questions using ONLY information retrieved from the RAG corpus.

RULES:
- Use the retrieval tool to find relevant passages before answering
- Provide clear, accurate, concise responses (1-3 sentences)
- If information is not found in the corpus, say "I don't have information about this in my knowledge base" - do not speculate
- If a question is ambiguous, ask for clarification

RESPONSE PATTERN:
1. First, retrieve relevant information from the corpus
2. Reason about what was found and its relevance
3. Provide a direct, concise answer

DOMAIN CONTEXT:
You are answering questions about:
- Texas Workforce Commission (TWC) childcare programs
- Child Care Services (CCS) eligibility and enrollment
- Texas Rising Star quality rating system
- Parent Share of Cost calculations
- Provider requirements and reimbursement rates
"""

# Initialize
vertexai.init(project=PROJECT_ID, location=LOCATION)

def query_rag(question: str):
    """Query the RAG corpus and generate a response."""

    # Create RAG retrieval tool
    rag_retrieval_tool = Tool.from_retrieval(
        retrieval=rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=CORPUS_NAME)],
                similarity_top_k=10,
            ),
        )
    )

    # Create model with RAG tool and system instruction
    model = GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=[rag_retrieval_tool],
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # Generate response
    response = model.generate_content(question)

    return response.text

if __name__ == "__main__":
    # Test questions
    test_questions = [
        "What are the income eligibility requirements for child care assistance in Texas?",
        "How does the Texas Rising Star program work?",
        "What is the parent share of cost and how is it calculated?",
    ]

    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {q}")
        print(f"{'='*60}")
        answer = query_rag(q)
        print(f"A: {answer}")
