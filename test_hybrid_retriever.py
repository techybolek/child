"""
Test hybrid retriever with BCY-26 query (known failure case for dense-only)
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from chatbot.hybrid_retriever import QdrantHybridRetriever
from chatbot import config

def test_hybrid_retriever():
    """Test hybrid retriever with BCY-26 query"""
    print("=" * 80)
    print("HYBRID RETRIEVER TEST: BCY-26 Query")
    print("=" * 80)

    # Temporarily enable hybrid retrieval
    original_flag = config.ENABLE_HYBRID_RETRIEVAL
    config.ENABLE_HYBRID_RETRIEVAL = True

    try:
        # Initialize retriever
        print(f"\nInitializing QdrantHybridRetriever...")
        retriever = QdrantHybridRetriever()

        # Test query (known failure case for dense-only)
        query = "What is BCY-26?"
        print(f"\nQuery: '{query}'")
        print("-" * 80)

        # Search
        results = retriever.search(query, top_k=5)

        print(f"\nReturned {len(results)} results:")
        print("=" * 80)

        for i, chunk in enumerate(results, 1):
            print(f"\n[{i}] Score: {chunk['score']:.4f}")
            print(f"    Document: {chunk['filename']}")
            print(f"    Page: {chunk['page']}")
            print(f"    Text preview: {chunk['text'][:200]}...")

        # Check if BCY-26 is mentioned in results
        bcy26_found = any('BCY-26' in chunk['text'] or 'bcy-26' in chunk['text'].lower()
                         for chunk in results)

        print("\n" + "=" * 80)
        if bcy26_found:
            print("✅ SUCCESS: BCY-26 found in results!")
        else:
            print("❌ FAILURE: BCY-26 NOT found in results")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        config.ENABLE_HYBRID_RETRIEVAL = original_flag

if __name__ == '__main__':
    test_hybrid_retriever()
