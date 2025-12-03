"""
Shared test definitions and utilities for conversational intelligence tests.
Used by both OAI agent and Custom RAG test runners.
"""

import json
from pathlib import Path

# Test definitions
TESTS = [
    {
        "id": "test_2",
        "name": "Multi-Hop Reasoning",
        "description": "Tests synthesis of information across turns with calculation",
        "turns": [
            "What percentage of SMI determines income eligibility for childcare assistance?",
            "What is the current SMI dollar amount for a family of 4?",
            "Based on what you told me, calculate the exact income cutoff for that family.",
            "If a family of 4 makes $4,500 per month, do they qualify?",
        ],
        "success_criteria": [
            "Retrieves SMI percentage from vector store",
            "Retrieves SMI dollar amount for family of 4",
            "Calculates cutoff by applying percentage to SMI (no re-retrieval needed)",
            "Applies calculated cutoff to specific scenario and gives yes/no answer",
        ]
    },
    {
        "id": "test_2b",
        "name": "Multi-Hop Reasoning (Direct)",
        "description": "Tests synthesis without explicit 'based on what you told me' phrase",
        "turns": [
            "What percentage of SMI determines income eligibility for childcare assistance?",
            "What is the current SMI dollar amount for a family of 4?",
            "Calculate the exact income cutoff for that family.",
            "If a family of 4 makes $4,500 per month, do they qualify?",
        ],
        "success_criteria": [
            "Retrieves SMI percentage from vector store",
            "Retrieves SMI dollar amount for family of 4",
            "Calculates cutoff by applying percentage to SMI (85% × $92,041 = $78,235)",
            "Applies calculated cutoff to specific scenario and gives yes/no answer",
        ]
    },
    {
        "id": "test_5",
        "name": "Topic Switch & Return",
        "description": "Tests context stack management when switching topics and returning",
        "turns": [
            "How do I apply for CCS?",
            "Wait, first tell me about Texas Rising Star",
            "Ok back to my application question",
        ],
        "success_criteria": [
            "Answers TRS question completely",
            "Returns to CCS application without re-asking",
        ]
    },
    {
        "id": "test_3",
        "name": "Negation & Filtering",
        "description": "Tests filtering by negation and ranking results",
        "turns": [
            "What childcare programs require employment to qualify?",
            "Which ones don't require employment?",
            "Of those, which have the highest income limits?",
        ],
        "success_criteria": [
            "Lists programs requiring employment",
            "Correctly filters to programs WITHOUT employment requirement",
            "Ranks filtered programs by income limit",
        ]
    },
    {
        "id": "test_4",
        "name": "Correction Handling",
        "description": "Tests clean pivot when user corrects prior input",
        "turns": [
            "What are the income limits for a family of 4?",
            "Sorry, I meant family of 6",
            "And what documents do I need to prove that income?",
        ],
        "success_criteria": [
            "Provides family of 4 limits initially",
            "Cleanly replaces with family of 6 limits (not blends)",
            "Maintains family of 6 context for document question",
        ]
    },
    {
        "id": "test_6",
        "name": "Comparative Reasoning",
        "description": "Tests comparison across entities with evolving constraints",
        "turns": [
            "What's the difference between CCS and CCMS?",
            "Which one is better for a single mom working part-time?",
            "What if she's also a student?",
        ],
        "success_criteria": [
            "Compares both programs clearly",
            "Applies part-time work constraint to recommendation",
            "Adjusts recommendation with student status",
        ]
    },
    {
        "id": "test_7",
        "name": "Hypothetical Application",
        "description": "Tests applying rules to specific user scenario",
        "turns": [
            "I'm a single parent with 2 kids, making $35,000/year",
            "Do I qualify for childcare assistance?",
            "What if I get a raise to $45,000?",
        ],
        "success_criteria": [
            "Acknowledges user's specific situation",
            "Applies eligibility rules to $35k scenario",
            "Re-evaluates with $45k (not retrieves fresh)",
        ]
    },
    {
        "id": "test_8",
        "name": "Temporal Process Reasoning",
        "description": "Tests tracking process sequence across turns",
        "turns": [
            "What happens after I submit my CCS application?",
            "How long does that take?",
            "What if they need more documents from me?",
            "And after that?",
        ],
        "success_criteria": [
            "Describes post-submission process",
            "Resolves 'that' to review/processing step",
            "Explains document request scenario",
            "Continues sequence from document submission",
        ]
    }
]


def get_output_dir() -> Path:
    """Get the test results output directory."""
    output_dir = Path(__file__).parent / "test_results"
    output_dir.mkdir(exist_ok=True)
    return output_dir


def save_results(results: dict, prefix: str) -> Path:
    """Save JSON results. Returns the output path."""
    output_dir = get_output_dir()
    output_file = output_dir / f"{prefix}.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    return output_file


def write_report(results: dict, prefix: str, system_name: str) -> Path:
    """Write human-readable report. Returns the report path."""
    output_dir = get_output_dir()
    report_file = output_dir / f"{prefix}.txt"

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
