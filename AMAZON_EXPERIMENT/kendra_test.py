from langchain_aws import AmazonKendraRetriever, ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

index_id = "4aee3b7a-0217-4ce5-a0a2-b737cda375d9"
region = "us-east-1"  # Adjust to your region

# Initialize Kendra retriever
retriever = AmazonKendraRetriever(
    index_id=index_id,
    region_name=region,
    top_k=5,
    min_score_confidence=0.0  # Required in langchain-aws 1.0
)

# Initialize Bedrock LLM (Amazon Titan - no approval needed)
llm = ChatBedrockConverse(
    model_id="amazon.titan-text-express-v1",
    region_name=region
)

# Create prompt template
prompt = ChatPromptTemplate.from_template("""Answer the question based on the following context:

Context:
{context}

Question: {question}

Answer:""")

# Format docs helper
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Create RAG chain using LCEL
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# Run query
query = "What is the Parent Share of Cost (PSoC) and how does it work?"

print("Fetching from Kendra and generating answer...\n")

# Get documents for source display
# docs = retriever.invoke(query)
answer = rag_chain.invoke(query)

print("Answer:", answer)
#print("\nSources:")
#for doc in docs:
#    print(f"  - {doc.metadata.get('source', doc.metadata.get('title', 'Unknown'))}")
