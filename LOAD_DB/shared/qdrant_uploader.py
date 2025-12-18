"""
Shared Qdrant upload utilities with contextual embeddings and hybrid search support.
"""

import logging
from typing import List, Optional
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector
from prompts import MASTER_CONTEXT
import config

logger = logging.getLogger(__name__)

# Import sparse embedder for hybrid mode
try:
    from sparse_embedder import BM25Embedder
except ImportError:
    BM25Embedder = None


def upload_with_embeddings(
    client: QdrantClient,
    collection_name: str,
    documents: List[Document],
    embeddings_model: OpenAIEmbeddings,
    contextual_mode: bool = False,
    contextual_processor = None,
    document_context: Optional[str] = None,
    hybrid_mode: bool = False
):
    """
    Upload documents to Qdrant with embeddings.

    For contextual mode:
    - Embedding is computed from [Master + Document + Chunk contexts + Original content]
    - Storage keeps only original content in page_content
    - Contexts stored separately in metadata for potential future use

    For hybrid mode:
    - Dense vectors use contextual embeddings (if contextual_mode=True)
    - Sparse vectors use original content only (for exact keyword matching)
    - Named vector storage: {"dense": [...], "sparse": {"indices": [...], "values": [...]}}

    Args:
        client: QdrantClient instance
        collection_name: Name of the Qdrant collection
        documents: List of LangChain Document objects
        embeddings_model: OpenAI embeddings model
        contextual_mode: Whether to use contextual embeddings
        contextual_processor: ContextualChunkProcessor instance (required if contextual_mode=True)
        document_context: Document-level context (required if contextual_mode=True)
        hybrid_mode: Whether to generate sparse vectors for hybrid search
    """
    if not documents:
        logger.warning("No documents to upload")
        return

    logger.info(f"Generating embeddings for {len(documents)} chunks...")

    # Store original content before any modifications
    original_contents = [doc.page_content for doc in documents]

    # Prepare content for embedding (may include context)
    texts_for_embedding = []

    # Generate contextual metadata if in contextual mode
    if contextual_mode and contextual_processor and document_context:
        logger.info("Generating contextual metadata for chunks...")

        # Prepare chunk data for context generation
        chunks_for_context = []
        for doc in documents:
            chunks_for_context.append({
                'page_num': doc.metadata.get('page', 1),
                'total_pages': doc.metadata.get('total_pages', 1),
                'chunk_index': doc.metadata.get('chunk_index', 0),
                'total_chunks': doc.metadata.get('total_chunks', 1),
                'chunk_text': doc.page_content,
            })

        # Generate chunk contexts in batches
        chunk_contexts = contextual_processor.generate_all_chunk_contexts(
            chunks_for_context,
            document_context
        )

        # Prepare enriched text for embedding and store contexts in metadata
        for i, doc in enumerate(documents):
            # Store all contexts in metadata (for retrieval visibility and future use)
            doc.metadata['master_context'] = MASTER_CONTEXT
            doc.metadata['document_context'] = document_context
            doc.metadata['has_context'] = True

            if chunk_contexts and i in chunk_contexts:
                chunk_context = chunk_contexts[i]
                doc.metadata['chunk_context'] = chunk_context
            else:
                doc.metadata['chunk_context'] = None

            # Build enriched text for embedding ONLY
            # This improves embedding relevance but isn't stored in page_content
            enriched_for_embedding = f"{document_context}"
            if doc.metadata.get('chunk_context'):
                enriched_for_embedding += f"\n\n{doc.metadata['chunk_context']}"
            enriched_for_embedding += f"\n\n{original_contents[i]}"

            texts_for_embedding.append(enriched_for_embedding)

        logger.info(f"Generated contexts for {len(documents)} chunks")
        logger.info("Using enriched context for embeddings, but storing only original content")
    else:
        # Non-contextual mode: use original content as-is
        for doc in documents:
            doc.metadata['has_context'] = False
        texts_for_embedding = original_contents.copy()

    # Generate embeddings from potentially enriched text
    embeddings = embeddings_model.embed_documents(texts_for_embedding)

    # Generate sparse vectors if hybrid mode
    sparse_vectors = None
    if hybrid_mode:
        if BM25Embedder is None:
            raise ImportError("BM25Embedder not available. Check sparse_embedder.py")

        logger.info(f"Generating sparse vectors for {len(documents)} chunks...")
        sparse_embedder = BM25Embedder(vocab_size=config.BM25_VOCABULARY_SIZE)

        # Use ORIGINAL content for sparse (no context)
        # This preserves exact keyword matching
        sparse_vectors = sparse_embedder.embed(original_contents)
        logger.info("Sparse vectors generated")

    # Get current max ID to avoid conflicts
    try:
        collection_info = client.get_collection(collection_name)
        current_count = collection_info.points_count
    except:
        current_count = 0

    # Create points (always use original content in page_content, not enriched)
    points = []
    for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
        point_id = current_count + i + 1

        # Ensure page_content is original (not enriched with contexts)
        doc.page_content = original_contents[i]

        # Build vector structure for hybrid or single vector
        if hybrid_mode and sparse_vectors:
            # Named vectors for hybrid search
            vector_data = {
                "dense": embedding,
                "sparse": SparseVector(
                    indices=sparse_vectors[i].indices,
                    values=sparse_vectors[i].values
                )
            }
        else:
            # Single unnamed vector for standard search
            vector_data = embedding

        point = PointStruct(
            id=point_id,
            vector=vector_data,
            payload={
                'text': doc.page_content,
                **doc.metadata
            }
        )
        points.append(point)

    # Upload in batches
    batch_size = config.UPLOAD_BATCH_SIZE
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        logger.info(f"Uploaded batch {i//batch_size + 1} ({len(batch)} points)")

    logger.info(f"Successfully uploaded {len(documents)} chunks to Qdrant")
