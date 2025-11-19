"""
Configuration settings for Texas Child Care Solutions web scraper
Option 5: Smart Hybrid approach
"""

import os
from datetime import datetime

# ===== PROJECT PATHS =====
# Get parent directory (project root) since config.py is now in SCRAPER/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPED_CONTENT_DIR = os.path.join(BASE_DIR, 'scraped_content')
RAW_DIR = os.path.join(SCRAPED_CONTENT_DIR, 'raw')
PAGES_DIR = os.path.join(RAW_DIR, 'pages')
PDFS_DIR = os.path.join(RAW_DIR, 'pdfs')
DOCUMENTS_DIR = os.path.join(RAW_DIR, 'documents')
PROCESSED_DIR = os.path.join(SCRAPED_CONTENT_DIR, 'processed')
REPORTS_DIR = os.path.join(SCRAPED_CONTENT_DIR, 'reports')

# ===== DOMAIN ALLOWLIST (Option 5: Smart Hybrid) =====
ALLOWED_DOMAINS = [
    'texaschildcaresolutions.org',       # Main portal (all pages)
    'twc.state.tx.us',                   # State authority (child care sections)
    'twc.texas.gov',                     # Alternative TWC domain
    'childcare.twc.texas.gov',           # Application portal (attempt with JS)
    'wfsgc.org',                         # Representative regional site (Houston)
]

# ===== SEED URLS =====
SEED_URLS = [
    'https://texaschildcaresolutions.org/financial-assistance-for-child-care/',
    'https://www.twc.texas.gov/programs/child-care',
    'https://childcare.twc.texas.gov/',
]

# ===== TWC URL PATTERNS TO TARGET =====
# Only scrape TWC pages matching these patterns
TWC_CHILD_CARE_PATTERNS = [
    '/childcare/',
    '/child-care',
    '/programs/child-care',
    '/customers/child-care',
    '/families/child-care',
    '/ccs',        # Child Care Services acronym
    '/ccms',       # Child Care Management System
    '/ccel/',      # Child Care and Early Learning resources
]

# ===== RATE LIMITING & TIMEOUTS =====
DELAY_BETWEEN_REQUESTS = 1.5  # seconds
TIMEOUT_PER_PAGE = 30         # seconds

# ===== SCRAPING LIMITS =====
MAX_PAGES = 500               # Maximum pages to scrape total
MAX_PDF_SIZE_MB = 50          # Skip PDFs larger than this
MAX_DOCUMENT_SIZE_MB = 50     # Skip documents larger than this
MIN_CONTENT_WORDS = 100       # Skip pages with less content than this

# ===== PDF/DOCUMENT EXCLUSIONS =====
# PDFs and documents to skip (translations, duplicates, etc.)
EXCLUDED_PDF_FILENAMES = [
    'child-care-services-parent-rights-vietnamese.pdf',
    'parent-tx3c-attendance-help-vietnames-twc.pdf',
    'provider-attendance-matrix-vietnamese-twc.pdf',
    'ccdf-emergency-preparedness-disaster-response-plan-2021-twc.pdf',
    'child-care-services-parent-rights-espanol-twc.pdf',
    'provider-attendance-matrix-español-twc.pdf',
    'child-care-quality-performance-report-2021-twc.pdf',
    'evaluation-of-the-effectiveness-of-child-care-report-to-87th-legislature-2021-twc.pdf',
    'evaluation-effectiveness-child-care-program-84-legislature-twc.pdf',
    'evaluation-effectiveness-child-care-program-85-legislature-twc.pdf',
    'evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf',
    'acf-218-qpr-ffy-2022-for-texas.pdf',
    'tx-pdg-renewal-application-2022-public.pdf',
    'acf-218-qpr-ffy-2023-for-texas.pdf',
    'child-care-teacher-desk-aid-march-2023-twc.pdf',
    'texas-pcqc-user-guide-2023.pdf',
    'child-care-provider-desk-aid-twc.pdf',
    'trs-parent-brochure-vie.pdf',
    'trs-parent-brochure-spa.pdf',
]

# ===== CONTENT PROCESSING =====
# Chunk size range (in words)
CHUNK_MIN_WORDS = 500
CHUNK_MAX_WORDS = 1000
CHUNK_OVERLAP_WORDS = 150

# Document processing
# When True, .docx and .xlsx documents are excluded from standard chunk processing
# Documents are still scraped and saved, but processed separately
PROCESS_DOCUMENTS_SEPARATELY = True

# Content type classification keywords
CONTENT_TYPE_RULES = {
    'eligibility_criteria': [
        'income', 'eligible', 'requirements', 'qualify', 'eligibility',
        'qualify for', 'meet the', 'must be', 'income limit'
    ],
    'application_process': [
        'apply', 'application', 'how to', 'steps', 'submit', 'register',
        'sign up', 'enrollment', 'apply for'
    ],
    'faq': [
        'question', 'answer', 'faq', 'Q:', 'A:', 'frequently asked',
        'common questions'
    ],
    'contact_info': [
        'phone', 'email', 'address', 'office', 'location', 'contact',
        'call us', 'reach us', 'office hours'
    ],
    'policy': [
        'policy', 'rules', 'regulation', 'guidelines', 'requirements',
        'procedures', 'compliance'
    ],
    'navigation': [
        'click here', 'visit', 'see more', 'learn more', 'read more',
        'go to', 'navigate to'
    ],
}

# ===== USER AGENT =====
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)

# ===== PLAYWRIGHT SETTINGS =====
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_TIMEOUT = 30000  # milliseconds

# ===== CONTENT EXTRACTION SETTINGS =====
# HTML tags to remove (navigation, headers, footers)
TAGS_TO_REMOVE = [
    'nav', 'header', 'footer', 'aside', 'script', 'style',
    'iframe', 'noscript', 'button'
]

# Classes and IDs to remove (common navigation elements)
SELECTORS_TO_REMOVE = [
    '.navigation', '.nav', '.menu', '.sidebar', '.footer',
    '.header', '.skip-link', '.breadcrumb', '#nav', '#menu',
    '#header', '#footer', '.social-media', '.share-buttons'
]

# ===== LOGGING =====
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(REPORTS_DIR, 'scraping_log.txt')

# ===== OUTPUT FILES =====
CONTENT_CHUNKS_FILE = os.path.join(PROCESSED_DIR, 'content_chunks.json')
SITE_MAP_FILE = os.path.join(PROCESSED_DIR, 'site_map.json')
ANALYSIS_REPORT_FILE = os.path.join(REPORTS_DIR, 'content_analysis.txt')

# ===== DRY RUN SETTINGS =====
DRY_RUN_MAX_PAGES = 5        # Only scrape this many pages in dry run

# ===== MISC =====
SCRAPE_TIMESTAMP = datetime.now().isoformat()

# ===== HELPER FUNCTIONS =====
def is_twc_child_care_url(url):
    """Check if a TWC URL matches child care patterns."""
    if 'twc.' not in url.lower():
        return True  # Non-TWC URLs are allowed

    # For TWC URLs, check if they match child care patterns
    for pattern in TWC_CHILD_CARE_PATTERNS:
        if pattern in url.lower():
            return True
    return False

def should_process_domain(domain):
    """Check if a domain should be processed."""
    return any(allowed in domain.lower() for allowed in ALLOWED_DOMAINS)

def is_excluded_pdf(url):
    """Check if a PDF URL should be excluded."""
    from urllib.parse import unquote

    # Decode URL-encoded characters (like %C3%B1 for ñ)
    decoded_url = unquote(url.lower())

    # Check if any excluded filename is in the URL
    for excluded_filename in EXCLUDED_PDF_FILENAMES:
        if excluded_filename.lower() in decoded_url:
            return True
    return False
