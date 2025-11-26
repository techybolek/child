from langchain_aws import AmazonKendraRetriever

index_id = "4aee3b7a-0217-4ce5-a0a2-b737cda375d9"
region = "us-east-1"

# Initialize Kendra retriever
retriever = AmazonKendraRetriever(
    index_id=index_id,
    region_name=region,
    top_k=5,
    min_score_confidence=0.0
)

# Query
query = "What is the Parent Share of Cost (PSoC) and how does it work?"

print(f"Query: {query}\n")
print("Retrieving documents from Kendra...\n")

# Retrieve documents (no LLM generation)
docs = retriever.invoke(query)

print(f"Retrieved {len(docs)} documents:\n")
print("=" * 80)

for i, doc in enumerate(docs, 1):
    print(f"\nDocument {i}:")
    print(f"Source: {doc.metadata.get('source', doc.metadata.get('title', 'Unknown'))}")
    print(f"Score: {doc.metadata.get('score', 'N/A')}")
    print(f"\nContent:\n{doc.page_content[:500]}...")  # First 500 chars
    print("-" * 80)
