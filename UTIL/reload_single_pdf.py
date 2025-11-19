"""
Surgical reload of a single PDF to Qdrant.

Deletes all chunks for a specific PDF and reloads it with the fixed text cleaner.
Avoids expensive full database reload.

Usage:
    python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
"""

import os
import sys
import logging
from typing import List

# Add LOAD_DB to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'LOAD_DB'))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.docstore.document import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel

import config
from contextual_processor import ContextualChunkProcessor
from prompts import MASTER_CONTEXT
from text_cleaner import clean_text, is_likely_toc, is_markdown_table


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class SinglePDFReloader:
    """Surgically reload a single PDF to Qdrant."""

    def __init__(self, pdf_filename: str, contextual_mode: bool = True):
        """
        Initialize the single PDF reloader.

        Args:
            pdf_filename: Name of the PDF file (e.g., 'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf')
            contextual_mode: If True, uses contextual embeddings (default: True for tro-child-3-contextual)
        """
        self.pdf_filename = pdf_filename
        self.contextual_mode = contextual_mode

        # Set collection name based on contextual mode
        self.collection_name = config.QDRANT_COLLECTION_NAME_CONTEXTUAL if contextual_mode else config.QDRANT_COLLECTION_NAME
        logger.info(f"Using collection: {self.collection_name}")

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY,
        )

        # Initialize OpenAI embeddings
        logger.info(f"Initializing OpenAI embeddings: {config.EMBEDDING_MODEL}")
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=config.OPENAI_API_KEY
        )

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=config.CHUNK_SEPARATORS,
            length_function=len,
        )

        # Initialize contextual processor if enabled
        self.contextual_processor = None
        if self.contextual_mode:
            logger.info(f"Initializing contextual processor with model: {config.GROQ_MODEL}")
            self.contextual_processor = ContextualChunkProcessor(
                groq_api_key=config.GROQ_API_KEY,
                model=config.GROQ_MODEL
            )

    def extract_pdf_with_pymupdf(self, pdf_path: str) -> List[Document]:
        """
        Extract PDF content using PyMuPDF (fast, standard text extraction).

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of LangChain Document objects (one per page)
        """
        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()
        return documents

    def fix_rotated_columns(self, df) -> tuple:
        """
        Detect and fix rotated table columns.

        Handles two patterns:
        1. All rows rotated (Year col has %, last col has years)
        2. Last row only scrambled (e.g., "58.81% | 2022 | 88.45%")

        Args:
            df: pandas DataFrame

        Returns:
            Tuple of (fixed_df, was_fixed_bool)
        """
        import pandas as pd
        import re

        if len(df.columns) < 2 or len(df) == 0:
            return df, False

        was_fixed = False
        last_col = df.iloc[:, -1].astype(str)
        first_col = df.iloc[:, 0].astype(str)
        first_col_name = df.columns[0]

        # Pattern 1: Global rotation - years in last column, percentages in first
        year_pattern = r'\b(19|20)\d{2}\b'
        has_years_in_last = last_col.str.contains(year_pattern, na=False, regex=True).sum() >= 2
        has_percentages_in_first = first_col.str.contains('%', na=False, regex=False).sum() >= 2

        if has_years_in_last and has_percentages_in_first and 'year' in first_col_name.lower():
            # Rotate columns: move last column to first
            cols = df.columns.tolist()
            df = df[[cols[-1]] + cols[:-1]]
            df.columns = cols
            was_fixed = True

            # Refresh column references after rotation
            first_col = df.iloc[:, 0].astype(str)

        # Pattern 2: Fix last row if it has percentage in Year column
        if len(df) > 1 and 'year' in first_col_name.lower():
            last_row_first_val = str(df.iloc[-1, 0])

            # Check if last row Year column starts with percentage
            if '%' in last_row_first_val and not re.match(year_pattern, last_row_first_val):
                # Extract year and values from the row
                row_vals = df.iloc[-1].tolist()

                # Look for a year value somewhere in the row
                year_val = None
                year_idx = None
                for idx, val in enumerate(row_vals):
                    val_str = str(val)
                    year_match = re.search(year_pattern, val_str)
                    if year_match:
                        year_val = year_match.group(0)
                        year_idx = idx
                        break

                if year_val and year_idx is not None:
                    # Rotate the last row values
                    new_row_vals = row_vals.copy()

                    if year_idx == len(row_vals) - 1:
                        # Year is in last column - rotate all columns right by 1
                        new_row_vals = [row_vals[-1]] + row_vals[:-1]
                    elif year_idx == 1:
                        # Year is in middle column - check if it's a left rotation issue
                        # Pattern: "58.81% | 2022 | 88.45%" should be "2022 | 88.45% | 58.81%"
                        new_row_vals = [year_val] + row_vals[2:] + [row_vals[0]]

                    # Apply the fix
                    df.iloc[-1] = new_row_vals
                    was_fixed = True

        # Pattern 3: Fix combined values (like "2016 84.55%") in Year column
        if 'year' in first_col_name.lower():
            for idx, val in enumerate(df.iloc[:, 0]):
                val_str = str(val)
                # Check for pattern: year followed by percentage
                combined_match = re.match(r'(\d{4})\s+([\d.]+%)', val_str)
                if combined_match:
                    year = combined_match.group(1)
                    pct = combined_match.group(2)

                    # Extract the year, shift other columns
                    row_vals = df.iloc[idx].tolist()

                    # Shift values: Year gets just the year, other cols shift right
                    new_row_vals = [year, pct] + row_vals[1:-1]
                    df.iloc[idx] = new_row_vals[:len(row_vals)]
                    was_fixed = True

        return df, was_fixed

    def create_chunks_from_items(self, items: List[dict], page_no: int, pdf_path: str) -> List[Document]:
        """
        Create chunks from items, grouping narrative and separating tables.

        Strategy:
        - Tables: One chunk per table
        - Narrative: Accumulate until ~1000 chars, then chunk
        - Preserve reading order

        Args:
            items: List of item dictionaries with 'type' and 'content' keys
            page_no: Page number (1-indexed)
            pdf_path: Path to PDF file

        Returns:
            List of Document chunks
        """
        chunks = []
        narrative_buffer = []
        narrative_chars = 0

        NARRATIVE_THRESHOLD = 1000
        NARRATIVE_MIN = 300  # Don't create tiny chunks

        for item in items:
            if item['type'] == 'table':
                # Flush narrative buffer first
                if narrative_buffer and narrative_chars >= NARRATIVE_MIN:
                    chunk_text = '\n\n'.join(narrative_buffer)
                    chunks.append(Document(
                        page_content=chunk_text,
                        metadata={
                            'source': pdf_path,
                            'page': page_no - 1,  # 0-indexed for compatibility
                            'format': 'markdown',
                            'extractor': 'docling',
                            'chunk_type': 'narrative'
                        }
                    ))
                    narrative_buffer = []
                    narrative_chars = 0

                # Create table chunk
                chunks.append(Document(
                    page_content=item['content'],
                    metadata={
                        'source': pdf_path,
                        'page': page_no - 1,  # 0-indexed for compatibility
                        'format': 'markdown',
                        'extractor': 'docling',
                        'chunk_type': 'table'
                    }
                ))

            elif item['type'] == 'text':
                text = item['content']
                item_size = len(text)

                # Case 1: Single item exceeds threshold - split it
                if item_size > NARRATIVE_THRESHOLD:
                    # Flush current buffer first
                    if narrative_buffer and narrative_chars >= NARRATIVE_MIN:
                        chunk_text = '\n\n'.join(narrative_buffer)
                        chunks.append(Document(
                            page_content=chunk_text,
                            metadata={
                                'source': pdf_path,
                                'page': page_no - 1,
                                'format': 'markdown',
                                'extractor': 'docling',
                                'chunk_type': 'narrative'
                            }
                        ))
                        narrative_buffer = []
                        narrative_chars = 0

                    # Split large narrative item using RecursiveCharacterTextSplitter
                    sub_chunks = self.text_splitter.split_text(text)
                    for sub_chunk in sub_chunks:
                        chunks.append(Document(
                            page_content=sub_chunk,
                            metadata={
                                'source': pdf_path,
                                'page': page_no - 1,
                                'format': 'markdown',
                                'extractor': 'docling',
                                'chunk_type': 'narrative'
                            }
                        ))

                # Case 2: Adding would exceed threshold - flush first
                elif narrative_chars + item_size >= NARRATIVE_THRESHOLD and narrative_buffer:
                    chunk_text = '\n\n'.join(narrative_buffer)
                    chunks.append(Document(
                        page_content=chunk_text,
                        metadata={
                            'source': pdf_path,
                            'page': page_no - 1,
                            'format': 'markdown',
                            'extractor': 'docling',
                            'chunk_type': 'narrative'
                        }
                    ))
                    narrative_buffer = [text]
                    narrative_chars = item_size

                # Case 3: Normal accumulation
                else:
                    narrative_buffer.append(text)
                    narrative_chars += item_size

        # Flush remaining narrative (even if below MIN to avoid losing content)
        if narrative_buffer:
            chunk_text = '\n\n'.join(narrative_buffer)
            chunks.append(Document(
                page_content=chunk_text,
                metadata={
                    'source': pdf_path,
                    'page': page_no - 1,  # 0-indexed for compatibility
                    'format': 'markdown',
                    'extractor': 'docling',
                    'chunk_type': 'narrative'
                }
            ))

        # Post-process: merge small chunks with previous chunk
        if len(chunks) >= 2:
            last_chunk = chunks[-1]
            if len(last_chunk.page_content) < NARRATIVE_MIN:
                # Merge with previous chunk
                prev_chunk = chunks[-2]
                merged_content = prev_chunk.page_content + '\n\n' + last_chunk.page_content
                chunks[-2] = Document(
                    page_content=merged_content,
                    metadata=prev_chunk.metadata
                )
                chunks.pop()  # Remove last chunk

        return chunks

    def extract_pdf_with_docling(self, pdf_path: str) -> List[Document]:
        """
        Extract PDF content using Docling with item-level chunking.
        Returns chunks in reading order with one chunk per semantic unit.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of LangChain Document chunks with markdown content
        """
        try:
            # Convert PDF using Docling
            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            doc = result.document

            # Get total pages
            num_pages = doc.num_pages()
            logger.info(f"  Docling extracted {num_pages} pages")

            # Group items by page and collect with position info for sorting
            page_items = {i: [] for i in range(1, num_pages + 1)}

            # Collect text items (doc.texts is already in reading order)
            for text_index, text_item in enumerate(doc.texts):
                if hasattr(text_item, 'prov') and text_item.prov:
                    page_no = text_item.prov[0].page_no
                    if page_no in page_items:
                        # Get bbox for position (PDF coords: origin at bottom-left, y decreases down page)
                        bbox = text_item.prov[0].bbox if hasattr(text_item.prov[0], 'bbox') else None
                        y_pos = bbox.t if bbox else 0

                        page_items[page_no].append({
                            'type': 'text',
                            'content': text_item.text,
                            'prov': text_item.prov,
                            'y_pos': y_pos,
                            'order': text_index  # Keep original order from doc.texts
                        })

            # Collect table items (doc.tables is already in reading order)
            for table_index, table_item in enumerate(doc.tables):
                if hasattr(table_item, 'prov') and table_item.prov:
                    page_no = table_item.prov[0].page_no
                    if page_no in page_items:
                        # Process table with column rotation fix
                        try:
                            import pandas as pd

                            df = table_item.export_to_dataframe(doc)
                            df_fixed, was_fixed = self.fix_rotated_columns(df)

                            if was_fixed:
                                logger.info(f"  🔧 Fixing rotated columns in table on page {page_no}")

                            table_md = df_fixed.to_markdown(index=False)

                        except Exception as e:
                            # Fallback to direct markdown export if DataFrame conversion fails
                            logger.warning(f"  DataFrame conversion failed on page {page_no}: {e}")
                            table_md = table_item.export_to_markdown(doc)

                        # Get bbox for position (PDF coords: origin at bottom-left, y decreases down page)
                        bbox = table_item.prov[0].bbox if hasattr(table_item.prov[0], 'bbox') else None
                        y_pos = bbox.t if bbox else 0

                        page_items[page_no].append({
                            'type': 'table',
                            'content': table_md,
                            'prov': table_item.prov,
                            'y_pos': y_pos,
                            'order': table_index + 10000  # Offset to keep tables after texts if same y_pos
                        })

            # Sort items by y-position DESCENDING (PDF coords: higher y = higher on page)
            # This preserves reading order (top to bottom)
            for page_no in page_items:
                page_items[page_no].sort(key=lambda item: (-item['y_pos'], item['order']))

            # Convert items to chunks (item-level chunking)
            documents = []
            for page_no in range(1, num_pages + 1):
                if not page_items[page_no]:
                    logger.debug(f"  Page {page_no} has no content, skipping")
                    continue

                page_docs = self.create_chunks_from_items(
                    page_items[page_no],
                    page_no,
                    pdf_path
                )
                documents.extend(page_docs)

                # Log chunk breakdown for this page
                table_chunks = sum(1 for d in page_docs if d.metadata.get('chunk_type') == 'table')
                narrative_chunks = sum(1 for d in page_docs if d.metadata.get('chunk_type') == 'narrative')
                logger.info(f"  📄 Page {page_no}: {len(page_docs)} chunks ({table_chunks} tables, {narrative_chunks} narrative)")

            logger.info(f"  ✅ Created {len(documents)} chunks from {num_pages} pages")
            return documents

        except Exception as e:
            logger.error(f"Docling extraction failed for {pdf_path}: {e}")
            logger.warning(f"Falling back to PyMuPDF for {pdf_path}")
            return self.extract_pdf_with_pymupdf(pdf_path)

    def delete_pdf_chunks(self):
        """Delete all chunks for this PDF from Qdrant."""
        logger.info(f"Deleting all chunks for: {self.pdf_filename}")

        try:
            # Scroll through all points and filter in Python
            # (Qdrant requires index for keyword filtering, simpler to filter locally)
            logger.info("Scrolling through collection to find matching chunks...")

            point_ids = []
            offset = None
            batch_size = 100

            while True:
                result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,  # Need payload to check 'doc' field
                    with_vectors=False
                )

                points, next_offset = result

                if not points:
                    break

                # Filter points that match our PDF
                # Check both 'doc' and 'filename' fields for backward compatibility
                for point in points:
                    if point.payload:
                        doc_value = point.payload.get('doc', '')
                        filename_value = point.payload.get('filename', '')
                        if doc_value == self.pdf_filename or filename_value == self.pdf_filename:
                            point_ids.append(point.id)

                if next_offset is None:
                    break

                offset = next_offset

            if point_ids:
                logger.info(f"Found {len(point_ids)} chunks to delete")
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                logger.info(f"✓ Deleted {len(point_ids)} chunks")
            else:
                logger.warning(f"No chunks found for {self.pdf_filename}")

            return len(point_ids)

        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise

    def process_pdf(self, pdf_path: str) -> List[Document]:
        """
        Process a single PDF file.

        Args:
            pdf_path: Full path to PDF file

        Returns:
            List of Document chunks
        """
        try:
            logger.info(f"Processing: {pdf_path}")

            # Check if PDF is in table whitelist (config.TABLE_PDFS)
            has_table = self.pdf_filename in config.TABLE_PDFS

            if has_table:
                logger.info(f"✓ PDF in table whitelist, using Docling")
                pages = self.extract_pdf_with_docling(pdf_path)
            else:
                logger.info(f"→ Standard PDF, using PyMuPDF")
                pages = self.extract_pdf_with_pymupdf(pdf_path)

            # Determine total pages for metadata
            is_docling = pages and pages[0].metadata.get('extractor') == 'docling'
            if is_docling:
                # For Docling, count unique pages in metadata
                unique_pages = set(doc.metadata.get('page', 0) for doc in pages)
                total_pages = len(unique_pages)
            else:
                # For PyMuPDF, len(pages) = pages since it's 1 doc per page
                total_pages = len(pages)

            logger.info(f"Loaded {total_pages} pages")

            # Clean page content
            for page in pages:
                page.page_content = clean_text(page.page_content)

            # Enrich metadata to match bulk loader format
            for page in pages:
                page.metadata['filename'] = self.pdf_filename
                page.metadata['content_type'] = 'pdf'

            # Split into chunks
            # Docling PDFs are already chunked at item level
            # PyMuPDF PDFs need chunking
            if is_docling:
                # Docling already returned item-level chunks, use as-is
                chunks = pages
                table_chunks = sum(1 for d in pages if d.metadata.get('chunk_type') == 'table')
                narrative_chunks = sum(1 for d in pages if d.metadata.get('chunk_type') == 'narrative')
                logger.info(f"Docling PDF: {total_pages} pages → {len(chunks)} chunks ({table_chunks} tables, {narrative_chunks} narrative)")
            elif len(pages) == 1:
                chunks = pages  # Don't split, use entire page as one chunk
                page_chars = len(pages[0].page_content)
                logger.info(f"Single-page PDF: loading as 1 chunk ({page_chars} characters)")
            else:
                chunks = self.text_splitter.split_documents(pages)
                logger.info(f"Multi-page PDF ({len(pages)} pages): split into {len(chunks)} chunks")

            # Filter out TOC chunks
            original_count = len(chunks)
            chunks = [chunk for chunk in chunks if not is_likely_toc(chunk.page_content)]
            filtered_count = original_count - len(chunks)

            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} TOC chunks ({filtered_count/original_count*100:.1f}%)")

            logger.info(f"Created {len(chunks)} chunks after filtering")

            # Add chunk index to metadata (re-index after filtering)
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
                chunk.metadata['total_chunks'] = len(chunks)

            # Add contextual metadata if enabled
            if self.contextual_mode and self.contextual_processor:
                logger.info("Generating contextual metadata...")

                # Generate document context
                full_text = "\n\n".join([page.page_content for page in pages])
                pdf_id = self.pdf_filename
                document_title = self.pdf_filename.replace('.pdf', '').replace('-', ' ').title()
                first_2000_chars = full_text[:2000]

                document_context = self.contextual_processor.generate_document_context(
                    pdf_id=pdf_id,
                    document_title=document_title,
                    total_pages=len(pages),
                    first_2000_chars=first_2000_chars
                )

                # Prepare chunks for context generation (need dict format)
                chunks_for_context = []
                total_chunks = len(chunks)
                for i, chunk in enumerate(chunks):
                    chunks_for_context.append({
                        'page_num': chunk.metadata.get('page', 0) + 1,  # 1-indexed
                        'total_pages': len(pages),
                        'chunk_index': i,
                        'total_chunks': total_chunks,
                        'chunk_text': chunk.page_content,
                    })

                # Generate chunk contexts
                chunk_contexts = self.contextual_processor.generate_all_chunk_contexts(
                    chunks_for_context,
                    document_context
                )

                # Add contexts to chunk metadata
                for i, chunk in enumerate(chunks):
                    chunk.metadata['master_context'] = MASTER_CONTEXT
                    chunk.metadata['document_context'] = document_context
                    chunk.metadata['has_context'] = True

                    if chunk_contexts and i in chunk_contexts:
                        chunk.metadata['chunk_context'] = chunk_contexts[i]
                    else:
                        chunk.metadata['chunk_context'] = None

                logger.info("✓ Contextual metadata generated")

            return chunks

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise

    def upload_chunks(self, chunks: List[Document]):
        """Upload chunks to Qdrant."""
        if not chunks:
            logger.warning("No chunks to upload")
            return

        logger.info(f"Uploading {len(chunks)} chunks to Qdrant...")

        try:
            # Store original content before any modifications
            original_contents = [chunk.page_content for chunk in chunks]

            # Prepare content for embedding (may include context)
            texts_for_embedding = []

            # Generate embeddings from enriched text if in contextual mode
            if self.contextual_mode and chunks:
                logger.info("Building enriched text for embeddings (contextual mode)...")

                for i, chunk in enumerate(chunks):
                    # Build enriched text for embedding ONLY (matches full pipeline logic)
                    # This improves embedding relevance but isn't stored in page_content
                    enriched_for_embedding = ""

                    if chunk.metadata.get('master_context'):
                        enriched_for_embedding = chunk.metadata['master_context']

                    if chunk.metadata.get('document_context'):
                        if enriched_for_embedding:
                            enriched_for_embedding += "\n\n"
                        enriched_for_embedding += chunk.metadata['document_context']

                    if chunk.metadata.get('chunk_context'):
                        if enriched_for_embedding:
                            enriched_for_embedding += "\n\n"
                        enriched_for_embedding += chunk.metadata['chunk_context']

                    # Add original content at the end
                    if enriched_for_embedding:
                        enriched_for_embedding += "\n\n"
                    enriched_for_embedding += original_contents[i]

                    texts_for_embedding.append(enriched_for_embedding)

                logger.info("Using enriched context for embeddings, but storing only original content")
            else:
                # Non-contextual mode: use original content as-is
                texts_for_embedding = original_contents.copy()

            # Generate embeddings from potentially enriched text
            embeddings = self.embeddings.embed_documents(texts_for_embedding)

            # Prepare points (always use original content in payload, not enriched)
            from qdrant_client.models import PointStruct
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_id = hash(f"{self.pdf_filename}_{i}_{chunk.metadata.get('page', 0)}")
                # Make sure point_id is positive
                if point_id < 0:
                    point_id = abs(point_id)

                # Ensure page_content is original (not enriched with contexts)
                chunk.page_content = original_contents[i]

                # Use metadata spread to include all fields (matches full pipeline)
                payload = {
                    'text': chunk.page_content,
                    **chunk.metadata
                }

                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                ))

            # Upload in batches
            batch_size = config.UPLOAD_BATCH_SIZE
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.info(f"Uploaded batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")

            logger.info(f"✓ Successfully uploaded {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"Error uploading chunks: {e}")
            raise

    def reload(self, pdf_path: str):
        """
        Full surgical reload: delete old chunks and upload new ones.

        Args:
            pdf_path: Full path to PDF file
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"SURGICAL RELOAD: {self.pdf_filename}")
        logger.info(f"{'='*60}\n")

        # Step 1: Delete old chunks
        deleted_count = self.delete_pdf_chunks()

        # Step 2: Process PDF with FIXED text cleaner
        chunks = self.process_pdf(pdf_path)

        # Step 3: Upload new chunks
        self.upload_chunks(chunks)

        logger.info(f"\n{'='*60}")
        logger.info(f"RELOAD COMPLETE")
        logger.info(f"Deleted: {deleted_count} old chunks")
        logger.info(f"Uploaded: {len(chunks)} new chunks")
        logger.info(f"{'='*60}\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python reload_single_pdf.py <pdf_filename>")
        print("Example: python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf")
        sys.exit(1)

    pdf_filename = sys.argv[1]

    # Find the PDF file
    pdf_dir = config.PDFS_DIR
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found: {pdf_path}")
        sys.exit(1)

    logger.info(f"Found PDF: {pdf_path}")

    # Create reloader and execute
    reloader = SinglePDFReloader(pdf_filename=pdf_filename, contextual_mode=True)
    reloader.reload(pdf_path)

    logger.info("✓ Surgical reload complete!")


if __name__ == '__main__':
    main()
