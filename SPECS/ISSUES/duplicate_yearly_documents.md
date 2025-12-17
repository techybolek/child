# Duplicate/Contradictory Yearly Documents in Knowledge Base

**Date:** 2025-12-17
**Status:** Open
**Severity:** High
**Impact:** RAG retrieval returns conflicting income limits and payment rates

## Summary

The Qdrant knowledge base contains multiple fiscal year versions of the same documents (BCY 2025 and BCY 2026), causing retrieval to return contradictory information about income eligibility limits and provider payment rates.

## Root Cause

1. BCY25 documents were archived to `ARCHIVE/archived_years/` but remain in `scraped_content/raw/pdfs/`
2. The loading pipeline loads all PDFs from `scraped_content/raw/pdfs/` without filtering by fiscal year
3. Both old and new versions get indexed into the same Qdrant collection

## Affected Documents

### Category 1: Income Limits (HIGH CONFLICT)

| Document | Year | Chunks | Status |
|----------|------|--------|--------|
| `bcy-26-income-eligibility-and-maximum-psoc-twc.pdf` | BCY 2026 | 3 | **KEEP** |
| `bcy2025-psoc-chart-twc.pdf` | BCY 2025 | 1 | **REMOVE** |
| `bcy-26-psoc-chart-twc.pdf` | BCY 2026 | 1 | **KEEP** |

### Category 2: Payment Rates (HIGH CONFLICT)

| Document | Effective Date | Chunks | Status |
|----------|---------------|--------|--------|
| `bcy26-board-max-provider-payment-rates-twc.pdf` | Oct 1, 2025 | 112 | **KEEP** |
| `bcy25-child-care-provider-payment-rates-twc.pdf` | Jan 13, 2025 | 112 | **REMOVE** |
| `bcy25-board-max-provider-payment-rates-4-age-groups-twc.pdf` | Oct 1, 2024 | 84 | **REMOVE** |

### Category 3: Legislative Reports (MODERATE CONFLICT)

| Document | Legislature | Chunks | Status |
|----------|------------|--------|--------|
| `evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc.pdf` | 89th (2025) | - | **KEEP** |
| `commission-meeting-materials-01.10.23-item3-valuation-effectiveness-child-care-report-88-leg.pdf` | 88th (2023) | - | **REMOVE** |

### Category 4: Historical Meeting Materials (LOW CONFLICT)

| Document | Date | Status |
|----------|------|--------|
| `commission_meeting_material_02.01.22_item10_dp_5th_tranche_crrsa_arpa_projects.pdf` | Feb 2022 | **REMOVE** - COVID-era funding |
| `commission-meeting-material-10.19.21-item16-dp-3rd-tranche-arpa-stabilization-twc.pdf` | Oct 2021 | **REMOVE** - COVID-era funding |

## Specific Contradictions

### Income Eligibility at 85% SMI

| Family Size | BCY 2025 (outdated) | BCY 2026 (current) | Difference |
|-------------|---------------------|--------------------| -----------|
| 2 | $4,971/month | $5,216/month | +$245 |
| 3 | $6,141/month | $6,443/month | +$302 |
| 4 | ~$5,859/month | $7,670/month | +$1,811 |
| 5 | - | $8,897/month | - |

### PSOC Percentage Scale

| Version | SMI Range | Starting PSOC % |
|---------|-----------|-----------------|
| BCY 2025 | 5% - 85% | 2.27% |
| BCY 2026 | 1% - 85% | 2.00% |

## Files in Both Active and Archive Directories

These files exist in both `scraped_content/raw/pdfs/` AND `ARCHIVE/archived_years/`:

```
bcy2025-psoc-chart-twc.pdf
bcy25-board-max-provider-payment-rates-4-age-groups-twc.pdf
bcy25-child-care-provider-payment-rates-twc.pdf
```

## Recommended Actions

### Immediate (Qdrant Cleanup)

1. Delete outdated documents from Qdrant collection `tro-child-hybrid-v1`:
   ```bash
   cd UTIL
   # BCY25 income/payment docs
   python delete_documents.py --filename "bcy2025-psoc-chart-twc.pdf"
   python delete_documents.py --filename "bcy25-child-care-provider-payment-rates-twc.pdf"
   python delete_documents.py --filename "bcy25-board-max-provider-payment-rates-4-age-groups-twc.pdf"
   # Outdated legislative/meeting materials
   python delete_documents.py --filename "commission-meeting-materials-01.10.23-item3-valuation-effectiveness-child-care-report-88-leg.pdf"
   python delete_documents.py --filename "commission_meeting_material_02.01.22_item10_dp_5th_tranche_crrsa_arpa_projects.pdf"
   python delete_documents.py --filename "commission-meeting-material-10.19.21-item16-dp-3rd-tranche-arpa-stabilization-twc.pdf"
   ```

### Short-term (Source Cleanup)

2. Remove outdated PDFs from `scraped_content/raw/pdfs/`:
   ```bash
   # BCY25 income/payment docs
   rm scraped_content/raw/pdfs/bcy2025-psoc-chart-twc.pdf
   rm scraped_content/raw/pdfs/bcy25-child-care-provider-payment-rates-twc.pdf
   rm scraped_content/raw/pdfs/bcy25-board-max-provider-payment-rates-4-age-groups-twc.pdf
   # Outdated legislative/meeting materials
   rm scraped_content/raw/pdfs/commission-meeting-materials-01.10.23-item3-valuation-effectiveness-child-care-report-88-leg.pdf
   rm scraped_content/raw/pdfs/commission_meeting_material_02.01.22_item10_dp_5th_tranche_crrsa_arpa_projects.pdf
   rm scraped_content/raw/pdfs/commission-meeting-material-10.19.21-item16-dp-3rd-tranche-arpa-stabilization-twc.pdf
   ```

### Long-term (Process Improvement)

3. Add fiscal year filtering to the loading pipeline:
   - Option A: Exclude files matching `bcy2[0-4]*` pattern (keep only BCY25+)
   - Option B: Maintain an explicit exclusion list in `LOAD_DB/config.py`
   - Option C: Add metadata field for fiscal year and filter at query time

4. Update scraper to not re-download archived documents:
   - Check if file exists in ARCHIVE before downloading
   - Or maintain a "do not download" list

## Verification

After cleanup, verify with:
```bash
cd UTIL
python retrieve_chunks_by_filename.py --filename "bcy2025-psoc-chart-twc.pdf"
# Should return: "No chunks found"

python retrieve_chunks_by_filename.py --filename "bcy-26-income-eligibility-and-maximum-psoc-twc.pdf"
# Should return: 3 chunks with BCY 2026 data
```

## Related Files

- `LOAD_DB/config.py` - Loading configuration
- `LOAD_DB/load_pdf_qdrant.py` - Main loading script
- `UTIL/delete_documents.py` - Document deletion utility
- `SCRAPER/` - Web scraping pipeline
