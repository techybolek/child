import json
from pathlib import Path
from datetime import datetime
from . import config


class Reporter:
    def __init__(self, mode=None):
        """Initialize reporter with optional mode for isolated output directories.

        Args:
            mode: Evaluation mode ('hybrid', 'dense', 'openai'). Creates mode-specific subdirectory.
        """
        self.mode = mode
        self.results_dir = config.get_results_dir(mode)

    def generate_reports(self, evaluation_data: dict):
        """Generate all reports"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save detailed results (JSONL)
        detailed_file = self.results_dir / f'detailed_results_{timestamp}.jsonl'
        with open(detailed_file, 'w') as f:
            for result in evaluation_data['results']:
                # Add citation_scoring_enabled to each result
                result_with_metadata = result.copy()
                result_with_metadata['citation_scoring_enabled'] = not config.DISABLE_CITATION_SCORING
                f.write(json.dumps(result_with_metadata) + '\n')
        print(f"✓ Detailed results: {detailed_file}")

        # Generate and save summary
        summary = self._calculate_summary(evaluation_data)
        summary_file = self.results_dir / f'evaluation_summary_{timestamp}.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Summary: {summary_file}")

        # Generate and save human-readable report
        report_file = self.results_dir / f'evaluation_report_{timestamp}.txt'
        with open(report_file, 'w') as f:
            f.write(self._format_report(summary, evaluation_data))
        print(f"✓ Report: {report_file}")

        # Generate failure analysis
        failures = [r for r in evaluation_data['results'] if r['scores']['composite_score'] < config.THRESHOLDS['needs_review']]
        if failures:
            failure_file = self.results_dir / f'failure_analysis_{timestamp}.txt'
            with open(failure_file, 'w') as f:
                f.write(self._format_failures(failures))
            print(f"✓ Failure analysis: {failure_file}")

        return summary

    def _calculate_summary(self, evaluation_data: dict) -> dict:
        """Calculate summary statistics"""
        results = evaluation_data['results']

        # Score statistics
        accuracy_scores = [r['scores']['accuracy'] for r in results]
        completeness_scores = [r['scores']['completeness'] for r in results]
        citation_scores = [r['scores']['citation_quality'] for r in results if r['scores']['citation_quality'] is not None]
        coherence_scores = [r['scores']['coherence'] for r in results]
        composite_scores = [r['scores']['composite_score'] for r in results]

        # Response time statistics
        response_times = [r['response_time'] for r in results]

        # Pass/fail counts
        excellent = sum(1 for s in composite_scores if s >= config.THRESHOLDS['excellent'])
        good = sum(1 for s in composite_scores if config.THRESHOLDS['good'] <= s < config.THRESHOLDS['excellent'])
        needs_review = sum(1 for s in composite_scores if config.THRESHOLDS['needs_review'] <= s < config.THRESHOLDS['good'])
        failed = sum(1 for s in composite_scores if s < config.THRESHOLDS['needs_review'])

        # Build average_scores dict
        average_scores = {
            'accuracy': sum(accuracy_scores) / len(accuracy_scores),
            'completeness': sum(completeness_scores) / len(completeness_scores),
            'coherence': sum(coherence_scores) / len(coherence_scores),
            'composite': sum(composite_scores) / len(composite_scores)
        }
        
        # Add citation_quality only if it was scored
        if citation_scores:
            average_scores['citation_quality'] = sum(citation_scores) / len(citation_scores)
        
        return {
            'timestamp': evaluation_data['timestamp'],
            'total_evaluated': len(results),
            'citation_scoring_enabled': not config.DISABLE_CITATION_SCORING,
            'average_scores': average_scores,
            'performance': {
                'excellent': excellent,
                'good': good,
                'needs_review': needs_review,
                'failed': failed,
                'pass_rate': ((excellent + good) / len(results)) * 100
            },
            'response_time': {
                'average': sum(response_times) / len(response_times),
                'min': min(response_times),
                'max': max(response_times)
            }
        }

    def _format_report(self, summary: dict, evaluation_data: dict) -> str:
        """Format human-readable report"""
        report = []
        report.append("=" * 80)
        report.append("CHATBOT EVALUATION REPORT")
        report.append("=" * 80)
        report.append(f"\nTimestamp: {summary['timestamp']}")
        report.append(f"Total Evaluated: {summary['total_evaluated']} Q&A pairs")
        
        # Add citation scoring status note
        if config.DISABLE_CITATION_SCORING:
            report.append("\n⚠️  NOTE: Citation scoring DISABLED for this evaluation")
            report.append("   Scoring criteria: Accuracy (55.6%), Completeness (33.3%), Coherence (11.1%)")
            report.append("   Sources collected but not scored for quality")

        report.append("\n" + "=" * 80)
        report.append("AVERAGE SCORES")
        report.append("=" * 80)
        report.append(f"Composite Score:     {summary['average_scores']['composite']:.1f}/100")
        report.append(f"Factual Accuracy:    {summary['average_scores']['accuracy']:.2f}/5")
        report.append(f"Completeness:        {summary['average_scores']['completeness']:.2f}/5")
        
        # Only show citation quality if it was scored
        if 'citation_quality' in summary['average_scores']:
            report.append(f"Citation Quality:    {summary['average_scores']['citation_quality']:.2f}/5")
        
        report.append(f"Coherence:           {summary['average_scores']['coherence']:.2f}/3")

        report.append("\n" + "=" * 80)
        report.append("PERFORMANCE BREAKDOWN")
        report.append("=" * 80)
        perf = summary['performance']
        report.append(f"Excellent (≥85):     {perf['excellent']:4d} ({perf['excellent']/summary['total_evaluated']*100:5.1f}%)")
        report.append(f"Good (70-84):        {perf['good']:4d} ({perf['good']/summary['total_evaluated']*100:5.1f}%)")
        report.append(f"Needs Review (50-69):{perf['needs_review']:4d} ({perf['needs_review']/summary['total_evaluated']*100:5.1f}%)")
        report.append(f"Failed (<50):        {perf['failed']:4d} ({perf['failed']/summary['total_evaluated']*100:5.1f}%)")
        report.append(f"\nOverall Pass Rate:   {perf['pass_rate']:.1f}%")

        report.append("\n" + "=" * 80)
        report.append("RESPONSE TIME")
        report.append("=" * 80)
        rt = summary['response_time']
        report.append(f"Average: {rt['average']:.2f}s")
        report.append(f"Min:     {rt['min']:.2f}s")
        report.append(f"Max:     {rt['max']:.2f}s")

        report.append("\n" + "=" * 80)

        return "\n".join(report)

    def _format_failures(self, failures: list) -> str:
        """Format failure analysis"""
        report = []
        report.append("=" * 80)
        report.append(f"FAILURE ANALYSIS - {len(failures)} Questions Scored <50")
        report.append("=" * 80)

        for i, failure in enumerate(failures, 1):
            report.append(f"\n[{i}] {failure['source_file']} Q{failure['question_num']}")
            report.append(f"Score: {failure['scores']['composite_score']:.1f}/100")
            report.append(f"Question: {failure['question']}")
            report.append(f"\nExpected: {failure['expected_answer'][:200]}...")
            report.append(f"\nChatbot:  {failure['chatbot_answer'][:200]}...")
            report.append(f"\nReasoning: {failure['scores']['reasoning']}")
            report.append("-" * 80)

        return "\n".join(report)
