"""
Docling PDF extractor for tables and structured content with item-level chunking.
"""

import logging
from typing import List, Dict, Tuple
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


class DoclingExtractor:
    """Extract PDF content using Docling with item-level chunking for tables and narrative."""

    def __init__(self, text_splitter: RecursiveCharacterTextSplitter):
        """
        Initialize Docling extractor.

        Args:
            text_splitter: Text splitter for chunking large narrative items
        """
        self.text_splitter = text_splitter

    def fix_rotated_columns(self, df) -> Tuple:
        """
        Detect and fix rotated table columns.

        Args:
            df: pandas DataFrame

        Returns:
            Tuple of (fixed_df, was_fixed_bool)
        """
        import pandas as pd
        import re

        if len(df.columns) < 2:
            return df, False

        last_col = df.iloc[:, -1].astype(str)
        first_col = df.iloc[:, 0].astype(str)
        first_col_name = df.columns[0]

        # Pattern: years in last column (2012-2020)
        year_pattern = r'\b(19|20)\d{2}\b'
        has_years_in_last = last_col.str.contains(year_pattern, na=False, regex=True).sum() >= 2
        has_percentages_in_first = first_col.str.contains('%', na=False, regex=False).sum() >= 2

        if has_years_in_last and has_percentages_in_first and 'year' in first_col_name.lower():
            # Rotate columns: move last column to first
            cols = df.columns.tolist()
            df = df[[cols[-1]] + cols[:-1]]
            df.columns = cols
            return df, True

        return df, False

    def create_chunks_from_items(self, items: List[Dict], page_no: int, pdf_path: str) -> List[Document]:
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

    def extract(self, pdf_path: str) -> List[Document]:
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
            raise
