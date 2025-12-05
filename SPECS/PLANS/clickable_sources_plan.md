# Plan: Make Sources Clickable in UI

## Problem
Sources displayed in the chatbot UI are not clickable because `source_url` is empty in Qdrant.

## Root Cause (Confirmed)
The loader can't find the JSON metadata files because of a **naming mismatch**:

| Component | Naming Pattern | Example |
|-----------|---------------|---------|
| **PDF files** | `{pdf-name}.pdf` | `trs-parent-brochure.pdf` |
| **JSON files (scraper)** | `{url-hash}_pdf.json` | `06f9f8bf52017feab8d5d5be266a955f_pdf.json` |
| **Loader looks for** | `{pdf-name}_pdf.json` | `trs-parent-brochure_pdf.json` ❌ NOT FOUND |

The scraper (`SCRAPER/pdf_extractor.py:166`) correctly saves `source_url` in the JSON, but uses `hashlib.md5(url)` for the filename. The loader (`LOAD_DB/load_pdf_qdrant.py:227-246`) looks for JSON by PDF filename, which doesn't match.

## Evidence

### Frontend is Ready
`frontend/components/SourceCard.tsx:57-68` already renders clickable links when `source.url` exists:
```tsx
{source.url ? (
  <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
    {source.doc}
  </a>
) : (
  <span className="text-gray-700">{source.doc}</span>
)}
```

### Qdrant Has No URLs
Query shows `source_url` is missing:
```
Filename: trs-parent-brochure.pdf
source_url: "MISSING"
```

### JSON Files Have URLs
`scraped_content/raw/pdfs/06f9f8bf52017feab8d5d5be266a955f_pdf.json`:
```json
{
  "pdf_id": "06f9f8bf52017feab8d5d5be266a955f",
  "source_url": "https://www.twc.texas.gov/sites/default/files/ccel/docs/tx3c-desk-aid-provider-payment-proof-twc.pdf",
  "filename": "tx3c-desk-aid-provider-payment-proof-twc.pdf"
}
```

### Loader Naming Mismatch
`LOAD_DB/load_pdf_qdrant.py:227-246`:
```python
def load_pdf_metadata(self, pdf_path: str) -> Optional[Dict[str, Any]]:
    pdf_name = os.path.basename(pdf_path)  # "trs-parent-brochure.pdf"
    pdf_id = os.path.splitext(pdf_name)[0]  # "trs-parent-brochure"

    metadata_patterns = [
        os.path.join(config.PDFS_DIR, f"{pdf_id}_pdf.json"),  # Looks for trs-parent-brochure_pdf.json
        os.path.join(config.PDFS_DIR, pdf_id + ".json")       # Looks for trs-parent-brochure.json
    ]
    # Neither pattern matches 06f9f8bf52017feab8d5d5be266a955f_pdf.json!
```

## Solution: Fix Loader to Find JSON by Filename Field

Modify `load_pdf_metadata()` in `LOAD_DB/load_pdf_qdrant.py` to:
1. Build an index of all JSON files → filename mappings on init
2. Look up by the `filename` field inside the JSON, not by filename pattern

### Implementation

**File: `LOAD_DB/load_pdf_qdrant.py`**

1. Add method to build JSON metadata index (in `__init__` or lazy):
```python
def _build_metadata_index(self) -> dict[str, dict]:
    """Build index: pdf_filename -> metadata dict from all JSON files."""
    index = {}
    for json_path in glob.glob(os.path.join(config.PDFS_DIR, "*_pdf.json")):
        try:
            with open(json_path) as f:
                data = json.load(f)
            if 'filename' in data:
                index[data['filename']] = data
        except Exception:
            pass
    return index
```

2. Modify `load_pdf_metadata()`:
```python
def load_pdf_metadata(self, pdf_path: str) -> Optional[Dict[str, Any]]:
    """Load metadata JSON for a PDF by matching filename field."""
    pdf_name = os.path.basename(pdf_path)
    return self._metadata_index.get(pdf_name)
```

3. Call `_build_metadata_index()` in `__init__` and store as `self._metadata_index`

### After Fix
- Re-run loader: `python load_pdf_qdrant.py --contextual`
- Sources will have URLs populated in Qdrant
- UI will display clickable links (frontend already supports this)

## Files to Modify

| File | Change |
|------|--------|
| `LOAD_DB/load_pdf_qdrant.py` | Fix `load_pdf_metadata()` to use filename field lookup |

## Testing
After implementation:
1. Run `python load_pdf_qdrant.py --test --contextual` to reload a few PDFs
2. Verify with `python verify_qdrant.py` that `source_url` is populated
3. Test in UI that sources are now clickable links
