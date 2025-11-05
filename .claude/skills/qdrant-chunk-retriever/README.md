# Qdrant Chunk Retriever Skill

A Claude Code skill that helps you retrieve and inspect chunks from specific PDF documents in your Qdrant vector database using the `UTIL/retrieve_chunks_by_filename.py` script.

## Overview

This skill provides an easy way to examine how documents are chunked and stored in Qdrant. It's useful for debugging retrieval issues, understanding document structure, verifying chunk content, and inspecting contextual embeddings.

## Features

- **Retrieve all chunks** from a specific PDF document
- **Inspect specific chunks** by index (0-indexed)
- **View chunk metadata** (page numbers, chunk index, total chunks)
- **Examine context fields** (document context, chunk context for continuity)
- **Control text preview length** (500 chars default, customizable, or full text)
- **Export to JSON** for external analysis
- **Efficient filtering** using Qdrant's scroll API

## Usage

Simply ask Claude to retrieve chunks using natural language:

```
"Show me all chunks from child-care-services-guide-twc.pdf"
"What's in chunk 5 of the payment rates document?"
"Retrieve chunks from the state plan PDF and save to JSON"
"Show me the full text of chunk 10"
"Inspect the chunks from bcy-26-income-eligibility document"
```

The skill activates automatically when you use keywords like:
- "retrieve chunks"
- "show chunks"
- "inspect chunks"
- "what's in chunk"
- "view document chunks"

## How It Works

### Behind the Scenes

When you ask to retrieve chunks, Claude will:

1. **Identify the document**: Determines which PDF file to retrieve from
2. **Build the command**: Constructs the appropriate command with options
3. **Run the script**: Executes `UTIL/retrieve_chunks_by_filename.py`
4. **Present results**: Shows chunk content, metadata, and context
5. **Suggest next steps**: Offers debugging insights if relevant

### The Retrieval Process

The `retrieve_chunks_by_filename.py` script:
1. Connects to your Qdrant collection
2. Filters chunks by exact filename match
3. Optionally filters by specific chunk index
4. Sorts chunks by chunk_index to maintain document order
5. Displays chunk text with metadata and context
6. Optionally exports to JSON file

## Examples

### Example 1: View All Chunks from a Document

```
You: Show me all chunks from child-care-services-guide-twc.pdf

Claude: I'll retrieve all chunks from that document.

        [Runs script]

        ✓ Retrieved 15 chunks from 'child-care-services-guide-twc.pdf'

        Chunk 0/15 - Page 1
        Text: [preview of first chunk...]

        Chunk 1/15 - Page 2
        Text: [preview of second chunk...]

        [... 13 more chunks ...]

        The document contains 15 chunks total. Would you like to see
        the full text of any specific chunk?
```

### Example 2: Inspect a Specific Chunk

```
You: What's in chunk 5 of the payment rates PDF?

Claude: Let me retrieve chunk 5 from the payment rates document.

        [Runs script with --chunk 5]

        Chunk 5/12 - Page 3
        Filename: bcy25-child-care-provider-payment-rates-twc.pdf

        Full text:
        [Complete chunk 5 text shown...]

        This chunk contains payment rate information for family
        childcare providers in different age groups.
```

### Example 3: Export to JSON for Analysis

```
You: Export all chunks from tx-ccdf-state-plan to JSON

Claude: I'll retrieve and save all chunks to a JSON file.

        [Runs script with --output]

        ✓ Saved 87 chunks to state_plan_chunks.json

        The JSON file contains complete chunk data including:
        - All chunk text content
        - Page numbers and indices
        - Context fields
        - Metadata

        File location: UTIL/state_plan_chunks.json
```

### Example 4: Debug Retrieval Issues

```
You: I'm getting weird results for "family of 5" queries.
     Can you check what's in the chunks?

Claude: Let me examine the chunks from the income eligibility document.

        [Retrieves and analyzes chunks]

        I found "family of 5" mentioned in chunks 3, 7, and 9.
        Let me show you chunk 3 with full context:

        Chunk 3/15 - Page 2
        Text: [chunk content with family of 5 info...]

        Document Context: [overall document summary...]
        Chunk Context: [previous chunk summary...]

        The issue appears to be that chunk 3 has the table header
        but the actual values are in chunk 4. This may be why
        retrieval isn't capturing the complete information.

        Would you like me to check chunk 4 as well?
```

## Command-Line Options

You can customize retrieval using these options:

### Basic Options

| Option | Description | Example |
|--------|-------------|---------|
| `--filename` | PDF filename to retrieve | `--filename "doc.pdf"` |
| `--chunk` `-c` | Specific chunk index (0-indexed) | `--chunk 5` |
| `--text-length` | Max characters to display (-1 = full) | `--text-length 1000` |
| `--output` | Save to JSON file | `--output chunks.json` |
| `--quiet` | Suppress console output | `--quiet` |
| `--collection` | Qdrant collection name | `--collection custom-coll` |

### Usage Examples

```bash
# All chunks from a file (500 char preview)
python retrieve_chunks_by_filename.py --filename "document.pdf"

# Specific chunk with full text
python retrieve_chunks_by_filename.py --filename "doc.pdf" --chunk 5 --text-length -1

# Export to JSON without console output
python retrieve_chunks_by_filename.py --filename "doc.pdf" --output data.json --quiet

# Show more text per chunk
python retrieve_chunks_by_filename.py --filename "doc.pdf" --text-length 2000
```

## Output Format

### Console Output

```
================================================================================
RETRIEVED CHUNKS: 10 total
================================================================================

Chunk 0/10 - Page 1
Filename: document.pdf
Point ID: abc123...
--------------------------------------------------------------------------------
Text:
This is the content of the first chunk from the document...
--------------------------------------------------------------------------------
Document Context:
This document discusses Texas childcare assistance programs...
Chunk Context:
[Previous chunk summary for continuity]
--------------------------------------------------------------------------------

[Additional chunks follow same format...]
```

### JSON Output

```json
{
  "metadata": {
    "filename": "document.pdf",
    "total_chunks": 10,
    "retrieved_at": "2025-01-15T10:30:00.000000",
    "collection": "tro-child-1"
  },
  "chunks": [
    {
      "id": "point-id-string",
      "chunk_index": 0,
      "total_chunks": 10,
      "page": 1,
      "text": "Full chunk text...",
      "filename": "document.pdf",
      "source_url": "https://...",
      "has_context": true,
      "master_context": "...",
      "document_context": "...",
      "chunk_context": "..."
    }
  ]
}
```

## Use Cases

### 1. Debug RAG Retrieval
When retrieval isn't finding expected information:
- View all chunks to verify the content exists
- Check chunk boundaries (is info split across chunks?)
- Examine context fields to understand embedding content

### 2. Verify Document Loading
After loading a new PDF:
- Check that chunks were created correctly
- Verify chunk count and order
- Ensure context fields are populated

### 3. Understand Document Structure
To see how a document is chunked:
- View all chunks with page numbers
- Identify where section breaks occur
- Understand chunk size and overlap

### 4. Investigate Chunk Context
For contextual embeddings:
- Examine `document_context` (overall summary)
- Review `chunk_context` (previous chunk for continuity)
- Verify context is relevant and accurate

### 5. Export for Analysis
Save chunks for external processing:
- Compare different chunking strategies
- Analyze chunk quality
- Share with team for review

## Configuration

The script uses your existing configuration from `LOAD_DB/config.py`:

```python
QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-1'
QDRANT_API_URL = 'your-qdrant-url'
QDRANT_API_KEY = 'your-qdrant-key'
```

Ensure environment variables are set:
```bash
export QDRANT_API_URL="your-url"
export QDRANT_API_KEY="your-key"
```

## File Structure

```
.claude/skills/qdrant-chunk-retriever/
├── SKILL.md    # Instructions for Claude (internal)
└── README.md   # User documentation (this file)

UTIL/
└── retrieve_chunks_by_filename.py  # The actual retrieval script
```

## Troubleshooting

### "No chunks found for filename"
- **Check filename**: Must be exact match (case-sensitive, include `.pdf`)
- **Verify document exists**: Run `python LOAD_DB/verify_qdrant.py` to list all documents
- **Check collection**: Ensure you're querying the correct collection

### Connection Errors
- **Environment variables**: Verify `QDRANT_API_URL` and `QDRANT_API_KEY` are set
- **Network**: Check connectivity to Qdrant server
- **API key**: Ensure key has read permissions

### "Chunk index not found"
- **Check range**: Chunk indices are 0-indexed (first chunk is 0)
- **Verify count**: First retrieve all chunks to see the valid range
- **Example**: If document has 10 chunks, valid indices are 0-9

### Script Not Running
- **Virtual environment**: Activate with `source .venv/bin/activate`
- **Dependencies**: Install with `pip install -r requirements.txt`
- **Script location**: Verify file exists: `ls UTIL/retrieve_chunks_by_filename.py`

## Tips

1. **Start with preview**: Use default 500-char preview first, then request full text if needed
2. **Use JSON export**: For detailed analysis, export to JSON rather than reading console output
3. **Check context fields**: Look for `has_context: true` to verify contextual embeddings
4. **Debug systematically**: If retrieval fails, check all chunks to find where info is located
5. **Note chunk boundaries**: Information spanning chunks may not be captured in single retrieval

## Related Commands

```bash
# List all documents in collection
python LOAD_DB/verify_qdrant.py

# Delete specific documents
python UTIL/delete_documents.py

# Reload a single PDF
python LOAD_DB/reload_single_pdf.py

# Load new PDFs
python LOAD_DB/load_pdf_qdrant.py --no-clear
```

## Dependencies

Uses existing project dependencies:
- `qdrant-client` - Qdrant Python client
- `argparse` - Command-line parsing (Python standard library)
- Configuration from `LOAD_DB/config.py`

No additional installation needed if your project is already set up.
