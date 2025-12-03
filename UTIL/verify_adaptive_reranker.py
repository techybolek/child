#!/usr/bin/env python3
"""
Test the adaptive reranker with the failed Q9 evaluation question.
"""
import sys
import os
sys.path.insert(0, '/home/tromanow/COHORT/TX')

from chatbot.chatbot import TexasChildcareChatbot
import json

def test_q9():
    """Test Q9 that previously failed with score 22.9/100"""

    # The question that failed
    q9_question = "What professional development initiatives were highlighted in the evaluation report?"

    print("=" * 80)
    print("TESTING ADAPTIVE RERANKER WITH Q9")
    print("=" * 80)
    print(f"\nQuestion: {q9_question}")
    print("\n" + "-" * 80)

    # Initialize chatbot (will use adaptive mode from config)
    print("\nInitializing chatbot with adaptive reranker enabled...")
    chatbot = TexasChildcareChatbot()

    # Run the query to see what's happening
    print("Running query...")
    response = chatbot.ask(q9_question)

    # Extract key information
    answer = response.get('answer', '')
    sources = response.get('sources', [])
    debug_info = {}  # No debug mode available

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    # Check if adaptive selection was used
    if 'adaptive_selection' in debug_info:
        adaptive = debug_info['adaptive_selection']
        print(f"\n✓ ADAPTIVE SELECTION USED")
        print(f"  - Chunks selected: {adaptive.get('chunks_selected', 'N/A')}")
        print(f"  - Score range: {adaptive.get('score_range', 'N/A')}")
    else:
        print("\n✗ ADAPTIVE SELECTION NOT DETECTED")

    # Show reranker statistics
    if 'reranker_threshold' in debug_info:
        threshold = debug_info['reranker_threshold']
        print(f"\nReranker Statistics:")
        print(f"  - Total retrieved: {threshold.get('total_retrieved', 0)}")
        print(f"  - Passed to generator: {threshold.get('passed_count', 0)}")
        print(f"  - Cutoff score: {threshold.get('cutoff_score', 0):.2f}")

    # Check if critical information is in the answer
    print("\n" + "-" * 80)
    print("CONTENT VALIDATION")
    print("-" * 80)

    critical_items = [
        ("AgriLife Trainings", "115,837"),
        ("Planning for Individualized Instruction", "441"),
        ("staff retention", None),
        ("TECPDS", None),
        ("CDA credentials", None)
    ]

    found_count = 0
    for item, number in critical_items:
        if item.lower() in answer.lower():
            if number and number in answer:
                print(f"✓ Found: {item} ({number} mentioned)")
                found_count += 1
            elif number:
                print(f"⚠ Found: {item} (but {number} NOT mentioned)")
                found_count += 0.5
            else:
                print(f"✓ Found: {item}")
                found_count += 1
        else:
            print(f"✗ Missing: {item}")

    print(f"\nContent Score: {found_count}/{len(critical_items)} items found")

    # Show the answer
    print("\n" + "=" * 80)
    print("GENERATED ANSWER")
    print("=" * 80)
    print(answer)

    # Show sources used
    print("\n" + "=" * 80)
    print("SOURCES CITED")
    print("=" * 80)
    for source in sources:
        print(f"  - {source['doc']} (Page {source['page']})")

    # Save detailed debug info
    debug_file = '/home/tromanow/COHORT/TX/test_adaptive_debug.json'
    with open(debug_file, 'w') as f:
        json.dump(debug_info, f, indent=2)
    print(f"\nDebug info saved to: {debug_file}")

    return found_count >= 4  # Success if we find at least 4 of 5 critical items

if __name__ == "__main__":
    success = test_q9()

    print("\n" + "=" * 80)
    if success:
        print("✓ TEST PASSED: Adaptive reranker improved Q9 results!")
    else:
        print("✗ TEST FAILED: Still missing critical information")
    print("=" * 80)

    sys.exit(0 if success else 1)