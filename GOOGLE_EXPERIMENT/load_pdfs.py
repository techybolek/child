import vertexai
from vertexai.preview import rag
from pathlib import Path
import time

# Configuration
PROJECT_ID = "docker-app-20250605"
LOCATION = "us-west1"
CORPUS_NAME = "projects/112470053465/locations/us-west1/ragCorpora/2305843009213693952"
PDF_DIR = Path("../scraped_content/raw/pdfs")

# Initialize
vertexai.init(project=PROJECT_ID, location=LOCATION)

def upload_pdfs():
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files to upload")

    # Get corpus - you need to update CORPUS_NAME with actual corpus resource name
    # Format: projects/{project}/locations/{location}/ragCorpora/{corpus_id}

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Uploading: {pdf_path.name}")
        start = time.time()

        try:
            rag_file = rag.upload_file(
                corpus_name=CORPUS_NAME,
                path=str(pdf_path.absolute()),
                display_name=pdf_path.stem,
            )
            elapsed = time.time() - start
            print(f"  Success: {rag_file.name} ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  Error: {e}")

    print("\nUpload complete!")

if __name__ == "__main__":
    upload_pdfs()
