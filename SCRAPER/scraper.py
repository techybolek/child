"""
Main scraper module for Texas Child Care Solutions
Handles URL queue management, fetching, and content extraction
"""

import os
import json
import time
import logging
import hashlib
import requests
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from typing import Set, Dict, Any, Optional, List
from collections import deque

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import config
from pdf_extractor import PDFExtractor
from document_extractor import DocumentExtractor

# Set up logging
logger = logging.getLogger(__name__)


class WebScraper:
    """Main web scraper class with multi-mode fetching."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize the web scraper.

        Args:
            dry_run: If True, limit scraping to a small number of pages
        """
        self.dry_run = dry_run
        self.max_pages = config.DRY_RUN_MAX_PAGES if dry_run else config.MAX_PAGES

        # URL tracking
        self.visited_urls: Set[str] = set()
        self.queued_urls: deque = deque()
        self.failed_urls: Dict[str, str] = {}

        # Robots.txt parsers per domain
        self.robots_parsers: Dict[str, RobotFileParser] = {}

        # Statistics
        self.stats = {
            'pages_scraped': 0,
            'pages_skipped': 0,
            'pdfs_downloaded': 0,
            'pdfs_excluded': 0,
            'documents_downloaded': 0,
            'errors': 0,
            'start_time': time.time(),
        }

        # PDF extractor
        self.pdf_extractor = PDFExtractor()

        # Document extractor
        self.document_extractor = DocumentExtractor()

        # Request session
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})

        # Playwright browser (lazy initialization)
        self.playwright = None
        self.browser = None

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        parsed = urlparse(url)
        # Remove fragments and common tracking parameters
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            # Keep query but normalize
            url += f"?{parsed.query}"
        return url.rstrip('/')

    def _should_scrape_url(self, url: str) -> bool:
        """Check if URL should be scraped based on rules."""
        # Check if already visited
        normalized = self._normalize_url(url)
        if normalized in self.visited_urls:
            return False

        # Check domain allowlist
        domain = self._get_domain(url)
        if not config.should_process_domain(domain):
            return False

        # Check TWC-specific patterns
        if not config.is_twc_child_care_url(url):
            logger.debug(f"Skipping non-child-care TWC URL: {url}")
            return False

        # Check robots.txt
        if not self._is_allowed_by_robots(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return False

        return True

    def _is_allowed_by_robots(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        domain = self._get_domain(url)

        # Get or create robots parser for this domain
        if domain not in self.robots_parsers:
            robot_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robot_url)
            try:
                parser.read()
                self.robots_parsers[domain] = parser
            except Exception as e:
                logger.warning(f"Could not read robots.txt for {domain}: {e}")
                # If we can't read robots.txt, allow the URL
                self.robots_parsers[domain] = None
                return True

        parser = self.robots_parsers[domain]
        if parser is None:
            return True

        return parser.can_fetch(config.USER_AGENT, url)

    def _fetch_with_requests(self, url: str) -> Optional[str]:
        """Fetch URL using requests library."""
        try:
            logger.debug(f"Fetching with requests: {url}")
            response = self.session.get(
                url,
                timeout=config.TIMEOUT_PER_PAGE,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text

        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright (for JavaScript-heavy pages)."""
        try:
            # Lazy initialization of Playwright
            if self.playwright is None:
                logger.info("Initializing Playwright browser...")
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(
                    headless=config.PLAYWRIGHT_HEADLESS
                )

            logger.debug(f"Fetching with Playwright: {url}")
            page = self.browser.new_page()
            page.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT, wait_until='networkidle')

            # Wait a bit for any dynamic content
            time.sleep(2)

            html = page.content()
            page.close()

            return html

        except PlaywrightTimeout:
            logger.error(f"Playwright timeout for {url}")
            return None
        except Exception as e:
            logger.error(f"Playwright failed for {url}: {e}")
            return None

    def fetch_page(self, url: str, use_playwright: bool = False) -> Optional[str]:
        """
        Fetch a page's HTML content.

        Args:
            url: URL to fetch
            use_playwright: Force use of Playwright for JavaScript rendering

        Returns:
            HTML content or None if failed
        """
        # Check if it's a PDF
        if self.pdf_extractor.is_pdf_url(url):
            logger.info(f"PDF URL detected, skipping HTML fetch: {url}")
            return None

        # Use appropriate fetcher
        if use_playwright or 'childcare.twc.texas.gov' in url:
            html = self._fetch_with_playwright(url)
        else:
            html = self._fetch_with_requests(url)

        return html

    def extract_content(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract main content and metadata from HTML.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            Dictionary with extracted content and metadata
        """
        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else ''

        # Remove unwanted elements
        for tag_name in config.TAGS_TO_REMOVE:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove elements by selectors
        for selector in config.SELECTORS_TO_REMOVE:
            for element in soup.select(selector):
                element.decompose()

        # Remove text from PDF/document links to prevent titles polluting content
        # (but keep the link element for discovery)
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].lower()
            if (href.endswith('.pdf') or href.endswith('.docx') or
                href.endswith('.xlsx') or href.endswith('.doc') or
                href.endswith('.xls') or '/pdf/' in href):
                a_tag.string = ''  # Clear the link text but keep the element

        # Extract main content
        # Try to find main content area
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # If no main content area found, use body
        if not main_content:
            main_content = soup.find('body')

        # Extract text
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)

        # Extract links
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_url = urljoin(url, href)
            link_text = a_tag.get_text().strip()

            links.append({
                'url': absolute_url,
                'text': link_text
            })

        # Build result
        result = {
            'url': url,
            'title': title,
            'text': text,
            'word_count': len(text.split()),
            'links': links,
            'domain': self._get_domain(url),
        }

        return result

    def discover_links(self, content: Dict[str, Any]) -> List[str]:
        """
        Discover new URLs from extracted content.

        Args:
            content: Content dictionary with links

        Returns:
            List of new URLs to scrape
        """
        new_urls = []
        links = content.get('links', [])

        for link in links:
            url = link['url']

            # Normalize and check if we should scrape
            if self._should_scrape_url(url):
                normalized = self._normalize_url(url)
                if normalized not in self.visited_urls and normalized not in self.queued_urls:
                    new_urls.append(normalized)

        return new_urls

    def save_page_content(self, content: Dict[str, Any]) -> str:
        """
        Save page content to disk.

        Args:
            content: Content dictionary

        Returns:
            Path to saved file
        """
        # Generate filename from URL
        url_hash = hashlib.md5(content['url'].encode()).hexdigest()
        filename = f"{url_hash}.json"
        filepath = os.path.join(config.PAGES_DIR, filename)

        # Save as JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved page content to {filepath}")
        return filepath

    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL.

        Args:
            url: URL to scrape

        Returns:
            Extracted content dictionary or None if failed
        """
        logger.info(f"Scraping: {url}")

        # Mark as visited
        normalized = self._normalize_url(url)
        self.visited_urls.add(normalized)

        # Check if document (.docx, .xlsx) FIRST (before PDF check)
        if self.document_extractor.is_document_url(url):
            logger.info(f"Downloading document: {url}")
            doc_metadata = self.document_extractor.process_document_url(url)

            if doc_metadata:
                self.stats['documents_downloaded'] += 1
                # Save document metadata
                url_hash = hashlib.md5(url.encode()).hexdigest()
                filename = f"{url_hash}_doc.json"
                filepath = os.path.join(config.DOCUMENTS_DIR, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(doc_metadata, f, indent=2, ensure_ascii=False)

                logger.info(f"Document downloaded: {doc_metadata['filename']} ({doc_metadata['file_size_mb']} MB)")
                return doc_metadata
            else:
                self.failed_urls[url] = "Document download failed"
                self.stats['errors'] += 1
                return None

        # Check if PDF
        if self.pdf_extractor.is_pdf_url(url):
            # Check if PDF is in exclusion list
            if config.is_excluded_pdf(url):
                logger.info(f"Skipping excluded PDF: {url}")
                self.stats['pdfs_excluded'] += 1
                return None

            logger.info(f"Downloading PDF: {url}")
            pdf_metadata = self.pdf_extractor.process_pdf_url(url)

            if pdf_metadata:
                self.stats['pdfs_downloaded'] += 1
                # Save PDF metadata
                url_hash = hashlib.md5(url.encode()).hexdigest()
                filename = f"{url_hash}_pdf.json"
                filepath = os.path.join(config.PDFS_DIR, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(pdf_metadata, f, indent=2, ensure_ascii=False)

                logger.info(f"PDF downloaded: {pdf_metadata['filename']} ({pdf_metadata['file_size_mb']} MB)")
                return pdf_metadata
            else:
                self.failed_urls[url] = "PDF download failed"
                self.stats['errors'] += 1
                return None

        # Fetch HTML
        html = self.fetch_page(url)
        if not html:
            self.failed_urls[url] = "Failed to fetch HTML"
            self.stats['errors'] += 1
            return None

        # Extract content
        content = self.extract_content(html, url)

        # Check word count threshold
        if content['word_count'] < config.MIN_CONTENT_WORDS:
            logger.info(f"Skipping thin content ({content['word_count']} words): {url}")
            self.stats['pages_skipped'] += 1
            return None

        # Save content
        self.save_page_content(content)
        self.stats['pages_scraped'] += 1

        # Discover new links
        new_links = self.discover_links(content)
        for link in new_links:
            if link not in self.queued_urls:
                self.queued_urls.append(link)

        logger.info(f"Found {len(new_links)} new links")

        return content

    def scrape(self, seed_urls: List[str]) -> Dict[str, Any]:
        """
        Main scraping method.

        Args:
            seed_urls: List of URLs to start scraping from

        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting scrape with {len(seed_urls)} seed URLs")
        logger.info(f"Dry run: {self.dry_run}, Max pages: {self.max_pages}")

        # Add seed URLs to queue
        for url in seed_urls:
            normalized = self._normalize_url(url)
            if normalized not in self.queued_urls:
                self.queued_urls.append(normalized)

        # Main scraping loop
        while self.queued_urls and self.stats['pages_scraped'] < self.max_pages:
            url = self.queued_urls.popleft()

            # Skip if somehow we've visited this
            if self._normalize_url(url) in self.visited_urls:
                continue

            try:
                # Scrape the URL
                content = self.scrape_url(url)

                # Rate limiting
                time.sleep(config.DELAY_BETWEEN_REQUESTS)

                # Progress update every 10 pages
                if self.stats['pages_scraped'] % 10 == 0:
                    self.print_progress()

            except Exception as e:
                logger.error(f"Unexpected error scraping {url}: {e}")
                self.failed_urls[url] = str(e)
                self.stats['errors'] += 1

        # Final progress
        self.print_progress()

        # Cleanup
        self.cleanup()

        # Calculate final stats
        elapsed = time.time() - self.stats['start_time']
        self.stats['elapsed_seconds'] = elapsed
        self.stats['total_visited'] = len(self.visited_urls)
        self.stats['queued_remaining'] = len(self.queued_urls)

        logger.info(f"Scraping complete. Visited {self.stats['total_visited']} URLs")

        return self.stats

    def print_progress(self):
        """Print current progress."""
        elapsed = time.time() - self.stats['start_time']
        logger.info(
            f"Progress: {self.stats['pages_scraped']} pages scraped, "
            f"{self.stats['documents_downloaded']} documents downloaded, "
            f"{self.stats['pdfs_downloaded']} PDFs downloaded, "
            f"{self.stats['pdfs_excluded']} PDFs excluded, "
            f"{self.stats['errors']} errors, "
            f"{len(self.queued_urls)} in queue, "
            f"{elapsed:.1f}s elapsed"
        )

    def cleanup(self):
        """Clean up resources."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

        self.session.close()


if __name__ == '__main__':
    # Test the scraper
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)

    scraper = WebScraper(dry_run=True)
    stats = scraper.scrape(config.SEED_URLS[:1])  # Test with first seed URL

    print("\n=== Scraping Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
