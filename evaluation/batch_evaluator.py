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

            # Query chatbot
            print("  → Querying chatbot...")
            chatbot_response = self.evaluator.query(qa['question'])
            print(f"  ✓ Response received ({chatbot_response['response_time']:.2f}s)")

            # Judge response
            print("  → Judging response...")
            scores = self.judge.evaluate(
                question=qa['question'],
                expected_answer=qa['expected_answer'],
                chatbot_answer=chatbot_response['answer'],
                sources=chatbot_response['sources']
            )
            print(f"  ✓ Score: {scores['composite_score']:.1f}/100")

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
