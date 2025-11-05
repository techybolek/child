# Qdrant PDF Reloader Skill

A Claude Code skill that surgically reloads a single PDF document to Qdrant without affecting other documents in the collection, using the `UTIL/reload_single_pdf.py` script.

## Overview

This skill provides a fast, targeted way to refresh individual PDF documents in your Qdrant vector database. Instead of reloading the entire collection (which can take hours), surgical reload updates just one document in seconds to minutes.

**Perfect for:**
- Fixing text cleaning issues in specific documents
- Updating a PDF after replacing the file
- Regenerating contextual embeddings for one document
- Applying latest processing improvements to specific files
- Quick fixes without disrupting the entire collection

## Features

- **Surgical precision**: Updates only the specified PDF, leaves others untouched
- **3-step process**: Delete old chunks → Re-process → Upload new chunks
- **Contextual embeddings**: Automatically generates document and chunk contexts
- **Smart text cleaning**: Applies fixed text cleaner, removes TOCs, normalizes formatting
- **Table preservation**: Single-page PDFs loaded as one chunk to preserve table structure
- **Fast execution**: Seconds to minutes vs. hours for full reload
- **Idempotent**: Safe to run multiple times - produces same result

## Usage

Simply ask Claude to reload a PDF using natural language:

```
"Reload bcy-26-income-eligibility-and-maximum-psoc-twc.pdf"
"Refresh the payment rates PDF with the fixed text cleaner"
"I updated the state plan file - please reload it"
"Regenerate contextual embeddings for the provider payment rates document"
```

The skill activates automatically when you use keywords like:
- "reload PDF"
- "refresh document"
- "reload [filename]"
- "update single file"
- "regenerate embeddings"

## How It Works

### The Surgical Reload Process

When you ask to reload a PDF, the script performs these steps:

1. **DELETE**: Finds and deletes all existing chunks for the specified PDF
2. **PROCESS**: Re-processes the PDF with current text cleaner and chunking logic
3. **GENERATE**: Creates fresh contextual embeddings (master, document, and chunk contexts)
4. **UPLOAD**: Uploads new chunks with embeddings to Qdrant

**Time:** Usually completes in under 1 minute for most documents.

### What Gets Updated

- ✅ Text cleaning (normalized whitespace, removed headers/footers)
- ✅ Chunk boundaries (latest chunking logic applied)
- ✅ TOC filtering (table of contents chunks removed)
- ✅ Contextual metadata (document context + chunk context)
- ✅ Embeddings (fresh OpenAI embeddings generated)

### What Stays the Same

- Collection structure
- All other documents
- Collection settings
- Your API connections

## Examples

### Example 1: Fix Text Cleaning Issue

```
You: The income eligibility PDF has weird spacing and garbled text.
     Can you reload it?

Claude: I'll surgically reload that PDF with the updated text cleaner.

        cd UTIL
        python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf

        [Processing...]

        ✓ Deleted 12 old chunks
        ✓ Processed 8 pages
        ✓ Created 10 chunks (filtered 2 TOC chunks)
        ✓ Generated contextual metadata
        ✓ Uploaded 10 new chunks

        Reload complete! The document now has:
        - Clean, normalized text
        - Removed TOC sections
        - Fresh contextual embeddings
```

### Example 2: Update Replaced File

```
You: I replaced bcy25-child-care-provider-payment-rates-twc.pdf
     with the corrected version. Can you reload it?

Claude: I'll reload the payment rates PDF with the new file.

        cd UTIL
        python reload_single_pdf.py bcy25-child-care-provider-payment-rates-twc.pdf

        ✓ Surgical reload complete!

        Deleted: 5 old chunks
        Uploaded: 5 new chunks (single-page table preserved)

        The corrected PDF is now in Qdrant.
```

### Example 3: Regenerate Context

```
You: The retrieval for the state plan isn't great.
     Can you regenerate the contextual embeddings?

Claude: I'll reload the state plan to regenerate contextual metadata.

        cd UTIL
        python reload_single_pdf.py tx-ccdf-state-plan-ffy2025-2027-approved.pdf

        [Processing...]

        ✓ Generated new contexts:
        - Document context: Comprehensive summary of state plan
        - Chunk contexts: Generated for all 87 chunks

        ✓ Uploaded 87 chunks with fresh contextual embeddings

        Retrieval should now be improved with better context.
```

## When to Use Surgical Reload vs. Full Reload

### Use Surgical Reload (This Skill) When:

✅ **Updating 1-10 PDFs**
✅ **Quick fix needed** (minutes, not hours)
✅ **Specific document has issues**
✅ **Other documents are fine** and shouldn't be touched
✅ **Testing text cleaner changes** on specific files

### Use Full Reload When:

❌ **Updating 10+ PDFs** (faster to reload all)
❌ **Major system changes** (new embedding model, chunk size)
❌ **Collection structure changed**
❌ **Starting fresh** with new document set
❌ **Migrating to new collection**

**Rule of Thumb:** < 10 files = surgical reload, > 10 files = full reload.

## Technical Details

### File Locations

- **Script:** `UTIL/reload_single_pdf.py`
- **PDF Source:** `scraped_content/raw/pdfs/`
- **Collection:** Uses `QDRANT_COLLECTION_NAME_CONTEXTUAL` from config

### Processing Features

**Text Cleaning:**
- Normalizes whitespace
- Removes page headers/footers
- Cleans special characters
- Filters TOC (table of contents) chunks

**Chunking Logic:**
- **Multi-page PDFs:** Split with RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
- **Single-page PDFs:** Loaded as one chunk (preserves table structure)

**Contextual Embeddings:**
- **Master Context:** Overview of Texas childcare system
- **Document Context:** Summary of the specific document
- **Chunk Context:** Summary of previous chunk (for continuity)

### Requirements

Ensure these are configured:
```bash
# OpenAI (for embeddings)
export OPENAI_API_KEY="your-key"

# Qdrant
export QDRANT_API_URL="your-url"
export QDRANT_API_KEY="your-key"

# GROQ (for context generation)
export GROQ_API_KEY="your-key"
```

## Workflow Steps

### 1. Identify the PDF to Reload

Determine which PDF needs updating (exact filename required).

### 2. Verify PDF Exists (Optional)

```bash
ls scraped_content/raw/pdfs/document-name.pdf
```

### 3. Ask Claude to Reload

Simply tell Claude:
- "Reload [filename]"
- "Refresh [filename]"
- "Update [description of document]"

### 4. Monitor Progress

Claude will show:
- Deletion count
- Processing stages
- Chunk creation
- Context generation
- Upload progress

### 5. Verify Results (Optional)

Check the reloaded chunks:
```bash
cd UTIL
python retrieve_chunks_by_filename.py --filename document.pdf
```

## Output Example

```
============================================================
SURGICAL RELOAD: bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
============================================================

Deleting all chunks for: bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
Scrolling through collection to find matching chunks...
Found 12 chunks to delete
✓ Deleted 12 chunks

Processing: scraped_content/raw/pdfs/bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
Loaded 8 pages
Multi-page PDF (8 pages): split into 12 chunks
Filtered out 2 TOC chunks (16.7%)
Created 10 chunks after filtering

Generating contextual metadata...
✓ Contextual metadata generated

Uploading 10 chunks to Qdrant...
Uploaded batch 1/1
✓ Successfully uploaded 10 chunks

============================================================
RELOAD COMPLETE
Deleted: 12 old chunks
Uploaded: 10 new chunks
============================================================

✓ Surgical reload complete!
```

## File Structure

```
.claude/skills/qdrant-pdf-reloader/
├── SKILL.md    # Instructions for Claude (internal)
└── README.md   # User documentation (this file)

UTIL/
└── reload_single_pdf.py  # The surgical reload script
```

## Troubleshooting

### "PDF not found"

**Cause:** PDF doesn't exist in `scraped_content/raw/pdfs/`

**Solution:**
- Verify exact filename (case-sensitive, include `.pdf`)
- Check if PDF was downloaded: `ls scraped_content/raw/pdfs/`
- Re-run scraper if PDF is missing

### "No chunks found" (during deletion)

**Cause:** Document isn't in Qdrant collection

**Solution:**
- Document may not have been loaded yet
- Skip deletion and proceed with upload only
- Verify with: `python LOAD_DB/verify_qdrant.py`

### Connection Errors

**Cause:** Can't connect to Qdrant or OpenAI

**Solution:**
- Check environment variables are set
- Verify API keys are valid
- Test network connectivity
- Check Qdrant server status

### Processing Errors

**Cause:** PDF file is corrupted or unreadable

**Solution:**
- Try opening PDF manually to verify it's readable
- Re-download the PDF if corrupted
- Check PDF file permissions

### Upload Errors

**Cause:** Embedding generation or Qdrant upload failed

**Solution:**
- Verify OpenAI API key has credits
- Check Qdrant collection exists
- Ensure collection has correct dimensions (1536 for text-embedding-3-small)

## Advanced Usage

### Compare Before and After

**Before reload:**
```bash
python retrieve_chunks_by_filename.py --filename doc.pdf --output before.json
```

**Reload:**
```bash
python reload_single_pdf.py doc.pdf
```

**After reload:**
```bash
python retrieve_chunks_by_filename.py --filename doc.pdf --output after.json
```

**Compare:**
- Check chunk counts
- Review text cleaning improvements
- Verify context fields populated

### Batch Reload Multiple Files

For multiple files, ask Claude to reload them sequentially:

```
"Reload these PDFs:
 - bcy25-child-care-provider-payment-rates-twc.pdf
 - bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
 - bcy2025-psoc-chart-twc.pdf"
```

Claude will run the reload script for each file.

## Performance

**Typical reload times:**

| Document Size | Pages | Chunks | Time |
|--------------|-------|--------|------|
| Small (1-page table) | 1 | 1 | ~10 sec |
| Medium | 5-10 | 5-15 | ~30 sec |
| Large | 20-50 | 30-80 | ~1-2 min |
| Very large | 100+ | 150+ | ~3-5 min |

*Time includes: deletion, processing, context generation, embedding, upload*

## Tips

1. **Verify first**: Use `retrieve_chunks_by_filename.py` to check current state before reloading
2. **One at a time**: For multiple PDFs, reload them one by one to monitor each
3. **Keep originals**: Don't delete source PDFs until reload is confirmed successful
4. **Check contexts**: After reload, verify context fields are populated properly
5. **Test retrieval**: Query the chatbot to ensure improved results

## Related Commands

```bash
# Retrieve chunks before/after reload
python UTIL/retrieve_chunks_by_filename.py --filename doc.pdf

# List all documents in collection
python LOAD_DB/verify_qdrant.py

# Delete document without reloading
python UTIL/delete_documents.py

# Full collection reload (all PDFs)
python LOAD_DB/load_pdf_qdrant.py
```

## Dependencies

Uses existing project dependencies:
- `langchain` - PyMuPDFLoader, text splitter
- `langchain-openai` - OpenAI embeddings
- `qdrant-client` - Qdrant operations
- Local modules: `contextual_processor`, `text_cleaner`, `prompts`, `config`

No additional installation needed if your project is already set up.

## Safety Notes

⚠️ **Deletion is permanent** - Old chunks are deleted before new ones are uploaded. Make sure you have the source PDF before reloading.

✅ **Idempotent** - Running multiple times produces the same result. Safe to retry if interrupted.

✅ **Isolated** - Only affects the specified PDF. Other documents remain unchanged.

✅ **No collection rebuild** - Doesn't require recreating the entire collection.
