"""
Auto-generated test for failed evaluation

Source: bcy-26-psoc-chart-twc-qa.md Q3
Composite Score: 25.0/100 (Failed threshold: 70)
Generated: 2025-11-03 09:14:09

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
    # A family of 4 earning $3,159 per month falls into the 35% State Median Income bracket. For one child in care, their monthly PSoC would be $135, which equals approximately $31 per week. This represents 4.26% of their monthly income.

    # Initialize handler (bypasses intent detection, goes directly to RAG)
    handler = RAGHandler(collection_name=args.collection)

    # Failed question
    question = 'What is the monthly PSoC for a family of 4 with one child in care earning $3,159 per month?'

    # Query chatbot via RAGHandler
    response = handler.handle(question)

    print("QUESTION:")
    print(question)

    print("\nEXPECTED ANSWER:")
    print("""A family of 4 earning $3,159 per month falls into the 35% State Median Income bracket. For one child in care, their monthly PSoC would be $135, which equals approximately $31 per week. This represents 4.26% of their monthly income.""")

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
