#!/bin/bash
# Test parallel evaluation modes with 1 question each

echo "Testing parallel evaluation modes..."
echo "===================================="

# Run all three modes in parallel
python -m evaluation.run_evaluation --mode hybrid --limit 1 &
PID_HYBRID=$!

python -m evaluation.run_evaluation --mode dense --limit 1 &
PID_DENSE=$!

python -m evaluation.run_evaluation --mode openai --limit 1 &
PID_OPENAI=$!

# Wait for all to complete
echo "Waiting for all evaluations to complete..."
wait $PID_HYBRID $PID_DENSE $PID_OPENAI

echo ""
echo "===================================="
echo "All evaluations complete!"
echo ""
echo "Results saved to:"
ls -la results/hybrid/ 2>/dev/null && echo ""
ls -la results/dense/ 2>/dev/null && echo ""
ls -la results/openai/ 2>/dev/null
