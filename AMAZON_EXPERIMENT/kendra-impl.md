# Amazon Kendra + Bedrock RAG Implementation

## Overview

This implementation uses **Amazon Kendra** for document retrieval and **Amazon Bedrock** (Titan) for answer generation, creating a complete RAG (Retrieval-Augmented Generation) pipeline.

## Prerequisites

### 1. AWS Services
- **Amazon Kendra** index with synced documents
- **Amazon Bedrock** with model access enabled

### 2. Python Dependencies
```bash
pip install langchain langchain-aws boto3
```

### 3. AWS Credentials
Configure via one of:
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
- AWS credentials file: `~/.aws/credentials`
- IAM role (if running on AWS infrastructure)

Required IAM permissions:
- `kendra:Query`
- `kendra:Retrieve`
- `bedrock:InvokeModel`

## Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| `index_id` | `4aee3b7a-0217-4ce5-a0a2-b737cda375d9` | Kendra index ID |
| `region` | `us-east-1` | AWS region |
| `model_id` | `amazon.titan-text-express-v1` | Bedrock LLM model |
| `top_k` | `5` | Number of documents to retrieve |

## Usage

```bash
cd /home/tromanow/COHORT/TX/AMAZON_EXPERIMENT
python kendra_test.py
```

To change the query, edit line 45 in `kendra_test.py`:
```python
query = "Your question here"
```

## Code Structure

```python
from langchain_aws import AmazonKendraRetriever, ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
```

### Components

1. **AmazonKendraRetriever** - Queries Kendra index for relevant documents
2. **ChatBedrockConverse** - Bedrock LLM for answer generation
3. **LCEL Chain** - LangChain Expression Language pipeline connecting retrieval → prompt → LLM → output

### Pipeline Flow

```
User Query
    ↓
Kendra Retriever (top_k=5 documents)
    ↓
Format Documents (concatenate content)
    ↓
Prompt Template (inject context + question)
    ↓
Bedrock LLM (Titan)
    ↓
Answer + Sources
```

## Alternative Models

To use Claude instead of Titan (requires Anthropic approval in Bedrock):

```python
llm = ChatBedrockConverse(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    region_name=region
)
```

**Note:** Claude models require filling out Anthropic's use case form in AWS Bedrock Model Access.

## Troubleshooting

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: langchain_aws` | `pip install langchain-aws` |
| `Invalid length for parameter IndexId` | Use full UUID from Kendra console |
| `ResourceNotFoundException: Model use case details` | Enable model in Bedrock Model Access |
| `AccessDeniedException` | Check IAM permissions for Kendra and Bedrock |

## Files

- `kendra_test.py` - Main RAG implementation
- `kendra-1.py` - Original sample (outdated imports)
- `kendra-impl.md` - This documentation
