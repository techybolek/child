iHere's a comprehensive prompt for Claude Code:

---

# Project: Extract and Organize Web Content for Vector Database

## Objective
I need you to scrape and organize content from https://texaschildcaresolutions.org/financial-assistance-for-child-care/ for loading into a vector database. This is a **link-heavy portal site** that routes to external resources rather than containing much content itself.

## The Challenge
This website appears to be content-poor and primarily serves as a navigation hub linking to:
- Multiple regional workforce solutions websites
- Texas government (.gov) sites  
- PDF documents with actual eligibility/application details
- Partner organization sites

Your job is to intelligently gather the ACTUAL useful content that users need to know about child care financial assistance in Texas.

## Phase 1: Discovery & Analysis

First, analyze the site structure:

1. **Visit the starting URL** and determine:
   - How much actual text content exists on this page (word count)
   - How many links are present (internal vs external)
   - What domains are being linked to
   - Are there PDFs? How many?
   - What's the content-to-link ratio?

2. **Generate a report** that shows:
   - Is this primarily a content site or a navigation hub?
   - What external domains does it link to?
   - Which domains appear to contain the actual information?
   - Sample of link anchor text to understand what's being linked

3. **Ask me for scope decision**: 
   - Should we scrape ONLY the main domain?
   - Should we follow links to specific external domains? (suggest top 5-7 most relevant)
   - Should we download and extract PDFs?

## Phase 2: Scraping Strategy

Based on my scope decision, implement smart scraping:

### Requirements:
- **Respect robots.txt** and add delays (1-2 seconds between requests)
- **Skip thin pages**: Don't save pages with <100 words of actual content
- **Handle PDFs**: Extract text from PDFs using a library like PyMuPDF
- **Track metadata**: URL, domain, title, last modified (if available), content type
- **Deduplication**: Don't scrape the same URL twice
- **Error handling**: Log failures but continue scraping
- **Progress tracking**: Show me what's being scraped in real-time

### Special Cases:
- If a page is mostly navigation/links, mark it as type: "navigation" 
- If a page has FAQ-style content (Q&A pairs), preserve that structure
- If a page has lists/tables of eligibility criteria, preserve formatting
- Extract any forms/application instructions specially

## Phase 3: Organization & Output Structure

Create the following directory structure:

```
scraped_content/
├── raw/
│   ├── pages/           # Individual page JSON files
│   ├── pdfs/            # PDF text extractions
│   └── metadata.json    # Scraping metadata
├── processed/
│   ├── content_chunks.json    # Ready for vector DB
│   └── site_map.json          # Navigation structure
└── reports/
    ├── scraping_summary.txt
    └── content_analysis.txt
```

### Format for content_chunks.json:
```json
[
  {
    "chunk_id": "unique_id",
    "text": "The actual content text, 500-1000 words max",
    "metadata": {
      "source_url": "https://...",
      "source_domain": "texaschildcaresolutions.org",
      "page_title": "Financial Assistance",
      "content_type": "article|faq|navigation|pdf|eligibility_criteria",
      "section_heading": "Who is eligible?",
      "chunk_index": 0,
      "word_count": 450,
      "scraped_date": "2025-10-09"
    }
  }
]
```

### Format for site_map.json:
```json
{
  "hub_pages": [
    {
      "url": "...",
      "title": "...",
      "links_to": ["url1", "url2"],
      "purpose": "Routes users to regional offices"
    }
  ],
  "content_pages": ["list of URLs with substantial content"],
  "pdf_documents": ["list of PDF URLs"],
  "external_resources": {"domain": ["urls"]}
}
```

## Phase 4: Content Processing

Before saving to content_chunks.json:

1. **Clean the text**:
   - Remove excessive whitespace and blank lines
   - Strip navigation menus, headers, footers
   - Remove "Skip to content" type links
   - Preserve paragraph breaks and list structures

2. **Chunk intelligently**:
   - Split long pages into 500-1000 word chunks
   - Try to split at natural boundaries (headings, paragraphs)
   - Add 100-200 word overlap between chunks
   - Keep related Q&A pairs together
   - Don't split tables or lists awkwardly

3. **Classify content type**:
   - "eligibility_criteria" - income limits, requirements, etc.
   - "application_process" - how to apply, forms needed
   - "faq" - question and answer format
   - "contact_info" - phone numbers, office locations
   - "navigation" - primarily links to other resources
   - "policy" - program rules and regulations

4. **Preserve structure where it matters**:
   - If content has numbered steps, keep them
   - If content is a comparison table, convert to clear text
   - If content has bullet points, preserve them

## Phase 5: Analysis Report

Generate `content_analysis.txt` with:

```
SCRAPING SUMMARY
================
Start URL: [url]
Total pages scraped: X
Total PDFs processed: X
Total chunks created: X
Date: [date]

CONTENT BREAKDOWN
=================
By type:
- Eligibility criteria: X chunks
- Application process: X chunks
- FAQs: X chunks
- Contact info: X chunks
- Navigation: X chunks
- Other: X chunks

By source:
- Main domain: X chunks
- External domain 1: X chunks
- External domain 2: X chunks
- PDFs: X chunks

QUALITY METRICS
===============
Average chunk word count: X
Pages skipped (too thin): X
Pages with errors: X
Duplicate URLs found: X

RECOMMENDATIONS
===============
- [Any issues you found]
- [Suggestions for improving content coverage]
- [Notes about missing information]
```

## Technical Specifications

**Libraries you should use:**
- `playwright` or `selenium` for JavaScript-heavy sites
- `beautifulsoup4` for HTML parsing
- `pymupdf` or `pypdf` for PDF extraction
- `requests` for simple page fetching
- Standard library `json` for data handling

**Code organization:**
Create these Python scripts:
1. `scraper.py` - Main scraping logic
2. `content_processor.py` - Cleaning and chunking
3. `pdf_extractor.py` - PDF handling
4. `config.py` - Settings (domains to scrape, delays, etc.)
5. `run_pipeline.py` - Orchestrates everything

## Constraints & Guidelines

- **Maximum pages**: Cap at 500 pages total (to avoid infinite crawling)
- **Timeout**: 30 seconds per page
- **Respect rate limits**: 1-2 second delay between requests
- **File size**: If a PDF is >50MB, skip it and note in logs
- **External domains**: Only follow if explicitly approved by me
- **Language**: Only process English content

## What I Need From You

After you complete each phase:
1. Show me the discovery analysis and wait for scope approval
2. Show me progress as you scrape (every 10-20 pages)
3. Alert me to any errors or issues
4. When complete, show me the summary stats and ask if I want any adjustments

## Success Criteria

The output is ready for vector DB if:
- ✅ All chunks have clear source attribution
- ✅ Content is clean and readable
- ✅ Chunks are 500-1000 words (except for naturally short FAQs)
- ✅ Metadata is complete and structured
- ✅ No duplicate content
- ✅ Navigation pages are separated from content pages

Please start with Phase 1: Discovery & Analysis, then wait for my approval before proceeding to scraping.