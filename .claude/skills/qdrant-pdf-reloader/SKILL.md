---
name: qdrant-pdf-reloader
description: Surgically reloads a single PDF to Qdrant by deleting old chunks and re-uploading with fixes. Use when user wants to reload, refresh, fix, or update a specific PDF without reloading the entire collection.
---

# Qdrant PDF Reloader

This skill helps users surgically reload a single PDF document to Qdrant without reloading the entire collection, using the `UTIL/reload_single_pdf.py` script.

## When to Use This Skill

Activate this skill automatically when the user:
- Wants to reload/refresh a specific PDF in Qdrant
- Needs to fix text cleaning issues in a particular document
- Wants to update a document with improved processing
- Needs to regenerate contextual embeddings for one PDF
- Asks to "reload [filename]", "refresh [filename]", or "fix [filename]"
- Uses keywords like "reload PDF", "refresh document", "update single file"

## What is Surgical Reload?

A **surgical reload** is a targeted operation that:
1. **Deletes** all existing chunks for the specified PDF from Qdrant
2. **Re-processes** the PDF with current text cleaner and chunking logic
3. **Generates** fresh contextual embeddings (document context + chunk context)
4. **Uploads** the new chunks to Qdrant

**Benefits:**
- Much faster than reloading the entire collection (seconds vs. hours)
- Only affects the target PDF - other documents remain unchanged
- Applies latest fixes (text cleaner, TOC filtering, contextual embeddings)
- No risk of losing other documents' data

## How to Use

### Step 1: Identify the PDF to Reload

Ask the user which PDF file needs to be reloaded. The filename must match exactly (e.g., `document-name.pdf`).

### Step 2: Verify PDF Exists

Check that the PDF file exists in the `scraped_content/raw/pdfs/` directory:

```bash
ls scraped_content/raw/pdfs/document-name.pdf
```

If not found, inform the user and ask them to verify the filename.

### Step 3: Run the Reload Script

Execute the surgical reload:

```bash
cd UTIL
python reload_single_pdf.py document-name.pdf
```

The script takes the PDF filename as the only argument.

### Step 4: Monitor Progress

The script will output progress through these stages:
1. **Deletion**: Removing old chunks from Qdrant
2. **Processing**: Loading PDF, cleaning text, chunking
3. **Context Generation**: Creating document and chunk contexts
4. **Upload**: Uploading new chunks with embeddings

### Step 5: Report Results

After completion, summarize:
- Number of old chunks deleted
- Number of new chunks uploaded
- Any errors or warnings encountered
- Confirm successful reload

## Script Features

### Automatic Text Cleaning
The script applies the **fixed text cleaner** which:
- Normalizes whitespace
- Removes page headers/footers
- Cleans special characters
- Filters out Table of Contents (TOC) chunks

### Contextual Embeddings
The script generates **contextual metadata**:
- **Master Context**: High-level overview of the entire Texas childcare system
- **Document Context**: Summary of the specific document (purpose, key topics)
- **Chunk Context**: Summary of the previous chunk for continuity

These contexts are included in embeddings to improve retrieval accuracy.

### Special Handling

**Single-page PDFs:**
- Loaded as one chunk (no splitting) to preserve table structure
- Common for payment rate tables and charts

**Multi-page PDFs:**
- Split into chunks using `RecursiveCharacterTextSplitter`
- Chunk size: 1000 characters
- Overlap: 200 characters

### Collection Target

By default, reloads to the **contextual collection** (`tro-child-1` or similar).

## Example Workflows

### Example 1: Fix Text Cleaning Issue

```
User: "The income eligibility PDF has garbled text. Can you reload it with the fixed text cleaner?"

Claude: I'll surgically reload that PDF with the updated text cleaner.

[Runs command]
cd UTIL
python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf

[Script output shows progress]
✓ Deleted 12 old chunks
✓ Loaded 8 pages
✓ Created 10 chunks after filtering (removed 2 TOC chunks)
✓ Generated contextual metadata
✓ Uploaded 10 new chunks

Reload complete! The document has been refreshed with:
- Fixed text cleaning
- TOC filtering
- Fresh contextual embeddings

Old chunks: 12 deleted
New chunks: 10 uploaded
```

### Example 2: Update After PDF Replacement

```
User: "I replaced the payment rates PDF with a corrected version. Please reload it."

Claude: I'll reload the payment rates PDF with the new version.

[Runs command]
cd UTIL
python reload_single_pdf.py bcy25-child-care-provider-payment-rates-twc.pdf

✓ Surgical reload complete!
Deleted: 5 old chunks (single-page table)
Uploaded: 5 new chunks

The updated PDF is now in Qdrant with fresh contextual embeddings.
```

### Example 3: Regenerate Contextual Embeddings

```
User: "Can you regenerate the contextual embeddings for the state plan document?"

Claude: I'll reload the state plan to regenerate contextual metadata.

cd UTIL
python reload_single_pdf.py tx-ccdf-state-plan-ffy2025-2027-approved.pdf

This will:
1. Delete existing chunks
2. Re-process the PDF
3. Generate new document and chunk contexts
4. Upload with fresh embeddings

[After completion]
✓ Reloaded with new contextual embeddings:
- Document context: [summary of document]
- Chunk contexts: Generated for all 87 chunks
```

### Example 4: Fix Single-Page Table

```
User: "The PSOC chart isn't being retrieved correctly. It's a single-page table PDF."

Claude: Single-page PDFs are loaded as one chunk to preserve table structure. Let me reload it.

cd UTIL
python reload_single_pdf.py bcy2025-psoc-chart-twc.pdf

✓ Single-page PDF: loading as 1 chunk (3,245 characters)
✓ Uploaded 1 chunk with full table content

The table is now loaded as a single coherent chunk, which should improve retrieval.
```

## When to Use vs. Full Reload

### Use Surgical Reload When:
- ✅ Fixing a specific document
- ✅ One or a few PDFs need updating
- ✅ Quick fix needed (seconds/minutes)
- ✅ Other documents are correct and shouldn't be touched

### Use Full Reload When:
- ❌ Major changes to chunking logic or embeddings model
- ❌ Many/most documents need updating
- ❌ Collection structure changed
- ❌ Starting fresh with new documents

**Rule of thumb:** If updating < 10 PDFs, use surgical reload. If updating > 10 PDFs or making system-wide changes, use full reload.

## Technical Details

### File Location
- **Script:** `UTIL/reload_single_pdf.py`
- **PDF Directory:** `scraped_content/raw/pdfs/`
- **Collection:** `QDRANT_COLLECTION_NAME_CONTEXTUAL` from config

### Dependencies
The script requires:
- LangChain (`PyMuPDFLoader`, `RecursiveCharacterTextSplitter`)
- OpenAI embeddings (`text-embedding-3-small`)
- Qdrant client
- GROQ API (for contextual metadata generation)
- Local modules: `contextual_processor`, `text_cleaner`, `prompts`

### Process Flow

```
1. DELETE PHASE
   └─ Scroll through collection
   └─ Find chunks where doc == pdf_filename
   └─ Delete all matching chunks

2. PROCESS PHASE
   └─ Load PDF with PyMuPDFLoader
   └─ Clean text on each page
   └─ Split into chunks (or keep as single chunk if 1 page)
   └─ Filter out TOC chunks

3. CONTEXT PHASE (Contextual Mode)
   └─ Generate document context from first 2000 chars
   └─ Generate chunk context for each chunk (uses previous chunk)
   └─ Add master context, document context, chunk context to metadata

4. UPLOAD PHASE
   └─ Generate OpenAI embeddings for chunk text
   └─ Create Qdrant points with embeddings + metadata
   └─ Upload in batches (100 per batch)
```

### Metadata Added to Chunks

Each uploaded chunk includes:
```python
{
    'text': chunk.page_content,
    'doc': pdf_filename,
    'page': page_number,
    'source_url': url (if available),
    'chunk_context': previous_chunk_summary,
    'document_context': document_summary,
    # Also in payload but not shown: master_context
}
```

## Error Handling

### PDF Not Found
If the PDF doesn't exist in `scraped_content/raw/pdfs/`:
- Verify the filename (exact match, case-sensitive)
- Check if the PDF was scraped/downloaded
- Suggest running the scraper if needed

### Deletion Errors
If deletion fails:
- Check Qdrant connection
- Verify API credentials
- Check if chunks actually exist (use `retrieve_chunks_by_filename.py`)

### Processing Errors
If PDF processing fails:
- Verify PDF is not corrupted
- Check if PDF is readable (try opening manually)
- Review error logs for specifics

### Upload Errors
If upload fails:
- Check OpenAI API key (for embeddings)
- Verify Qdrant connection
- Check if collection exists

## Advanced Usage

### Verify Before Reloading

Check existing chunks before reloading:
```bash
cd UTIL
python retrieve_chunks_by_filename.py --filename document.pdf
```

This shows:
- How many chunks currently exist
- Current chunk content
- Whether issues are present

### Verify After Reloading

Confirm successful reload:
```bash
cd UTIL
python retrieve_chunks_by_filename.py --filename document.pdf --text-length -1
```

Check:
- Chunk count matches expectations
- Text is cleaned properly
- Context fields are populated

### Compare Before/After

1. Export chunks before reload:
```bash
python retrieve_chunks_by_filename.py --filename doc.pdf --output before.json
```

2. Reload the PDF:
```bash
python reload_single_pdf.py doc.pdf
```

3. Export chunks after reload:
```bash
python retrieve_chunks_by_filename.py --filename doc.pdf --output after.json
```

4. Compare the JSON files to see what changed.

## Notes

- **Contextual mode is default**: All reloads use contextual embeddings
- **Chunk IDs are deterministic**: Based on hash of (filename, chunk_index, page)
- **Idempotent operation**: Running multiple times produces same result
- **No undo**: Once chunks are deleted, they're gone (reload completes the operation)
- **Collection must exist**: Script doesn't create collections, only updates existing ones

## Related Tools

- `UTIL/retrieve_chunks_by_filename.py`: Verify chunks before/after reload
- `UTIL/delete_documents.py`: Delete without reloading (if you just want to remove)
- `LOAD_DB/load_pdf_qdrant.py`: Full collection reload (all PDFs)
- `LOAD_DB/verify_qdrant.py`: Verify collection statistics
