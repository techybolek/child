"""
Auto-generated test for failed evaluation

Source: child-care-provider-desk-aid-twc-qa.md Q1
Composite Score: 8.3/100 (Failed threshold: 70)
Generated: 2025-11-05 16:38:40

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
    # The Child Care Provider Desk Aid is a guide that helps child care providers learn how to use WorkInTexas.com to post job openings and search for candidates for their child care programs. It provides step-by-step instructions for registering as an employer, creating job postings (called job orders), and searching for potential employees through the WorkInTexas.com platform.

    # Initialize handler (bypasses intent detection, goes directly to RAG)
    handler = RAGHandler(collection_name=args.collection)

    # Failed question
    question = 'What is the purpose of the Child Care Provider Desk Aid?'

    # Query chatbot via RAGHandler
    response = handler.handle(question)

    print("QUESTION:")
    print(question)

    print("\nEXPECTED ANSWER:")
    print("""The Child Care Provider Desk Aid is a guide that helps child care providers learn how to use WorkInTexas.com to post job openings and search for candidates for their child care programs. It provides step-by-step instructions for registering as an employer, creating job postings (called job orders), and searching for potential employees through the WorkInTexas.com platform.""")

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
