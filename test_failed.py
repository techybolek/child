"""
Auto-generated test for failed evaluation

Source: bcy-26-psoc-chart-twc-qa.md Q8
Composite Score: 66.7/100 (Failed threshold: 70)
Generated: 2025-11-05 12:54:33

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
    # The document recommends using the PSoC Calculator to determine the exact PSoC amount based on your family\'s specific situation. The calculator takes into account three key factors: family size, monthly income, and the number of children in care, providing precise monthly and weekly PSoC amounts.

    # Initialize handler (bypasses intent detection, goes directly to RAG)
    handler = RAGHandler(collection_name=args.collection)

    # Failed question
    question = 'What tool is recommended for calculating the exact PSoC amount for a family?'

    # Query chatbot via RAGHandler
    response = handler.handle(question)

    print("QUESTION:")
    print(question)

    print("\nEXPECTED ANSWER:")
    print("""The document recommends using the PSoC Calculator to determine the exact PSoC amount based on your family\'s specific situation. The calculator takes into account three key factors: family size, monthly income, and the number of children in care, providing precise monthly and weekly PSoC amounts.""")

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
