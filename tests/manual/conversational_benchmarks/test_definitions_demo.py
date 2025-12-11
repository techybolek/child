"""
Shared test definitions and utilities for conversational intelligence tests.
Used by both OAI agent and Custom RAG test runners.
"""

import json
from datetime import datetime
from pathlib import Path

# Test definitions
TESTS = [
    {
        "name": "Multi-Hop Reasoning (Direct)",
        "description": "Tests synthesis without explicit 'based on what you told me' phrase",
        "turns": [
            "What assistance can expect a family of 4?"
            "Calculate the exact income cutoff for that family.",
            "What about 5?",
        ]
    },
    ####################################################################################################
    {
        "name": "Topic Switch & Return",
        "description": "Tests context stack management when switching topics and returning",
        "turns": [
            "How do I apply for CCS?",
            "Wait, first tell me about Texas Rising Star",
            "Compare these two"
        ]
    },
    ####################################################################################################
    {
        "name": "Negation & Filtering",
        "description": "Tests filtering by negation and ranking results",
        "turns": [
            "What childcare programs require employment to qualify?",
            "Which ones don't require employment?",
        ]
    },
    ####################################################################################################
    {
        "name": "Correction Handling",
        "description": "Tests clean pivot when user corrects prior input",
        "turns": [
            "What are the income limits for a family of 4?",
            "Sorry, I meant 6",
            "And what documents do I need to prove that income?",
        ],
        "success_criteria": [
            "Provides family of 4 limits initially",
            "Cleanly replaces with family of 6 limits (not blends)",
            "Maintains family of 6 context for document question",
        ]
    },
    ####################################################################################################
    {
        "name": "Hypothetical Application",
        "description": "Tests applying rules to specific user scenario",
        "turns": [
            "I'm a single parent with 2 kids, making $35,000/year. Do I qualify for childcare assistance?",
            "What if I get a raise to $45,000?",
        ]
    },
    ####################################################################################################
    {
        "name": "Temporal Process Reasoning",
        "description": "Tests tracking process sequence across turns",
        "turns": [
            "What happens after I submit my CCS application?",
            "How long does that take?",
            "What if they need more documents from me?",
            "And after that?",
        ]
    }
]


def get_output_dir(system: str) -> Path:
    """Get timestamped output directory for a system.

    Args:
        system: 'rag' or 'openai'

    Returns:
        Path to results/conversational_benchmarks/{system}/RUN_{timestamp}/
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Navigate from tests/manual/conversational_benchmarks/ to project root
    base = Path(__file__).parent.parent.parent.parent / "results" / "conversational_benchmarks"
    output_dir = base / system / f"RUN_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_results(results: dict, system: str) -> Path:
    """Save JSON results. Returns the output path."""
    output_dir = get_output_dir(system)
    output_file = output_dir / "results.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    return output_file


def write_report(results: dict, system: str, system_name: str) -> Path:
    """Write human-readable report. Returns the report path."""
    # Use same directory as results.json (get from parent of results file)
    output_dir = get_output_dir(system)
    report_file = output_dir / "report.txt"

    with open(report_file, "w") as f:
        f.write(f"CONVERSATIONAL INTELLIGENCE TEST REPORT - {system_name.upper()}\n")
        f.write(f"System: {system_name}\n")
        f.write("=" * 60 + "\n\n")

        for test in results["tests"]:
            f.write(f"TEST: {test['test_name']}\n")
            f.write(f"Description: {test['description']}\n")
            if "thread_id" in test:
                f.write(f"Thread ID: {test['thread_id']}\n")
            f.write("-" * 40 + "\n\n")

            for turn in test["turns"]:
                f.write(f"[Turn {turn['turn']}] User:\n{turn['user']}\n\n")
                if turn.get("reformulated_query") and turn["reformulated_query"] != turn["user"]:
                    f.write(f"[Turn {turn['turn']}] Reformulated:\n{turn['reformulated_query']}\n\n")
                f.write(f"[Turn {turn['turn']}] Assistant:\n{turn['assistant']}\n\n")
                f.write(f"(Response time: {turn['elapsed_seconds']}s)\n")
                if turn.get("sources"):
                    f.write(f"Sources: {len(turn['sources'])} chunks\n")
                f.write("-" * 40 + "\n\n")

            f.write("Success Criteria:\n")
            for criterion in test["success_criteria"]:
                f.write(f"  - {criterion}\n")
            f.write("\n" + "=" * 60 + "\n\n")

    return report_file
