import vertexai
from vertexai.preview import rag

# Initialize
project_id = "docker-app-20250605"
location = "us-west1"  # us-central1 and us-east4 are restricted for new projects
vertexai.init(project=project_id, location=location)

# Create a Corpus with a Managed DB
# This automatically handles the vector DB infrastructure for you
vector_db = rag.RagManagedDb(retrieval_strategy=rag.KNN())
corpus = rag.create_corpus(
    display_name="my-enterprise-knowledge-base",
    backend_config=rag.RagVectorDbConfig(vector_db=vector_db)
)

print(f"Corpus created: {corpus.name}")