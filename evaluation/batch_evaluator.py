import json
from pathlib import Path
from datetime import datetime
from .qa_parser import load_all_qa_pairs, parse_qa_file
from .evaluator import ChatbotEvaluator
from .judge import LLMJudge
from . import config


class BatchEvaluator:
    def __init__(self, collection_name=None, resume=False, resume_limit=None, debug=False, retrieval_top_k=None, clear_checkpoint=False):
        self.evaluator = ChatbotEvaluator(collection_name=collection_name, retrieval_top_k=retrieval_top_k)
        self.judge = LLMJudge()
        self.resume = resume
        self.resume_limit = resume_limit
        self.debug = debug
        self.retrieval_top_k = retrieval_top_k
        self.clear_checkpoint = clear_checkpoint

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

        # Track if this is a partial resume (for checkpoint cleanup decision)
        partial_resume = False

        # Check for existing checkpoint
        checkpoint_file = Path(config.RESULTS_DIR) / "checkpoint.json"
        if checkpoint_file.exists():
            if self.resume:
                print(f"\n📂 Loading checkpoint from {checkpoint_file}...")
                checkpoint_data = self._load_checkpoint(checkpoint_file)
                results = checkpoint_data['results']
                stats = checkpoint_data['stats']

                # Build set of processed questions to skip
                processed = {(r['source_file'], r['question_num']) for r in results}
                qa_pairs = [qa for qa in qa_pairs if (qa['source_file'], qa['question_num']) not in processed]

                total_remaining = len(qa_pairs)

                # Apply resume-limit if specified
                if self.resume_limit is not None:
                    qa_pairs = qa_pairs[:self.resume_limit]
                    partial_resume = (len(qa_pairs) < total_remaining)
                    print(f"✓ Resuming from checkpoint: {len(results)} already processed")
                    print(f"  Processing {len(qa_pairs)} of {total_remaining} remaining (--resume-limit {self.resume_limit})")
                else:
                    print(f"✓ Resuming from checkpoint: {len(results)} already processed, {len(qa_pairs)} remaining")

                stats['total'] = len(results) + len(qa_pairs)
            else:
                print(f"\n⚠️  Checkpoint file exists: {checkpoint_file}")
                print("Use --resume flag to resume from checkpoint, or delete the file to start fresh")
                raise SystemExit("Checkpoint exists. Use --resume to continue or delete checkpoint file.")

        print(f"\nStarting evaluation...")
        print("=" * 80)

        for i, qa in enumerate(qa_pairs, 1):
            print(f"\n[{i}/{len(qa_pairs)}] Processing: {qa['source_file']} Q{qa['question_num']}")
            print(f"Question: {qa['question'][:80]}...")

            try:
                # Query chatbot
                print("  → Querying chatbot...")
                chatbot_response = self.evaluator.query(qa['question'], debug=self.debug)
                print(f"  ✓ Response received ({chatbot_response['response_time']:.2f}s)")

                # Print debug info if enabled
                if self.debug and 'debug_info' in chatbot_response:
                    self._print_debug_info(chatbot_response['debug_info'])
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

                # Create fallback score to trigger graceful exit with test_failed.py generation
                scores = {
                    'accuracy': 0,
                    'completeness': 0,
                    'citation_quality': 0,
                    'coherence': 0,
                    'composite_score': 0,
                    'reasoning': f"Judge evaluation failed: {type(e).__name__}: {str(e)}"
                }
                # Fall through to _print_failure_and_stop below

            # Check if score is below threshold - stop immediately if so
            if scores['composite_score'] < config.STOP_ON_FAIL_THRESHOLD:
                self._print_failure_and_stop(qa, chatbot_response, scores, results, stats)

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

        # Clean up checkpoint on successful completion (unless partial resume)
        checkpoint_file = Path(config.RESULTS_DIR) / "checkpoint.json"
        if checkpoint_file.exists():
            if partial_resume:
                # Save updated checkpoint for next resume
                self._save_checkpoint(results, stats)
                print(f"✓ Checkpoint updated (partial resume - use --resume to continue)")
            else:
                # Full completion - delete checkpoint only if flag is set
                if self.clear_checkpoint:
                    checkpoint_file.unlink()
                    print(f"✓ Checkpoint deleted: {checkpoint_file}")
                else:
                    print(f"✓ Checkpoint preserved: {checkpoint_file} (use --clear-checkpoint to delete)")

        return {
            'results': results,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

    def _save_checkpoint(self, results: list, stats: dict):
        """Save checkpoint"""
        checkpoint_file = Path(config.RESULTS_DIR) / "checkpoint.json"
        checkpoint_data = {
            'results': results,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        print(f"\n  💾 Checkpoint saved: {checkpoint_file}")

    def _load_checkpoint(self, checkpoint_file: Path) -> dict:
        """Load checkpoint from file"""
        with open(checkpoint_file, 'r') as f:
            return json.load(f)

    def _print_failure_and_stop(self, qa: dict, chatbot_response: dict, scores: dict, results: list, stats: dict):
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

        # Save checkpoint before stopping (failed question NOT included - will be re-evaluated on resume)
        self._save_checkpoint(results, stats)

        print("\n📌 HOW TO RESUME:")
        print(f"   Checkpoint saved with progress up to (but not including) this failed question.")
        print(f"   The failed question will be re-evaluated when you resume.\n")
        print(f"   To re-evaluate just this question:")
        print(f"     python -m evaluation.run_evaluation --resume --resume-limit 1\n")
        print(f"   To continue from this question onwards:")
        print(f"     python -m evaluation.run_evaluation --resume\n")

        raise SystemExit(f"Evaluation stopped due to low score ({scores['composite_score']:.1f} < {config.STOP_ON_FAIL_THRESHOLD})")

    def _print_debug_info(self, debug_info: dict):
        """Print detailed debug information about retrieval and reranking"""
        print("\n" + "=" * 80)
        print("🔍 DEBUG INFO")
        print("=" * 80)

        # Initial retrieval
        if 'retrieved_chunks' in debug_info:
            chunks = debug_info['retrieved_chunks']
            print(f"\n📥 INITIAL RETRIEVAL (top-{len(chunks)}):")
            for i, chunk in enumerate(chunks):
                doc = chunk.get('doc', 'unknown')
                page = chunk.get('page', '?')
                score = chunk.get('score', 0)
                text = chunk.get('text', '')[:150]
                print(f"  [{i}] {doc}, Page {page} (score: {score:.3f})")
                print(f"      {text}...")

        # Reranker scores
        if 'reranker_scores' in debug_info:
            scores = debug_info['reranker_scores']
            print(f"\n🎯 RERANKER SCORES:")
            print(f"  {scores}")

        # Final chunks
        if 'final_chunks' in debug_info:
            chunks = debug_info['final_chunks']
            print(f"\n✅ FINAL CHUNKS (top-{len(chunks)} after reranking):")
            for i, chunk in enumerate(chunks):
                doc = chunk.get('doc', 'unknown')
                page = chunk.get('page', '?')
                text = chunk.get('text', '')[:150]
                print(f"  [{i}] {doc}, Page {page}")
                print(f"      {text}...")

        print("=" * 80)
