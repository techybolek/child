import json
from pathlib import Path
from datetime import datetime
from .qa_parser import load_all_qa_pairs, parse_qa_file
from .evaluator import ChatbotEvaluator
from .judge import LLMJudge
from . import config


class BatchEvaluator:
    def __init__(self):
        self.evaluator = ChatbotEvaluator()
        self.judge = LLMJudge()

    def evaluate_all(self, limit: int = None):
        """Evaluate all Q&A pairs"""
        print(f"Loading Q&A pairs from {config.QA_DIR}...")
        qa_pairs = load_all_qa_pairs(config.QA_DIR)

        if limit:
            qa_pairs = qa_pairs[:limit]

        print(f"Found {len(qa_pairs)} Q&A pairs")
        return self._evaluate_batch(qa_pairs)

    def evaluate_file(self, filename: str):
        """Evaluate Q&A pairs from a single file"""
        file_path = Path(config.QA_DIR) / filename
        print(f"Loading Q&A pairs from {file_path}...")
        qa_pairs = parse_qa_file(str(file_path))
        print(f"Found {len(qa_pairs)} Q&A pairs")
        return self._evaluate_batch(qa_pairs)

    def _evaluate_batch(self, qa_pairs: list) -> dict:
        """Evaluate a batch of Q&A pairs"""
        results = []
        stats = {
            'total': len(qa_pairs),
            'processed': 0,
            'failed': 0,
            'total_response_time': 0
        }

        print(f"\nStarting evaluation...")
        print("=" * 80)

        for i, qa in enumerate(qa_pairs, 1):
            print(f"\n[{i}/{len(qa_pairs)}] Processing: {qa['source_file']} Q{qa['question_num']}")
            print(f"Question: {qa['question'][:80]}...")

            try:
                # Query chatbot
                print("  → Querying chatbot...")
                chatbot_response = self.evaluator.query(qa['question'])
                print(f"  ✓ Response received ({chatbot_response['response_time']:.2f}s)")
            except Exception as e:
                print(f"\n❌ ERROR: Failed to query chatbot")
                print(f"Question: {qa['question']}")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                raise

            try:
                # Judge response
                print("  → Judging response...")
                scores = self.judge.evaluate(
                    question=qa['question'],
                    expected_answer=qa['expected_answer'],
                    chatbot_answer=chatbot_response['answer'],
                    sources=chatbot_response['sources']
                )
                print(f"  ✓ Score: {scores['composite_score']:.1f}/100")
            except Exception as e:
                print(f"\n❌ ERROR: Failed to judge response")
                print(f"Question: {qa['question']}")
                print(f"Chatbot answer: {chatbot_response['answer'][:200]}...")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                raise

            # Check if score is below threshold - stop immediately if so
            if scores['composite_score'] < config.STOP_ON_FAIL_THRESHOLD:
                self._print_failure_and_stop(qa, chatbot_response, scores)

            # Store result
            result = {
                'source_file': qa['source_file'],
                'question_num': qa['question_num'],
                'question': qa['question'],
                'expected_answer': qa['expected_answer'],
                'chatbot_answer': chatbot_response['answer'],
                'sources': chatbot_response['sources'],
                'response_type': chatbot_response['response_type'],
                'response_time': chatbot_response['response_time'],
                'scores': scores
            }
            results.append(result)

            # Update stats
            stats['processed'] += 1
            stats['total_response_time'] += chatbot_response['response_time']

            # Checkpoint
            if i % config.CHECKPOINT_INTERVAL == 0:
                self._save_checkpoint(results, stats)

        print("\n" + "=" * 80)
        print(f"Evaluation complete! Processed {stats['processed']}/{stats['total']} pairs")

        return {
            'results': results,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

    def _save_checkpoint(self, results: list, stats: dict):
        """Save checkpoint"""
        checkpoint_file = Path(config.RESULTS_DIR) / f"checkpoint_{stats['processed']}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump({'results': results, 'stats': stats}, f, indent=2)
        print(f"\n  💾 Checkpoint saved: {checkpoint_file}")

    def _print_failure_and_stop(self, qa: dict, chatbot_response: dict, scores: dict):
        """Print detailed failure information and stop evaluation"""
        print("\n" + "=" * 80)
        print("⚠️  LOW SCORE DETECTED - STOPPING EVALUATION")
        print("=" * 80)
        print(f"Source: {qa['source_file']} Q{qa['question_num']}")
        print(f"Composite Score: {scores['composite_score']:.1f}/100 (Threshold: {config.STOP_ON_FAIL_THRESHOLD})")

        print("\nQUESTION:")
        print(qa['question'])

        print("\nEXPECTED ANSWER:")
        print(qa['expected_answer'])

        print("\nCHATBOT ANSWER:")
        print(chatbot_response['answer'])

        print("\nSCORES:")
        print(f"  Factual Accuracy:    {scores['accuracy']:.1f}/5")
        print(f"  Completeness:        {scores['completeness']:.1f}/5")
        print(f"  Citation Quality:    {scores['citation_quality']:.1f}/5")
        print(f"  Coherence:           {scores['coherence']:.1f}/3")
        print(f"  Composite:           {scores['composite_score']:.1f}/100")

        print("\nJUDGE REASONING:")
        print(scores['reasoning'])

        if chatbot_response['sources']:
            print("\nSOURCES CITED:")
            for source in chatbot_response['sources']:
                print(f"  - {source['doc']}, Page {source['page']}")
        else:
            print("\nSOURCES CITED: None")

        print("=" * 80)

        self._generate_test_file(qa, chatbot_response, scores)

        raise SystemExit(f"Evaluation stopped due to low score ({scores['composite_score']:.1f} < {config.STOP_ON_FAIL_THRESHOLD})")

    def _generate_test_file(self, qa: dict, chatbot_response: dict, scores: dict):
        """Generate test_failed.py for the failed question"""
        # Escape single quotes in strings for the generated code
        question = qa['question'].replace("'", "\\'")
        expected_answer = qa['expected_answer'].replace("'", "\\'")
        source_file = qa['source_file'].replace("'", "\\'")

        # Generate test file content
        test_content = f'''"""
Auto-generated test for failed evaluation

Source: {source_file} Q{qa['question_num']}
Composite Score: {scores['composite_score']:.1f}/100 (Failed threshold: {config.STOP_ON_FAIL_THRESHOLD})
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from chatbot.handlers.rag_handler import RAGHandler

# Expected answer (from Q&A file):
# {expected_answer}

# Initialize handler (bypasses intent detection, goes directly to RAG)
handler = RAGHandler()

# Failed question
question = '{question}'

# Query chatbot via RAGHandler
response = handler.handle(question)

print("QUESTION:")
print(question)

print("\\nEXPECTED ANSWER:")
print("""{expected_answer}""")

print("\\nCHATBOT ANSWER:")
print(response['answer'])

print("\\nSOURCES:")
if response['sources']:
    for source in response['sources']:
        print(f"- {{source['doc']}}, Page {{source['page']}}")
else:
    print("No sources cited")
'''

        # Write to test_failed.py in project root
        test_file = Path('.') / 'test_failed.py'
        with open(test_file, 'w') as f:
            f.write(test_content)

        print(f"\n✨ Generated test_failed.py for quick debugging")
        print(f"   Run with: python test_failed.py")
