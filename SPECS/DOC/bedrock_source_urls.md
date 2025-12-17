# Bedrock KB Source URL Citations

Enables full clickable source URLs in Bedrock Agent citations instead of just filenames.

## Problem

**Before:** Bedrock citations returned only filenames:
```json
{"doc": "wd-24-23-att1-twc.pdf", "pages": [], "url": ""}
```

**After:** Citations include full source URLs:
```json
{"doc": "wd-24-23-att1-twc.pdf", "pages": [], "url": "https://www.twc.texas.gov/sites/default/files/ccel/docs/wd-24-23-att1-twc.pdf"}
```

## Solution

Add `.metadata.json` files to S3 alongside PDFs. Bedrock indexes these and returns metadata in API responses.

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Metadata generation script | Done | `LOAD_DB/generate_bedrock_metadata.py` |
| S3 upload script | Done | `LOAD_DB/upload_bedrock_metadata.py` |
| Handler citation extraction | Done | `chatbot/handlers/bedrock_kb_handler.py` |
| Evaluator citation extraction | Done | `evaluation/bedrock_evaluator.py` |
| Integration tests | Done | `tests/test_bedrock_kb_integration.py` |
| Documentation | Done | `SPECS/DOC/bedrock_kb.md` |
| S3 upload + KB resync | Done | Executed 2025-12-17 |

## How It Works

### 1. Metadata File Format

Each PDF needs a companion `.metadata.json` file:

```
s3://cohort-tx-1/
├── wd-24-23-att1-twc.pdf
├── wd-24-23-att1-twc.pdf.metadata.json
```

Metadata file contents:
```json
{
  "metadataAttributes": {
    "source_url": "https://www.twc.texas.gov/sites/default/files/ccel/docs/wd-24-23-att1-twc.pdf"
  }
}
```

### 2. Source URL Origin

URLs come from scraper metadata at `scraped_content/raw/pdfs/*_pdf.json`:
```json
{
  "pdf_id": "06f9f8bf52017feab8d5d5be266a955f",
  "source_url": "https://www.twc.texas.gov/sites/default/files/ccel/docs/tx3c-desk-aid-provider-payment-proof-twc.pdf",
  "filename": "tx3c-desk-aid-provider-payment-proof-twc.pdf"
}
```

### 3. API Response Structure

After KB resync, Bedrock returns metadata in `retrievedReferences`:
```python
ref = {
    'location': {'s3Location': {'uri': 's3://cohort-tx-1/wd-24-23-att1-twc.pdf'}},
    'metadata': {'source_url': 'https://www.twc.texas.gov/...'},  # From .metadata.json
    'content': {'text': '...'}
}
```

### 4. Code Extraction

Both handler and evaluator extract the URL:
```python
metadata = ref.get('metadata', {})
source_url = metadata.get('source_url', '')
```

## Scripts

### generate_bedrock_metadata.py

Generates `.metadata.json` files from scraper data.

```bash
cd LOAD_DB
python generate_bedrock_metadata.py           # Generate files
python generate_bedrock_metadata.py --dry-run # Preview only
```

**Input:** `scraped_content/raw/pdfs/*_pdf.json` (28 files)
**Output:** `LOAD_DB/bedrock_metadata/*.metadata.json` (28 files)

### upload_bedrock_metadata.py

Uploads metadata to S3 and triggers KB resync.

```bash
cd LOAD_DB
python upload_bedrock_metadata.py              # Upload and resync
python upload_bedrock_metadata.py --dry-run    # Preview only
python upload_bedrock_metadata.py --skip-resync # Upload only
python upload_bedrock_metadata.py --no-wait    # Don't wait for completion
```

**Requires:** AWS credentials with S3 and Bedrock permissions

## Testing

### Integration Tests

```bash
# Run citation URL tests (requires metadata uploaded and KB resynced)
pytest tests/test_bedrock_kb_integration.py -v -k "citation"
```

Tests verify:
1. `test_handler_returns_full_source_urls` - Handler returns `https://` URLs
2. `test_evaluator_returns_full_source_urls` - Evaluator returns `https://` URLs
3. `test_handler_and_evaluator_urls_match_format` - Both return consistent format

### Manual Verification

```bash
# Quick test with debug output
python -m evaluation.run_evaluation --mode bedrock --test --limit 1 --debug
```

Check that `sources` array contains full URLs.

## Files Modified

| File | Change |
|------|--------|
| `chatbot/handlers/bedrock_kb_handler.py:54-91` | `_extract_citations()` extracts `source_url` from metadata |
| `evaluation/bedrock_evaluator.py:68-96` | Citation extraction with deduplication and `url` field |
| `tests/test_bedrock_kb_integration.py:144-212` | `TestBedrockCitationURLs` class |
| `SPECS/DOC/bedrock_kb.md:93-128` | Metadata setup documentation |

## Files Created

| File | Purpose |
|------|---------|
| `LOAD_DB/generate_bedrock_metadata.py` | Generate .metadata.json files |
| `LOAD_DB/upload_bedrock_metadata.py` | Upload to S3 and resync KB |
| `LOAD_DB/bedrock_metadata/` | Generated metadata files (28 files) |

## Configuration

| Setting | Value |
|---------|-------|
| S3 Bucket | `cohort-tx-1` |
| Knowledge Base ID | `371M2G58TV` |
| Data Source ID | `V4C2EUGYSY` |
| AWS Region | `us-east-1` |
| Metadata source | `scraped_content/raw/pdfs/*_pdf.json` |

## Activation Steps

To enable full URLs in production:

```bash
cd LOAD_DB

# Step 1: Generate metadata (already done)
python generate_bedrock_metadata.py

# Step 2: Upload to S3 and resync (DONE 2025-12-17)
python upload_bedrock_metadata.py

# Step 3: Verify
pytest tests/test_bedrock_kb_integration.py -v -k "citation"
```

## Comparison: Before vs After

### Handler Response

**Before:**
```python
{
    'answer': '...',
    'sources': [
        {'doc': 'wd-24-23-att1-twc.pdf', 'pages': [], 'url': ''}
    ]
}
```

**After:**
```python
{
    'answer': '...',
    'sources': [
        {'doc': 'wd-24-23-att1-twc.pdf', 'pages': [], 'url': 'https://www.twc.texas.gov/sites/default/files/ccel/docs/wd-24-23-att1-twc.pdf'}
    ]
}
```

### Evaluator Response

**Before:**
```python
{
    'answer': '...',
    'sources': [
        {'doc': 'wd-24-23-att1-twc.pdf', 'page': 'N/A', 'text': '...'}
    ]
}
```

**After:**
```python
{
    'answer': '...',
    'sources': [
        {'doc': 'wd-24-23-att1-twc.pdf', 'page': 'N/A', 'url': 'https://www.twc.texas.gov/...', 'text': '...'}
    ]
}
```

## Troubleshooting

### Empty URL Field

If `url` is empty after upload:
1. Verify metadata files uploaded: `aws s3 ls s3://cohort-tx-1/*.metadata.json`
2. Check KB resync completed: AWS Console → Bedrock → Knowledge Bases → 371M2G58TV
3. Wait 1-2 minutes for indexing to complete

### Upload Fails

Check AWS credentials:
```bash
aws sts get-caller-identity
aws s3 ls s3://cohort-tx-1/
```

### Tests Fail

Tests require metadata to be uploaded and KB resynced:
```bash
# Run upload first
python upload_bedrock_metadata.py

# Then run tests
pytest tests/test_bedrock_kb_integration.py -v -k "citation"
```
