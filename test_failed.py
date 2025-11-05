"""
Auto-generated test for failed evaluation

Source: child-care-provider-desk-aid-twc-qa.md Q3
Composite Score: 4.2/100 (Failed threshold: 70)
Generated: 2025-11-05 16:51:39

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
    # The three representative types are: (1) Direct Representative of your Organization - which includes employees, principals, and owners of the organization that is registering; (2) Third Party Agents (TPA) - companies that represent one or more registered organizations and perform activities on their behalf; and (3) Professional Employer Organization (PEO) - companies that manage payroll for one or more registered organizations and serve as the employer of record for tax and insurance purposes.

    # Initialize handler (bypasses intent detection, goes directly to RAG)
    handler = RAGHandler(collection_name=args.collection)

    # Failed question
    question = 'What are the three representative types available when registering on WorkInTexas.com?'

    # Query chatbot via RAGHandler
    response = handler.handle(question)

    print("QUESTION:")
    print(question)

    print("\nEXPECTED ANSWER:")
    print("""The three representative types are: (1) Direct Representative of your Organization - which includes employees, principals, and owners of the organization that is registering; (2) Third Party Agents (TPA) - companies that represent one or more registered organizations and perform activities on their behalf; and (3) Professional Employer Organization (PEO) - companies that manage payroll for one or more registered organizations and serve as the employer of record for tax and insurance purposes.

---""")

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
