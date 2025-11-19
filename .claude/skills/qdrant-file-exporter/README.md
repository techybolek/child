# Qdrant File Exporter Skill

Export all text chunks from a specific PDF file in the Qdrant vector database to a plain text file.

## Overview

This skill provides a simple way to extract all chunks for a particular PDF document from the Qdrant vector database. It queries the `tro-child-3-contextual` collection, retrieves all chunks matching the specified filename, and saves them to a plain text file for inspection or analysis.

The output includes the complete three-tier contextual embedding hierarchy (master context, document context, and chunk-specific contexts) that enhances retrieval accuracy in the RAG system.

## Features

- **Bulk Extraction**: Retrieve all chunks for a specific PDF in one operation
- **Three-Tier Contexts**: Includes master, document, and chunk-specific contexts
- **Sequential Order**: Chunks sorted by chunk_index to maintain original document order
- **Plain Text Output**: Simple, readable format without JSON or metadata clutter
- **Page Number Headers**: Each chunk labeled with its source page number
- **Document Start**: Output begins with the actual document beginning (not random chunks)
- **Automatic Scrolling**: Handles large files by scrolling through all Qdrant points
- **Organized Output**: Saves to `UTIL/` directory with clear naming

## Installation

No additional dependencies beyond the main project requirements. The skill uses:

- `qdrant-client` (already in project requirements.txt)
- Standard Python libraries (os, sys)

Ensure environment variables are set:

```bash
export QDRANT_API_URL="your-qdrant-url"
export QDRANT_API_KEY="your-qdrant-key"
```

## Usage

### Via Claude Code (Automatic)

Simply ask Claude:

- "Export all chunks from [filename.pdf]"
- "Dump the chunks for the income eligibility PDF"
- "Save all chunks from [filename] to a file"

Claude will automatically activate this skill and run the export.

### Manual Usage

Run the script directly:

```bash
python .claude/skills/qdrant-file-exporter/scripts/export_chunks.py "filename.pdf"
```

Example:

```bash
python .claude/skills/qdrant-file-exporter/scripts/export_chunks.py "bcy-26-income-eligibility-and-maximum-psoc-twc.pdf"
```

## Output

Exported files are saved to:

```
UTIL/[filename]_chunks.txt
```

### Output Format

```
================================================================================
MASTER CONTEXT (applies to all chunks)
================================================================================
This is official Texas Workforce Commission (TWC) documentation regarding...

================================================================================

DOCUMENT CONTEXT
--------------------------------------------------------------------------------
This report evaluates the Texas Workforce Commission's subsidized child‑care program...

================================================================================

--- Chunk 1 (Page 0) ---

[Chunk Context]: Evaluation of TWC's subsidized child‑care program, detailing background...

[Chunk text content]

--- Chunk 2 (Page 0) ---

[Chunk Context]: Section on agency roles and legal mandates...

[Chunk text content]

...
```

**Output includes three-tier contextual embeddings:**
- **Master Context**: Domain-level context (once at beginning)
- **Document Context**: Document-specific summary (once at beginning)
- **Chunk Context**: Chunk-specific context (for each chunk)

Chunks are sorted by their original document order (chunk_index). The first chunk will be from the beginning of the document.

## Examples

### Example 1: Export Income Eligibility Document

```bash
$ python .claude/skills/qdrant-file-exporter/scripts/export_chunks.py "bcy-26-income-eligibility-and-maximum-psoc-twc.pdf"

Connecting to Qdrant...
Collection: tro-child-3-contextual
Searching for chunks with doc='bcy-26-income-eligibility-and-maximum-psoc-twc.pdf'...
Found 47 chunks
Saved to: UTIL/bcy-26-income-eligibility-and-maximum-psoc-twc_chunks.txt
```

### Example 2: Via Claude

```
User: "Export all chunks from the PSOC chart PDF"
Claude: "Which PDF would you like to export? Please provide the exact filename."
User: "bcy-26-psoc-chart-twc.pdf"
Claude: *Runs export*
        ✅ Extracted 12 chunks from bcy-26-psoc-chart-twc.pdf
        📄 Saved to: UTIL/bcy-26-psoc-chart-twc_chunks.txt
```

## File Structure

```
.claude/skills/qdrant-file-exporter/
├── SKILL.md              # Claude instructions
├── README.md             # This file
└── scripts/
    └── export_chunks.py  # Main export script
```

## Troubleshooting

### "File not found in collection"

- Check the exact filename spelling (case-sensitive)
- Use `qdrant-chunk-retriever` skill to search for available files
- Verify the PDF was loaded to the collection

### "Connection error"

- Check QDRANT_API_URL and QDRANT_API_KEY environment variables
- Verify network connectivity
- Run `python LOAD_DB/verify_qdrant.py` to test connection

### "No chunks found"

- The file exists but has 0 chunks (unusual)
- May indicate loading issue - try reloading the PDF

## Related Skills

- `qdrant-chunk-retriever` - Search and inspect specific chunks
- `qdrant-doc-deleter` - Delete documents from collection
- `qdrant-pdf-reloader` - Reload single PDF to collection

## Technical Details

- **Collection**: tro-child-3-contextual (hardcoded)
- **Filter Field**: `filename` (exact match)
- **Extracted Metadata**:
  - `chunk_index` - For sequential ordering
  - `page` - Page number
  - `text` - Chunk content
  - `chunk_context` - Chunk-specific context
  - `document_context` - Document summary
  - `master_context` - Domain-level context
- **Scroll Limit**: 100 chunks per batch
- **Output Encoding**: UTF-8
