"""
Auto-generated test for failed evaluation

Source: bcy-26-psoc-chart-twc-qa.md Q2
Composite Score: 45.8/100 (Failed threshold: 70)
Generated: 2025-11-03 18:54:37

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
    # The PSoC includes an add-on percentage for each additional child beyond the first child. This add-on varies by income level - for example, at 15% SMI, there\'s a 0.225% add-on per additional child, while at 35% SMI it\'s 0.525%. Notably, at 85% SMI (the highest income bracket), there is no additional charge for extra children (0.000% add-on). At higher income levels (75% and 85% SMI), the add-on is significantly lower at 0.072% and 0.000% respectively.

    # Initialize handler (bypasses intent detection, goes directly to RAG)
    handler = RAGHandler(collection_name=args.collection)

    # Failed question
    question = 'How does the PSoC change when families have multiple children in care?'

    # Query chatbot via RAGHandler
    response = handler.handle(question)

    print("QUESTION:")
    print(question)

    print("\nEXPECTED ANSWER:")
    print("""The PSoC includes an add-on percentage for each additional child beyond the first child. This add-on varies by income level - for example, at 15% SMI, there\'s a 0.225% add-on per additional child, while at 35% SMI it\'s 0.525%. Notably, at 85% SMI (the highest income bracket), there is no additional charge for extra children (0.000% add-on). At higher income levels (75% and 85% SMI), the add-on is significantly lower at 0.072% and 0.000% respectively.""")

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
