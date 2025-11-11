rm -f results/debug_eval.txt
source .venv/bin/activate && python -m evaluation.run_evaluation --investigate
