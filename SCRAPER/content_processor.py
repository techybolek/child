"""
Content processing module for Texas Child Care Solutions scraper
Handles text cleaning, intelligent chunking, and content classification
"""

import re
import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

import config

# Set up logging
logger = logging.getLogger(__name__)


class ContentProcessor:
    """Handles content cleaning, chunking, and classification."""

    def __init__(self):
        """Initialize content processor."""
        self.chunk_min_words = config.CHUNK_MIN_WORDS
        self.chunk_max_words = config.CHUNK_MAX_WORDS
        self.overlap_words = config.CHUNK_OVERLAP_WORDS
        self.content_type_rules = config.CONTENT_TYPE_RULES

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common navigation artifacts
        artifacts = [
            'Skip to content',
            'Skip to main content',
            'Skip navigation',
            'Jump to content',
            'Click here to',
            'Print this page',
            'Share this page',
        ]
        for artifact in artifacts:
            text = text.replace(artifact, '')

        # Fix common encoding issues
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2019', "'")  # Right single quotation mark
        text = text.replace('\u201c', '"')  # Left double quotation mark
        text = text.replace('\u201d', '"')  # Right double quotation mark
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '--') # Em dash

        # Remove excessive punctuation
        text = re.sub(r'\.{3,}', '...', text)
        text = re.sub(r'-{3,}', '---', text)

        # Clean up multiple spaces again after replacements
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences (simple approach).

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting (not perfect but sufficient)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_by_headings(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Attempt to chunk text by headings/sections.

        Args:
            text: Text to chunk
            metadata: Base metadata for chunks

        Returns:
            List of chunks with metadata
        """
        # Look for heading patterns (markdown-style or numbered)
        heading_pattern = r'(?:^|\n)(#{1,3}\s+.*?|[A-Z][A-Za-z\s]{3,30}:|\d+\.\s+[A-Z][A-Za-z\s]{3,50})'

        sections = re.split(heading_pattern, text)

        if len(sections) <= 2:
            # No clear headings found, fall back to size-based chunking
            return self.chunk_by_size(text, metadata)

        chunks = []
        current_heading = None

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # Check if this looks like a heading
            if (re.match(r'^#{1,3}\s+', section) or
                re.match(r'^[A-Z][A-Za-z\s]{3,30}:$', section) or
                re.match(r'^\d+\.\s+[A-Z]', section)):
                current_heading = section
            else:
                # This is content under a heading
                word_count = len(section.split())

                if word_count >= self.chunk_min_words:
                    chunk_meta = metadata.copy()
                    chunk_meta['section_heading'] = current_heading or 'Introduction'
                    chunk_meta['word_count'] = word_count

                    chunks.append({
                        'text': section,
                        'metadata': chunk_meta
                    })

        return chunks if chunks else self.chunk_by_size(text, metadata)

    def chunk_by_size(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk text by size with overlap.

        Args:
            text: Text to chunk
            metadata: Base metadata for chunks

        Returns:
            List of chunks with metadata
        """
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = sentence.split()
            sentence_word_count = len(sentence_words)

            # If adding this sentence would exceed max, save current chunk
            if current_word_count + sentence_word_count > self.chunk_max_words and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_meta = metadata.copy()
                chunk_meta['word_count'] = current_word_count

                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_meta
                })

                # Start new chunk with overlap
                overlap_text = ' '.join(current_chunk[-self.overlap_words:]) if len(current_chunk) > self.overlap_words else ''
                current_chunk = [overlap_text] if overlap_text else []
                current_word_count = len(overlap_text.split())

            current_chunk.append(sentence)
            current_word_count += sentence_word_count

        # Add final chunk if it meets minimum size
        if current_chunk and current_word_count >= self.chunk_min_words:
            chunk_text = ' '.join(current_chunk)
            chunk_meta = metadata.copy()
            chunk_meta['word_count'] = current_word_count

            chunks.append({
                'text': chunk_text,
                'metadata': chunk_meta
            })

        return chunks

    def classify_content_type(self, text: str, url: str = '') -> str:
        """
        Classify content type based on keywords.

        Args:
            text: Text to classify
            url: Optional URL for additional context

        Returns:
            Content type string
        """
        text_lower = text.lower()
        url_lower = url.lower()

        # Count keyword matches for each type
        scores = {}
        for content_type, keywords in self.content_type_rules.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text_lower)
            # Boost score if content type appears in URL
            if content_type.replace('_', '-') in url_lower:
                score += 2
            scores[content_type] = score

        # Get the type with highest score
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                return max(scores, key=scores.get)

        # Default to general if no clear type
        return 'general'

    def generate_chunk_id(self, url: str, chunk_index: int) -> str:
        """Generate a unique ID for a chunk."""
        unique_string = f"{url}_{chunk_index}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]

    def process_page_content(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a page's raw content into chunks.

        Args:
            raw_data: Dictionary with 'text', 'url', 'title', etc.

        Returns:
            List of chunk dictionaries ready for vector DB
        """
        text = raw_data.get('text', '')
        url = raw_data.get('url', '')
        title = raw_data.get('title', '')
        source_domain = raw_data.get('domain', '')

        if not text:
            logger.warning(f"No text content for URL: {url}")
            return []

        # Clean the text
        cleaned_text = self.clean_text(text)
        word_count = len(cleaned_text.split())

        # Skip if too short
        if word_count < config.MIN_CONTENT_WORDS:
            logger.info(f"Skipping thin content ({word_count} words): {url}")
            return []

        # Base metadata
        base_metadata = {
            'source_url': url,
            'source_domain': source_domain,
            'page_title': title,
            'scraped_date': config.SCRAPE_TIMESTAMP,
        }

        # Chunk the content
        if word_count < self.chunk_max_words:
            # Small enough to be a single chunk
            chunks = [{
                'text': cleaned_text,
                'metadata': {
                    **base_metadata,
                    'word_count': word_count,
                    'chunk_index': 0,
                    'section_heading': title
                }
            }]
        else:
            # Need to chunk
            chunks = self.chunk_by_headings(cleaned_text, base_metadata)

        # Add content type and chunk ID to each chunk
        final_chunks = []
        for i, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = i
            chunk['metadata']['content_type'] = self.classify_content_type(
                chunk['text'],
                url
            )
            chunk['metadata']['chunk_id'] = self.generate_chunk_id(url, i)
            final_chunks.append(chunk)

        logger.info(f"Created {len(final_chunks)} chunks from {url}")
        return final_chunks

    def deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate chunks based on text similarity.

        Args:
            chunks: List of chunks

        Returns:
            Deduplicated list of chunks
        """
        seen_texts = set()
        unique_chunks = []

        for chunk in chunks:
            # Create a normalized version for comparison
            text = chunk.get('text', '')
            normalized = re.sub(r'\s+', ' ', text.lower().strip())

            # Use first 100 characters as fingerprint
            fingerprint = normalized[:100]

            if fingerprint not in seen_texts:
                seen_texts.add(fingerprint)
                unique_chunks.append(chunk)
            else:
                logger.debug(f"Skipping duplicate chunk from {chunk['metadata'].get('source_url')}")

        logger.info(f"Deduplicated {len(chunks)} chunks to {len(unique_chunks)} unique chunks")
        return unique_chunks

    def format_for_vector_db(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format chunks in the final structure for vector DB.

        Args:
            chunks: List of chunks with text and metadata

        Returns:
            List of formatted chunks
        """
        formatted = []

        for chunk in chunks:
            formatted.append({
                'chunk_id': chunk['metadata']['chunk_id'],
                'text': chunk['text'],
                'metadata': chunk['metadata']
            })

        return formatted


# Convenience function
def process_content(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Quick function to process raw page content.

    Args:
        raw_data: Dictionary with page content and metadata

    Returns:
        List of processed chunks
    """
    processor = ContentProcessor()
    return processor.process_page_content(raw_data)


if __name__ == '__main__':
    # Test the processor
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)

    test_data = {
        'url': 'https://example.com/test',
        'title': 'Test Page',
        'domain': 'example.com',
        'text': '''
        Eligibility Requirements

        To qualify for child care assistance, families must meet income requirements.
        The income limits vary based on family size. Families receiving TANF or other
        public assistance may automatically qualify. Parents must be working or attending
        education or training programs to be eligible.

        How to Apply

        To apply for child care services, visit the online portal at childcare.texas.gov.
        You will need to create an account and provide documentation of income, employment,
        and family size. The application process takes approximately 30 days.
        ''' * 5  # Repeat to make it longer
    }

    processor = ContentProcessor()
    chunks = processor.process_page_content(test_data)

    print(f"\nCreated {len(chunks)} chunks:")
    for chunk in chunks:
        meta = chunk['metadata']
        print(f"\n- Chunk {meta['chunk_index']}: {meta['word_count']} words, "
              f"type: {meta['content_type']}")
        print(f"  First 100 chars: {chunk['text'][:100]}...")
