"""
End-to-end test for the OpenAI Agent evaluation mode.

Runs a minimal evaluation ONCE and validates all artifacts are created correctly.

Usage:
    pytest tests/test_evaluation_e2e_openai.py -v
    python tests/test_evaluation_e2e_openai.py  # Direct execution

Note: OpenAI mode has higher latency (~5-8s per question) so timeout is extended.
"""

import json
import subprocess
import sys
from pathlib import Path

# Test configuration
SANITY_QA_FILE = "test-sanity-qa.md"
MODE = "openai"
RUN_NAME = "TEST_OPENAI"
MIN_EXPECTED_QUESTIONS = 3
MIN_PASS_SCORE = 60.0
TIMEOUT = 600  # Extended timeout for OpenAI's higher latency


class EvaluationResult:
    """Singleton to hold evaluation result - runs once, validates many times."""
    _instance = None
    _has_run = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def run(self):
        """Run evaluation if not already run."""
        if self._has_run:
            return self

        # Clear any existing checkpoint
        checkpoint_path = Path(f"results/{MODE}/checkpoint.json")
        if checkpoint_path.exists():
            checkpoint_path.unlink()

        cmd = [
            sys.executable, "-m", "evaluation.run_evaluation",
            "--mode", MODE,
            "--file", SANITY_QA_FILE,
            "--run-name", RUN_NAME,
            "--clear-checkpoint"
        ]

        self.process_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )

        self._has_run = True

        # Find run directory
        if self.process_result.returncode == 0:
            mode_dir = Path(f"results/{MODE}")
            run_dirs = sorted(mode_dir.glob(f"{RUN_NAME}_*"), reverse=True)
            self.run_dir = run_dirs[0] if run_dirs else None
        else:
            self.run_dir = None

        return self


# Module-level instance
_eval_result = EvaluationResult()


def get_eval_result():
    """Get the singleton evaluation result, running if needed."""
    return _eval_result.run()


def test_evaluation_completes_successfully():
    """Test that evaluation runs without errors."""
    result = get_eval_result()

    assert result.process_result.returncode == 0, (
        f"Evaluation failed with return code {result.process_result.returncode}\n"
        f"STDOUT:\n{result.process_result.stdout}\n"
        f"STDERR:\n{result.process_result.stderr}"
    )

    assert "Evaluation complete!" in result.process_result.stdout, (
        f"Expected 'Evaluation complete!' in output.\n"
        f"STDOUT:\n{result.process_result.stdout}"
    )


def test_artifacts_created():
    """Test that all expected output files are created."""
    result = get_eval_result()
    assert result.run_dir is not None, "No run directory found"

    required_files = [
        "detailed_results.jsonl",
        "evaluation_summary.json",
        "evaluation_report.txt",
        "run_info.txt"
    ]

    for filename in required_files:
        filepath = result.run_dir / filename
        assert filepath.exists(), f"Missing required file: {filepath}"
        assert filepath.stat().st_size > 0, f"File is empty: {filepath}"


def test_detailed_results_format():
    """Test that detailed_results.jsonl has correct structure."""
    result = get_eval_result()
    assert result.run_dir is not None, "No run directory found"

    results_file = result.run_dir / "detailed_results.jsonl"

    results = []
    with open(results_file) as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))

    assert len(results) >= MIN_EXPECTED_QUESTIONS, (
        f"Expected at least {MIN_EXPECTED_QUESTIONS} results, got {len(results)}"
    )

    required_fields = [
        "source_file", "question_num", "question", "expected_answer",
        "chatbot_answer", "sources", "response_time", "scores"
    ]

    for i, entry in enumerate(results):
        for field in required_fields:
            assert field in entry, f"Result {i} missing required field: {field}"

        scores = entry["scores"]
        assert "accuracy" in scores, f"Result {i} missing accuracy score"
        assert "completeness" in scores, f"Result {i} missing completeness score"
        assert "coherence" in scores, f"Result {i} missing coherence score"
        assert "composite_score" in scores, f"Result {i} missing composite_score"


def test_summary_statistics():
    """Test that evaluation_summary.json has valid statistics."""
    result = get_eval_result()
    assert result.run_dir is not None, "No run directory found"

    summary_file = result.run_dir / "evaluation_summary.json"

    with open(summary_file) as f:
        summary = json.load(f)

    assert "timestamp" in summary
    assert "total_evaluated" in summary
    assert "average_scores" in summary
    assert "performance" in summary

    assert summary["total_evaluated"] >= MIN_EXPECTED_QUESTIONS

    avg = summary["average_scores"]
    assert 0 <= avg["accuracy"] <= 5, f"Invalid accuracy: {avg['accuracy']}"
    assert 0 <= avg["completeness"] <= 5, f"Invalid completeness: {avg['completeness']}"
    assert 0 <= avg["coherence"] <= 3, f"Invalid coherence: {avg['coherence']}"
    assert 0 <= avg["composite"] <= 100, f"Invalid composite: {avg['composite']}"


def test_pass_rate_acceptable():
    """Test that the sanity questions achieve minimum pass rate."""
    result = get_eval_result()
    assert result.run_dir is not None, "No run directory found"

    summary_file = result.run_dir / "evaluation_summary.json"

    with open(summary_file) as f:
        summary = json.load(f)

    composite_score = summary["average_scores"]["composite"]

    assert composite_score >= MIN_PASS_SCORE, (
        f"Composite score {composite_score:.1f} below minimum {MIN_PASS_SCORE}. "
        f"Sanity test questions should pass reliably."
    )


def test_no_checkpoint_left_on_success():
    """Test that checkpoint is cleared after successful completion."""
    result = get_eval_result()
    assert result.process_result.returncode == 0, "Evaluation failed"

    checkpoint_path = Path(f"results/{MODE}/checkpoint.json")

    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        assert checkpoint.get("completed", False) or \
               len(checkpoint.get("completed_pairs", [])) >= MIN_EXPECTED_QUESTIONS, (
            "Checkpoint exists but evaluation not marked complete"
        )


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        ("Evaluation completes successfully", test_evaluation_completes_successfully),
        ("Artifacts created", test_artifacts_created),
        ("Detailed results format", test_detailed_results_format),
        ("Summary statistics", test_summary_statistics),
        ("Pass rate acceptable", test_pass_rate_acceptable),
        ("No checkpoint left on success", test_no_checkpoint_left_on_success),
    ]

    print("=" * 70)
    print(f"EVALUATION FRAMEWORK END-TO-END TEST ({MODE.upper()} MODE)")
    print("=" * 70)
    print()

    # Run evaluation once upfront
    print("Running evaluation (once)...", flush=True)
    result = get_eval_result()
    if result.process_result.returncode == 0:
        print(f"✓ Evaluation completed successfully")
        print(f"  Run directory: {result.run_dir}")
    else:
        print(f"✗ Evaluation failed")
        print(f"  STDERR: {result.process_result.stderr[:500]}")
    print()

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"Validating: {name}...", end=" ", flush=True)
            test_func()
            print("✓ PASSED")
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR")
            print(f"  {type(e).__name__}: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
