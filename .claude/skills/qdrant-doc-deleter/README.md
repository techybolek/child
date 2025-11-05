# Qdrant Document Deleter Skill

A Claude Code skill that helps you delete specific PDF documents from your Qdrant vector database collection using the `UTIL/delete_documents.py` script.

## Overview

This skill provides a safe, guided interface for removing PDF documents from your Qdrant collection. It's particularly useful when you need to:
- Remove outdated document versions (e.g., 2024 versions when you have 2025 updates)
- Clean up incorrectly loaded documents
- Manage collection size by removing unnecessary files
- Update documents by deleting old versions before reloading

## Features

- **Guided deletion process**: Claude walks you through the entire workflow
- **Safety confirmations**: Requires explicit "yes" confirmation before deleting
- **Detailed statistics**: Shows exactly how many chunks were deleted per document
- **Error handling**: Continues processing even if individual documents fail
- **Surgical precision**: Removes only specified documents, leaving others untouched
- **No collection rebuild**: Deletes chunks without reloading the entire collection

## Usage

Simply ask Claude to delete documents using natural language:

```
"Delete the 2024 payment rate PDFs from Qdrant"
"Remove tx-ccdf-state-plan-ffy2025-2027-approved.pdf from the database"
"Clean up old document versions"
"I need to delete some PDFs from the vector database"
```

The skill activates automatically when you use keywords like:
- "delete documents"
- "remove from Qdrant"
- "clean up PDFs"
- "delete from vector database"

## How It Works

### Behind the Scenes

When you ask to delete documents, Claude will:

1. **Identify documents**: Asks you which PDF files to delete
2. **Update script**: Modifies `UTIL/delete_documents.py` with your document list
3. **Explain process**: Shows what will be deleted and asks for confirmation
4. **Run deletion**: Executes the script with safety confirmations
5. **Report results**: Summarizes how many chunks were deleted

### The Delete Process

The `delete_documents.py` script:
1. Scrolls through all chunks in your Qdrant collection
2. Filters chunks where `filename` matches your specified PDFs
3. Collects all matching chunk IDs
4. Deletes them in batch operations
5. Reports statistics for each document

### Safety Features

- **Confirmation required**: You must type "yes" when prompted
- **No accidental deletions**: Script shows what will be deleted before proceeding
- **Per-document tracking**: See results for each document individually
- **Error resilience**: If one document fails, others still process

## Examples

### Example 1: Delete Multiple Documents

```
You: I need to delete these old 2024 PDFs:
     - wd-24-23-att1-twc.pdf
     - acf-218-qpr-ffy-2024-for-texas.pdf

Claude: I'll delete those 2024 documents from your Qdrant collection.

        [Updates script and runs deletion]

        ✓ Results:
        - wd-24-23-att1-twc.pdf: 45 chunks deleted
        - acf-218-qpr-ffy-2024-for-texas.pdf: 32 chunks deleted

        Total: 77 chunks removed from collection
```

### Example 2: Delete and Replace

```
You: Delete tx-ccdf-state-plan-ffy2025-2027-approved.pdf
     so I can reload the corrected version

Claude: I'll delete the current version of that document.

        [Runs deletion]

        ✓ Deleted tx-ccdf-state-plan-ffy2025-2027-approved.pdf: 124 chunks

        You can now reload the corrected version using:
        cd LOAD_DB
        python load_pdf_qdrant.py --no-clear
```

### Example 3: Clean Up After Verification

```
You: I ran verify_qdrant.py and saw duplicate documents.
     Can you help me clean them up?

Claude: I can help delete duplicates. Which documents should I remove?

        [You specify the duplicates]

        [Claude deletes them and shows statistics]
```

## Workflow Steps

### 1. Preparation (Optional)
Before deleting, you might want to verify what's in your collection:

```bash
cd LOAD_DB
python verify_qdrant.py
```

This shows all documents and their chunk counts.

### 2. Ask Claude to Delete
Simply tell Claude which documents to delete:
- By filename: "Delete document-name.pdf"
- By category: "Delete all 2024 versions"
- By description: "Remove the old payment rate PDFs"

### 3. Review and Confirm
Claude will:
- Show you the document list
- Explain what will happen
- Run the script (you'll need to type "yes" when prompted)

### 4. Check Results
Claude reports:
- How many chunks deleted per document
- Any errors or warnings
- Total chunks removed

## Configuration

The skill uses your existing configuration from `LOAD_DB/config.py`:

```python
QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-1'  # Collection to delete from
QDRANT_API_URL = 'your-qdrant-url'
QDRANT_API_KEY = 'your-qdrant-key'
```

Ensure your environment variables are set:
```bash
export QDRANT_API_URL="your-url"
export QDRANT_API_KEY="your-key"
```

## File Structure

```
.claude/skills/qdrant-doc-deleter/
├── SKILL.md    # Instructions for Claude (internal)
└── README.md   # User documentation (this file)

UTIL/
└── delete_documents.py  # The actual deletion script
```

## Important Notes

### Permanent Deletion
⚠️ **Deletions are permanent** - there's no undo feature. Make sure you really want to delete the documents before confirming.

### Filename Matching
- Documents are identified by their exact filename (e.g., `document.pdf`)
- Matching is case-sensitive
- Must include the `.pdf` extension

### Collection Management
- Deletion is "surgical" - only specified documents are removed
- Other documents in the collection are unaffected
- No need to rebuild or reload the entire collection

### After Deletion
If you deleted a document to reload a corrected version:
```bash
cd LOAD_DB
python load_pdf_qdrant.py --no-clear  # Appends without clearing
```

## Troubleshooting

### "No chunks found for document"
- Check the filename spelling (case-sensitive)
- Verify the document was actually in the collection (use `verify_qdrant.py`)
- Ensure you included the `.pdf` extension

### "Error deleting document"
- Check your Qdrant connection settings
- Verify API URL and API key are correct
- Check network connectivity to Qdrant server

### Script doesn't run
- Ensure you're in the virtual environment: `source .venv/bin/activate`
- Check dependencies are installed: `pip install -r requirements.txt`
- Verify the script exists: `ls UTIL/delete_documents.py`

## Related Commands

```bash
# Verify collection before/after deletion
python LOAD_DB/verify_qdrant.py

# Load new documents after deletion
python LOAD_DB/load_pdf_qdrant.py --no-clear

# Reload a single document (delete + re-add)
python LOAD_DB/reload_single_pdf.py
```

## Dependencies

Uses existing project dependencies:
- `qdrant-client` - Qdrant Python client
- Logging from Python standard library
- Configuration from `LOAD_DB/config.py`

No additional installation needed if your project is already set up.
