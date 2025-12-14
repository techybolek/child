#!/bin/bash
# Validation script for Bedrock Knowledge Base Evaluator
# Runs all tests and commands to verify the implementation

echo "========================================"
echo "BEDROCK KB EVALUATOR VALIDATION"
echo "========================================"
echo ""

# Track results
PASSED=0
FAILED=0

run_test() {
    local name="$1"
    local cmd="$2"
    echo "----------------------------------------"
    echo "TEST: $name"
    echo "CMD: $cmd"
    echo "----------------------------------------"
    if eval "$cmd"; then
        echo "✓ PASSED: $name"
        ((PASSED++))
    else
        echo "✗ FAILED: $name"
        ((FAILED++))
    fi
    echo ""
}

# 1. Check AWS credentials
echo "Checking AWS credentials..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✓ AWS credentials configured"
else
    echo "✗ AWS credentials not configured - skipping Bedrock tests"
    exit 1
fi
echo ""

# 2. Verify 'bedrock' appears in CLI help
run_test "CLI help shows bedrock mode" \
    "python -m evaluation.run_evaluation --help 2>&1 | grep -q 'bedrock'"

# 3. Quick evaluation test
run_test "Quick evaluation (limit 3)" \
    "python -m evaluation.run_evaluation --mode bedrock --test --limit 3 --no-stop-on-fail"

# 4. Debug mode with sanity questions
run_test "Debug mode with sanity questions" \
    "python -m evaluation.run_evaluation --mode bedrock --file test-sanity-qa.md --debug --no-stop-on-fail"

# 5. E2E pytest for bedrock mode
run_test "E2E pytest for bedrock" \
    "pytest tests/test_evaluation_e2e_bedrock.py -v"

# 6. Regression tests for existing modes
run_test "Regression test - hybrid E2E" \
    "pytest tests/test_evaluation_e2e.py -v"

run_test "Regression test - kendra E2E" \
    "pytest tests/test_evaluation_e2e_kendra.py -v"

# Summary
echo "========================================"
echo "VALIDATION SUMMARY"
echo "========================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "========================================"

if [ $FAILED -gt 0 ]; then
    echo "✗ VALIDATION FAILED"
    exit 1
else
    echo "✓ ALL TESTS PASSED"
    exit 0
fi
