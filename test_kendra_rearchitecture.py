"""Test script for rearchitected KendraHandler"""

from chatbot.handlers.kendra_handler import KendraHandler

def test_kendra_handler():
    """Test the rearchitected KendraHandler with a simple query"""

    print("Initializing KendraHandler...")
    handler = KendraHandler()

    # Test query
    query = "What is the Parent Share of Cost (PSoC)?"

    print(f"\nQuery: {query}")
    print("\nRetrieving and generating answer...")

    # Run query with debug mode
    result = handler.handle(query, debug=True)

    # Print results
    print("\n" + "="*80)
    print("ANSWER:")
    print("="*80)
    print(result['answer'])

    print("\n" + "="*80)
    print("SOURCES:")
    print("="*80)
    for i, source in enumerate(result['sources'], 1):
        print(f"{i}. {source['doc']}, Page {source['page']}")
        if source.get('url'):
            print(f"   URL: {source['url']}")

    # Print debug info if available
    if 'debug_info' in result:
        print("\n" + "="*80)
        print("DEBUG INFO:")
        print("="*80)
        print(f"Retrieved {len(result['debug_info']['retrieved_chunks'])} chunks from Kendra")
        for i, chunk in enumerate(result['debug_info']['retrieved_chunks'], 1):
            print(f"\nChunk {i}:")
            print(f"  Doc: {chunk['doc']}, Page: {chunk['page']}")
            print(f"  Score: {chunk['score']}")
            print(f"  Text preview: {chunk['text'][:200]}...")

    print("\n" + "="*80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("="*80)

if __name__ == "__main__":
    test_kendra_handler()
