"""
Main pipeline orchestration for Texas Child Care Solutions scraper
Coordinates scraping, processing, and analysis
"""

import os
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter

import config
from scraper import WebScraper
from content_processor import ContentProcessor
from site_mapper import SiteMapper

# Set up directories
def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        config.SCRAPED_CONTENT_DIR,
        config.RAW_DIR,
        config.PAGES_DIR,
        config.PDFS_DIR,
        config.DOCUMENTS_DIR,
        config.PROCESSED_DIR,
        config.REPORTS_DIR,
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Set up logging
def setup_logging(log_file: str = None):
    """Configure logging for the pipeline."""
    log_file = log_file or config.LOG_FILE

    # Create formatter
    formatter = logging.Formatter(config.LOG_FORMAT)

    # File handler
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


logger = logging.getLogger(__name__)


class ScrapingPipeline:
    """Main pipeline class that orchestrates the scraping process."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize the scraping pipeline.

        Args:
            dry_run: If True, limit to a small number of pages for testing
        """
        self.dry_run = dry_run
        self.scraper = WebScraper(dry_run=dry_run)
        self.processor = ContentProcessor()
        self.mapper = SiteMapper()

        self.scraping_stats = {}
        self.processing_stats = {}
        self.all_chunks = []

    def phase_1_scrape(self, seed_urls: List[str]) -> Dict[str, Any]:
        """
        Phase 1: Scrape websites.

        Args:
            seed_urls: List of URLs to start scraping from

        Returns:
            Scraping statistics
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: SCRAPING")
        logger.info("=" * 60)

        self.scraping_stats = self.scraper.scrape(seed_urls)

        logger.info(f"Scraping complete:")
        logger.info(f"  - Pages scraped: {self.scraping_stats['pages_scraped']}")
        logger.info(f"  - Documents downloaded: {self.scraping_stats.get('documents_downloaded', 0)}")
        logger.info(f"  - PDFs downloaded: {self.scraping_stats['pdfs_downloaded']}")
        logger.info(f"  - PDFs excluded: {self.scraping_stats.get('pdfs_excluded', 0)}")
        logger.info(f"  - Pages skipped (thin): {self.scraping_stats['pages_skipped']}")
        logger.info(f"  - Errors: {self.scraping_stats['errors']}")
        logger.info(f"  - Time: {self.scraping_stats['elapsed_seconds']:.1f}s")

        return self.scraping_stats

    def phase_2_process(self) -> List[Dict[str, Any]]:
        """
        Phase 2: Process scraped content into chunks.

        Returns:
            List of processed chunks
        """
        logger.info("=" * 60)
        logger.info("PHASE 2: CONTENT PROCESSING")
        logger.info("=" * 60)

        # Load all scraped pages (excluding documents if configured)
        exclude_docs = getattr(config, 'PROCESS_DOCUMENTS_SEPARATELY', False)
        pages = self.mapper.load_all_pages(exclude_documents=exclude_docs)

        if exclude_docs:
            logger.info(f"Processing {len(pages)} HTML pages (documents excluded for separate processing)")
        else:
            logger.info(f"Processing {len(pages)} total pages")

        # Process each page into chunks
        all_chunks = []
        for i, page in enumerate(pages, 1):
            try:
                chunks = self.processor.process_page_content(page)
                all_chunks.extend(chunks)

                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(pages)} pages, {len(all_chunks)} chunks so far")

            except Exception as e:
                url = page.get('url', page.get('source_url', 'unknown'))
                logger.error(f"Failed to process {url}: {e}")

        logger.info(f"Created {len(all_chunks)} total chunks")

        # Deduplicate
        unique_chunks = self.processor.deduplicate_chunks(all_chunks)
        logger.info(f"After deduplication: {len(unique_chunks)} unique chunks")

        # Format for vector DB
        self.all_chunks = self.processor.format_for_vector_db(unique_chunks)

        # Save chunks
        output_file = config.CONTENT_CHUNKS_FILE
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"Chunks saved to {output_file}")

        # Calculate processing stats
        self.processing_stats = {
            'total_pages_processed': len(pages),
            'chunks_created': len(all_chunks),
            'chunks_after_dedup': len(unique_chunks),
            'average_chunk_size': sum(c['metadata']['word_count'] for c in self.all_chunks) / len(self.all_chunks) if self.all_chunks else 0,
        }

        return self.all_chunks

    def phase_3_analyze(self) -> Dict[str, Any]:
        """
        Phase 3: Analyze content and create reports.

        Returns:
            Analysis results
        """
        logger.info("=" * 60)
        logger.info("PHASE 3: ANALYSIS & REPORTING")
        logger.info("=" * 60)

        # Create site map
        site_map = self.mapper.generate_site_map()

        # Analyze chunks
        content_types = Counter()
        domains = Counter()
        total_words = 0

        for chunk in self.all_chunks:
            metadata = chunk['metadata']
            content_types[metadata.get('content_type', 'unknown')] += 1
            domains[metadata.get('source_domain', 'unknown')] += 1
            total_words += metadata.get('word_count', 0)

        # Generate analysis report
        report_lines = [
            "=" * 70,
            "TEXAS CHILD CARE SOLUTIONS - SCRAPING ANALYSIS REPORT",
            "=" * 70,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SCRAPING SUMMARY",
            "=" * 70,
            f"Start URLs: {', '.join(config.SEED_URLS)}",
            f"Total pages scraped: {self.scraping_stats.get('pages_scraped', 0)}",
            f"Total documents downloaded: {self.scraping_stats.get('documents_downloaded', 0)}",
            f"Total PDFs downloaded: {self.scraping_stats.get('pdfs_downloaded', 0)}",
            f"Total chunks created: {len(self.all_chunks)}",
            f"Scraping time: {self.scraping_stats.get('elapsed_seconds', 0):.1f} seconds",
            "",
            "CONTENT BREAKDOWN",
            "=" * 70,
            "By content type:",
        ]

        for content_type, count in content_types.most_common():
            percentage = (count / len(self.all_chunks) * 100) if self.all_chunks else 0
            report_lines.append(f"  - {content_type}: {count} chunks ({percentage:.1f}%)")

        report_lines.extend([
            "",
            "By source domain:",
        ])

        for domain, count in domains.most_common():
            percentage = (count / len(self.all_chunks) * 100) if self.all_chunks else 0
            report_lines.append(f"  - {domain}: {count} chunks ({percentage:.1f}%)")

        report_lines.extend([
            "",
            "QUALITY METRICS",
            "=" * 70,
            f"Average chunk word count: {self.processing_stats.get('average_chunk_size', 0):.1f}",
            f"Total content words: {total_words:,}",
            f"Pages skipped (too thin): {self.scraping_stats.get('pages_skipped', 0)}",
            f"Pages with errors: {self.scraping_stats.get('errors', 0)}",
            f"Duplicate chunks removed: {self.processing_stats.get('chunks_created', 0) - self.processing_stats.get('chunks_after_dedup', 0)}",
            "",
            "SITE STRUCTURE",
            "=" * 70,
            f"Hub pages (navigation): {site_map['summary']['hub_pages']}",
            f"Content pages: {site_map['summary']['content_pages']}",
            f"PDF documents: {site_map['summary']['pdf_documents']}",
            f"Unique domains scraped: {site_map['summary']['unique_domains']}",
            "",
            "RECOMMENDATIONS",
            "=" * 70,
        ])

        # Add recommendations based on results
        if len(self.all_chunks) < 20:
            report_lines.append("  ⚠ Low chunk count. Consider expanding to more domains or pages.")
        elif len(self.all_chunks) > 50:
            report_lines.append("  ✓ Good chunk count achieved.")

        if self.processing_stats.get('average_chunk_size', 0) < 400:
            report_lines.append("  ⚠ Average chunk size is small. May indicate thin content.")
        elif self.processing_stats.get('average_chunk_size', 0) > 1200:
            report_lines.append("  ⚠ Average chunk size is large. Consider reducing max chunk size.")
        else:
            report_lines.append("  ✓ Chunk sizes are well-balanced.")

        if self.scraping_stats.get('errors', 0) > len(self.all_chunks) * 0.1:
            report_lines.append("  ⚠ High error rate (>10%). Check failed URLs in logs.")
        else:
            report_lines.append("  ✓ Low error rate.")

        report_lines.extend([
            "",
            "=" * 70,
            "NEXT STEPS",
            "=" * 70,
            "1. Review content_chunks.json for vector DB ingestion",
            "2. Check site_map.json for navigation structure",
            "3. Review scraping_log.txt for detailed execution log",
            "4. Load chunks into your vector database",
            "=" * 70,
        ])

        # Save report
        report_text = '\n'.join(report_lines)
        report_file = config.ANALYSIS_REPORT_FILE

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        logger.info(f"Analysis report saved to {report_file}")

        # Print report to console
        print("\n" + report_text)

        return {
            'site_map': site_map,
            'content_types': dict(content_types),
            'domains': dict(domains),
            'total_chunks': len(self.all_chunks),
            'total_words': total_words,
        }

    def run(self, seed_urls: List[str] = None) -> Dict[str, Any]:
        """
        Run the complete pipeline.

        Args:
            seed_urls: Optional list of seed URLs (defaults to config)

        Returns:
            Complete results dictionary
        """
        seed_urls = seed_urls or config.SEED_URLS

        try:
            # Phase 1: Scrape
            scraping_stats = self.phase_1_scrape(seed_urls)

            # Phase 2: Process
            chunks = self.phase_2_process()

            # Phase 3: Analyze
            analysis = self.phase_3_analyze()

            logger.info("=" * 60)
            logger.info("PIPELINE COMPLETE!")
            logger.info("=" * 60)

            return {
                'success': True,
                'scraping_stats': scraping_stats,
                'processing_stats': self.processing_stats,
                'analysis': analysis,
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Texas Child Care Solutions Web Scraper'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (limited pages for testing)'
    )
    args = parser.parse_args()

    # Ensure directories exist
    ensure_directories()

    # Setup logging
    logger = setup_logging()

    logger.info("=" * 70)
    logger.info("TEXAS CHILD CARE SOLUTIONS SCRAPER - OPTION 5: SMART HYBRID")
    logger.info("=" * 70)
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info(f"Target domains: {', '.join(config.ALLOWED_DOMAINS)}")
    logger.info("")

    # Run pipeline
    pipeline = ScrapingPipeline(dry_run=args.dry_run)
    results = pipeline.run()

    if results['success']:
        logger.info("All phases completed successfully!")
        logger.info(f"Output files:")
        logger.info(f"  - Chunks: {config.CONTENT_CHUNKS_FILE}")
        logger.info(f"  - Site map: {config.SITE_MAP_FILE}")
        logger.info(f"  - Analysis: {config.ANALYSIS_REPORT_FILE}")
        logger.info(f"  - Log: {config.LOG_FILE}")
    else:
        logger.error(f"Pipeline failed: {results.get('error')}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
