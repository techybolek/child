"""
Site mapping module for Texas Child Care Solutions scraper
Analyzes site structure and creates navigation maps
"""

import os
import json
import logging
from typing import Dict, List, Any, Set
from collections import defaultdict

import config

# Set up logging
logger = logging.getLogger(__name__)


class SiteMapper:
    """Analyzes scraped content and creates site structure maps."""

    def __init__(self, pages_dir: str = None, pdfs_dir: str = None):
        """
        Initialize site mapper.

        Args:
            pages_dir: Directory containing scraped page JSON files
            pdfs_dir: Directory containing extracted PDF JSON files
        """
        self.pages_dir = pages_dir or config.PAGES_DIR
        self.pdfs_dir = pdfs_dir or config.PDFS_DIR

    def is_document(self, page: Dict[str, Any]) -> bool:
        """
        Check if a page is a document (.docx or .xlsx).

        Args:
            page: Page data dictionary

        Returns:
            True if page is a document
        """
        content_type = page.get('content_type', '')
        return content_type in ['docx', 'xlsx']

    def load_all_pages(self, exclude_documents: bool = False) -> List[Dict[str, Any]]:
        """
        Load all scraped page data.

        Args:
            exclude_documents: If True, exclude .docx and .xlsx documents

        Returns:
            List of page data dictionaries
        """
        pages = []

        # Load regular pages
        if os.path.exists(self.pages_dir):
            for filename in os.listdir(self.pages_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.pages_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            pages.append(data)
                    except Exception as e:
                        logger.error(f"Failed to load {filepath}: {e}")

        # Load PDFs
        if os.path.exists(self.pdfs_dir):
            for filename in os.listdir(self.pdfs_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.pdfs_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            pages.append(data)
                    except Exception as e:
                        logger.error(f"Failed to load {filepath}: {e}")

        # Filter out documents if requested
        if exclude_documents:
            original_count = len(pages)
            pages = [page for page in pages if not self.is_document(page)]
            documents_excluded = original_count - len(pages)
            logger.info(f"Loaded {len(pages)} pages ({documents_excluded} documents excluded)")
        else:
            logger.info(f"Loaded {len(pages)} total pages")

        return pages

    def load_all_documents(self) -> List[Dict[str, Any]]:
        """
        Load only document files (.docx and .xlsx).

        Returns:
            List of document data dictionaries
        """
        all_pages = self.load_all_pages(exclude_documents=False)
        documents = [page for page in all_pages if self.is_document(page)]
        logger.info(f"Loaded {len(documents)} documents")
        return documents

    def classify_page_type(self, page: Dict[str, Any]) -> str:
        """
        Classify page as hub (navigation-heavy) or content.

        Args:
            page: Page data dictionary

        Returns:
            'hub', 'content', or 'pdf'
        """
        # PDFs are always content
        if page.get('content_type') == 'pdf':
            return 'pdf'

        word_count = page.get('word_count', 0)
        links = page.get('links', [])
        link_count = len(links)

        # Calculate content-to-link ratio
        if word_count == 0:
            return 'hub'

        ratio = word_count / max(link_count, 1)

        # If very few words per link, it's a hub page
        if ratio < 50:  # Less than 50 words per link
            return 'hub'
        else:
            return 'content'

    def analyze_site_structure(self) -> Dict[str, Any]:
        """
        Analyze site structure and create a map.

        Returns:
            Site map dictionary
        """
        pages = self.load_all_pages()

        # Initialize structure
        site_map = {
            'hub_pages': [],
            'content_pages': [],
            'pdf_documents': [],
            'external_resources': defaultdict(list),
            'domain_stats': defaultdict(int),
            'total_pages': len(pages),
        }

        # Classify and organize pages
        for page in pages:
            url = page.get('url', page.get('source_url', ''))
            title = page.get('title', page.get('filename', ''))
            domain = page.get('domain', page.get('source_domain', ''))
            page_type = self.classify_page_type(page)

            # Count by domain
            site_map['domain_stats'][domain] += 1

            # Add to appropriate category
            if page_type == 'hub':
                links_to = [link['url'] for link in page.get('links', [])]
                site_map['hub_pages'].append({
                    'url': url,
                    'title': title,
                    'domain': domain,
                    'link_count': len(links_to),
                    'word_count': page.get('word_count', 0),
                    'links_to': links_to[:20],  # Limit to first 20 links
                })

            elif page_type == 'content':
                site_map['content_pages'].append({
                    'url': url,
                    'title': title,
                    'domain': domain,
                    'word_count': page.get('word_count', 0),
                })

            elif page_type == 'pdf':
                site_map['pdf_documents'].append({
                    'url': url,
                    'filename': title,
                    'domain': domain,
                    'word_count': page.get('word_count', 0),
                })

            # Track external resources by domain
            for link in page.get('links', []):
                link_url = link.get('url', '')
                if link_url and domain in link_url:
                    # Internal link, skip
                    continue
                # External link
                # Extract domain from link
                try:
                    from urllib.parse import urlparse
                    link_domain = urlparse(link_url).netloc
                    if link_domain and link_domain not in config.ALLOWED_DOMAINS:
                        site_map['external_resources'][link_domain].append({
                            'url': link_url,
                            'text': link.get('text', ''),
                            'from_page': url,
                        })
                except Exception:
                    pass

        # Convert defaultdict to regular dict for JSON serialization
        site_map['external_resources'] = dict(site_map['external_resources'])
        site_map['domain_stats'] = dict(site_map['domain_stats'])

        # Add summary stats
        site_map['summary'] = {
            'hub_pages': len(site_map['hub_pages']),
            'content_pages': len(site_map['content_pages']),
            'pdf_documents': len(site_map['pdf_documents']),
            'unique_domains': len(site_map['domain_stats']),
            'external_domains_referenced': len(site_map['external_resources']),
        }

        logger.info(f"Site map created: {site_map['summary']}")

        return site_map

    def save_site_map(self, site_map: Dict[str, Any], output_file: str = None):
        """
        Save site map to JSON file.

        Args:
            site_map: Site map dictionary
            output_file: Output file path
        """
        output_file = output_file or config.SITE_MAP_FILE

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(site_map, f, indent=2, ensure_ascii=False)

        logger.info(f"Site map saved to {output_file}")

    def generate_site_map(self, output_file: str = None) -> Dict[str, Any]:
        """
        Convenience method to analyze and save site map.

        Args:
            output_file: Output file path

        Returns:
            Site map dictionary
        """
        site_map = self.analyze_site_structure()
        self.save_site_map(site_map, output_file)
        return site_map


# Convenience function
def create_site_map(pages_dir: str = None, output_file: str = None) -> Dict[str, Any]:
    """
    Quick function to create a site map.

    Args:
        pages_dir: Directory containing scraped pages
        output_file: Output file path

    Returns:
        Site map dictionary
    """
    mapper = SiteMapper(pages_dir)
    return mapper.generate_site_map(output_file)


if __name__ == '__main__':
    # Test the site mapper
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)

    mapper = SiteMapper()
    site_map = mapper.generate_site_map()

    print("\n=== Site Map Summary ===")
    for key, value in site_map.get('summary', {}).items():
        print(f"{key}: {value}")

    print("\n=== Domain Statistics ===")
    for domain, count in site_map.get('domain_stats', {}).items():
        print(f"{domain}: {count} pages")
