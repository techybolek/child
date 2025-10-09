"""
PDF extraction module for Texas Child Care Solutions scraper
Handles downloading and text extraction from PDF documents
"""

import os
import logging
import requests
import hashlib
from urllib.parse import urlparse
from typing import Optional, Dict, Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logging.warning("PyMuPDF not available. PDF extraction will be disabled.")

import config

# Set up logging
logger = logging.getLogger(__name__)


class PDFExtractor:
    """Handles PDF downloading and text extraction."""

    def __init__(self, output_dir: str = None):
        """
        Initialize PDF extractor.

        Args:
            output_dir: Directory to save extracted PDF text
        """
        self.output_dir = output_dir or config.PDFS_DIR
        self.user_agent = config.USER_AGENT
        self.max_size_bytes = config.MAX_PDF_SIZE_MB * 1024 * 1024
        self.timeout = config.TIMEOUT_PER_PAGE

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not installed. PDF extraction disabled.")

    def _generate_pdf_id(self, url: str) -> str:
        """Generate a unique ID for a PDF URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_filename_from_url(self, url: str) -> str:
        """Extract filename from URL."""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename or not filename.endswith('.pdf'):
            filename = f"{self._generate_pdf_id(url)}.pdf"
        return filename

    def download_pdf(self, url: str) -> Optional[str]:
        """
        Download PDF from URL.

        Args:
            url: URL of the PDF

        Returns:
            Path to downloaded PDF, or None if download failed
        """
        try:
            logger.info(f"Downloading PDF: {url}")

            # Make HEAD request to check size
            headers = {'User-Agent': self.user_agent}
            head_response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)

            # Check content type
            content_type = head_response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower():
                logger.warning(f"URL does not appear to be a PDF: {url} (Content-Type: {content_type})")
                # Continue anyway, sometimes servers don't report correctly

            # Check file size
            content_length = head_response.headers.get('Content-Length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if int(content_length) > self.max_size_bytes:
                    logger.warning(f"PDF too large ({size_mb:.1f} MB): {url}")
                    return None
                logger.info(f"PDF size: {size_mb:.1f} MB")

            # Download the PDF
            response = requests.get(url, headers=headers, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Save to file
            filename = self._get_filename_from_url(url)
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded PDF to: {filepath}")
            return filepath

        except requests.RequestException as e:
            logger.error(f"Failed to download PDF {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading PDF {url}: {e}")
            return None

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text, or None if extraction failed
        """
        if not PYMUPDF_AVAILABLE:
            logger.error("PyMuPDF not available. Cannot extract text.")
            return None

        try:
            logger.info(f"Extracting text from: {pdf_path}")

            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # Add page marker
                if text.strip():
                    text_parts.append(f"\n--- Page {page_num + 1} ---\n")
                    text_parts.append(text)

            doc.close()

            full_text = ''.join(text_parts)
            word_count = len(full_text.split())

            logger.info(f"Extracted {word_count} words from {len(doc)} pages")

            return full_text.strip()

        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return None

    def process_pdf_url(self, url: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Download and extract text from PDF URL.

        Args:
            url: URL of the PDF
            metadata: Optional metadata to include

        Returns:
            Dictionary with extracted content and metadata, or None if failed
        """
        pdf_id = self._generate_pdf_id(url)

        # Download PDF
        pdf_path = self.download_pdf(url)
        if not pdf_path:
            return None

        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return None

        # Build result
        result = {
            'pdf_id': pdf_id,
            'source_url': url,
            'filename': os.path.basename(pdf_path),
            'text': text,
            'word_count': len(text.split()),
            'content_type': 'pdf',
        }

        # Add additional metadata if provided
        if metadata:
            result.update(metadata)

        return result

    def is_pdf_url(self, url: str) -> bool:
        """
        Check if URL appears to be a PDF.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be a PDF
        """
        url_lower = url.lower()
        return url_lower.endswith('.pdf') or '/pdf/' in url_lower or 'filetype=pdf' in url_lower


# Convenience function for quick extraction
def extract_pdf(url: str, output_dir: str = None) -> Optional[Dict[str, Any]]:
    """
    Quick function to extract text from a PDF URL.

    Args:
        url: URL of the PDF
        output_dir: Directory to save extracted text

    Returns:
        Dictionary with extracted content and metadata
    """
    extractor = PDFExtractor(output_dir)
    return extractor.process_pdf_url(url)


if __name__ == '__main__':
    # Test the extractor
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)

    # Test URL (replace with actual PDF URL if needed)
    test_url = "https://www.twc.texas.gov/files/example.pdf"

    extractor = PDFExtractor()
    result = extractor.process_pdf_url(test_url)

    if result:
        print(f"Successfully extracted {result['word_count']} words from PDF")
        print(f"First 200 characters: {result['text'][:200]}")
    else:
        print("PDF extraction failed")
