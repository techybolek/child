"""
Auto-generated test for failed evaluation

Source: bcy-26-psoc-chart-twc-qa.md Q5
Composite Score: 45.8/100 (Failed threshold: 70)
Generated: 2025-11-04 11:58:34

Usage:
    python test_failed.py                          # Use default collection
    python test_failed.py --collection tro-child-1  # Use specific collection
"""

import argparse
from chatbot.handlers.rag_handler import RAGHandler


def main():
    parser = argparse.ArgumentParser(description='Test failed evaluation question')
    parser.add_argument('--collection', type=str, help='Qdrant collection name')
    args = parser.parse_args()

    # Expected answer (from Q&A file):
    # For a family of 5, the monthly income thresholds are: $105 (1% SMI), $1,571 (15% SMI), $2,617 (25% SMI), $3,664 (35% SMI), $4,711 (45% SMI), $5,757 (55% SMI), $6,804 (65% SMI), $7,851 (75% SMI), and $8,897 (85% SMI). These thresholds determine which sliding fee scale bracket the family falls into.

    # Initialize handler (bypasses intent detection, goes directly to RAG)
    handler = RAGHandler(collection_name=args.collection)

    # Failed question
    question = 'What income levels correspond to each State Median Income (SMI) percentage for a family of 5?'

    # Query chatbot via RAGHandler
    response = handler.handle(question)

    print("QUESTION:")
    print(question)

    print("\nEXPECTED ANSWER:")
    print("""For a family of 5, the monthly income thresholds are: $105 (1% SMI), $1,571 (15% SMI), $2,617 (25% SMI), $3,664 (35% SMI), $4,711 (45% SMI), $5,757 (55% SMI), $6,804 (65% SMI), $7,851 (75% SMI), and $8,897 (85% SMI). These thresholds determine which sliding fee scale bracket the family falls into.""")

    print("\nCHATBOT ANSWER:")
    print(response['answer'])

    print("\nSOURCES:")
    if response['sources']:
        for source in response['sources']:
            print(f"- {source['doc']}, Page {source['page']}")
    else:
        print("No sources cited")


if __name__ == '__main__':
    main()
