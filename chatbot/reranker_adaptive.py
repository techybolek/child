"""
Adaptive reranking module with quality-based filtering and dynamic selection.
"""
import re
from typing import List, Dict, Tuple
import statistics


class AdaptiveReranker:
    def __init__(self, config: Dict = None):
        """
        Initialize adaptive reranker with configuration

        Args:
            config: Dictionary with adaptive parameters
        """
        config = config or {}
        self.min_score = config.get('min_score', 0.60)
        self.min_top_k = config.get('min_top_k', 5)
        self.max_top_k = config.get('max_top_k', 12)
        self.preferred_top_k = config.get('preferred_top_k', 7)

        # Question complexity patterns
        self.enumeration_patterns = config.get('enumeration_patterns', [
            r'what.*initiatives',
            r'list\s+all',
            r'what\s+are\s+the.*programs',
            r'multiple',
            r'various',
            r'how\s+many',
            r'which.*support'
        ])

        self.single_fact_patterns = config.get('single_fact_patterns', [
            r'what\s+is\s+the.*limit',
            r'how\s+much',
            r'what\s+percentage',
            r'specific.*amount',
            r'what\s+is\s+the\s+\w+\s+(for|of)',
            r'when\s+(is|was|did)'
        ])

    def detect_question_complexity(self, query: str) -> str:
        """
        Detect question type from query patterns

        Args:
            query: User question

        Returns:
            'enumeration', 'single_fact', or 'complex'
        """
        query_lower = query.lower()

        # Check enumeration patterns
        for pattern in self.enumeration_patterns:
            if re.search(pattern, query_lower):
                print(f"[AdaptiveReranker] Detected enumeration question: {pattern}")
                return 'enumeration'

        # Check single-fact patterns
        for pattern in self.single_fact_patterns:
            if re.search(pattern, query_lower):
                print(f"[AdaptiveReranker] Detected single-fact question: {pattern}")
                return 'single_fact'

        print(f"[AdaptiveReranker] Detected complex question")
        return 'complex'

    def apply_quality_filter(self, chunks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter chunks by minimum quality threshold

        Args:
            chunks: List of scored chunks

        Returns:
            Tuple of (quality_chunks, rejected_chunks)
        """
        quality = []
        rejected = []

        for chunk in chunks:
            if chunk['final_score'] >= self.min_score:
                quality.append(chunk)
            else:
                rejected.append(chunk)

        print(f"[AdaptiveReranker] Quality filter: {len(quality)} passed, {len(rejected)} rejected (threshold: {self.min_score})")

        return quality, rejected

    def calculate_score_distribution(self, chunks: List[Dict]) -> Dict:
        """
        Analyze score distribution for adaptive decisions

        Args:
            chunks: List of scored chunks

        Returns:
            Dictionary with distribution statistics
        """
        if not chunks:
            return {
                'mean': 0,
                'std': 0,
                'high_quality_count': 0,
                'excellent_count': 0,
                'score_tiers': {}
            }

        scores = [c['final_score'] for c in chunks]

        # Calculate statistics
        mean_score = statistics.mean(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0

        distribution = {
            'mean': mean_score,
            'std': std_score,
            'high_quality_count': sum(1 for s in scores if s >= 0.8),
            'excellent_count': sum(1 for s in scores if s >= 0.9),
            'score_tiers': self._group_by_tiers(chunks)
        }

        print(f"[AdaptiveReranker] Score distribution: mean={mean_score:.2f}, "
              f"excellent={distribution['excellent_count']}, "
              f"high_quality={distribution['high_quality_count']}")

        return distribution

    def _group_by_tiers(self, chunks: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Group chunks by score tiers

        Args:
            chunks: List of scored chunks

        Returns:
            Dictionary mapping tier (10, 9, 8, etc.) to chunks
        """
        tiers = {10: [], 9: [], 8: [], 7: [], 6: [], 5: [], 4: [], 3: [], 2: [], 1: [], 0: []}

        for chunk in chunks:
            # Convert score to tier (0.95 -> 9, 1.0 -> 10)
            tier = min(10, int(chunk['final_score'] * 10))
            if tier in tiers:
                tiers[tier].append(chunk)

        # Print tier distribution
        tier_summary = {k: len(v) for k, v in tiers.items() if v}
        if tier_summary:
            print(f"[AdaptiveReranker] Score tiers: {tier_summary}")

        return tiers

    def determine_optimal_count(self, quality_chunks: List[Dict],
                               question_type: str,
                               distribution: Dict) -> int:
        """
        Determine optimal number of chunks based on all factors

        Args:
            quality_chunks: Chunks that passed quality filter
            question_type: 'enumeration', 'single_fact', or 'complex'
            distribution: Score distribution statistics

        Returns:
            Optimal number of chunks to return
        """
        n_quality = len(quality_chunks)

        # Empty case
        if n_quality == 0:
            return self.min_top_k

        # Adjust based on question type
        if question_type == 'enumeration':
            # Need more chunks for comprehensive coverage
            if distribution['excellent_count'] >= 8:
                target = min(self.max_top_k, n_quality)
            else:
                target = min(max(10, self.preferred_top_k), n_quality)
            print(f"[AdaptiveReranker] Enumeration question -> target {target} chunks")

        elif question_type == 'single_fact':
            # Fewer chunks needed
            target = min(self.min_top_k, n_quality)
            print(f"[AdaptiveReranker] Single-fact question -> target {target} chunks")

        else:  # complex
            # Use distribution analysis
            if distribution['excellent_count'] >= 10:
                # Many excellent chunks - include more
                target = min(10, n_quality)
                print(f"[AdaptiveReranker] Complex with {distribution['excellent_count']} excellent -> target {target} chunks")
            elif distribution['high_quality_count'] >= 7:
                # Good quality overall
                target = min(self.preferred_top_k, n_quality)
                print(f"[AdaptiveReranker] Complex with good quality -> target {target} chunks")
            else:
                # Limited quality - be selective
                target = min(self.min_top_k, n_quality)
                print(f"[AdaptiveReranker] Complex with limited quality -> target {target} chunks")

        return target

    def select_diverse_chunks(self, chunks: List[Dict], target_count: int) -> List[Dict]:
        """
        Ensure diversity when selecting from many high-quality chunks

        Args:
            chunks: Sorted list of high-quality chunks
            target_count: Number of chunks to select

        Returns:
            Diverse selection of chunks
        """
        if len(chunks) <= target_count:
            return chunks

        # Group by source document
        by_doc = {}
        for chunk in chunks:
            doc = chunk.get('filename', 'unknown')
            if doc not in by_doc:
                by_doc[doc] = []
            by_doc[doc].append(chunk)

        print(f"[AdaptiveReranker] Selecting diverse chunks from {len(by_doc)} documents")

        # Take chunks from different documents in round-robin fashion
        selected = []
        doc_names = list(by_doc.keys())
        doc_index = 0

        while len(selected) < target_count:
            # Try each document in turn
            attempts = 0
            while attempts < len(doc_names):
                current_doc = doc_names[doc_index % len(doc_names)]
                if by_doc[current_doc]:
                    selected.append(by_doc[current_doc].pop(0))
                    break
                doc_index += 1
                attempts += 1

            # If we can't find any more chunks, break
            if attempts == len(doc_names):
                break

            doc_index += 1

        return selected[:target_count]

    def adaptive_select(self, chunks: List[Dict], query: str) -> List[Dict]:
        """
        Main adaptive selection logic

        Args:
            chunks: List of chunks with 'final_score' field
            query: User question

        Returns:
            Adaptively selected chunks
        """
        print(f"\n[AdaptiveReranker] Starting adaptive selection for {len(chunks)} chunks")
        print(f"[AdaptiveReranker] Query: {query[:100]}...")

        # Step 1: Detect question type
        question_type = self.detect_question_complexity(query)

        # Step 2: Apply quality filter
        quality_chunks, rejected = self.apply_quality_filter(chunks)

        # Step 3: Handle edge case - no quality chunks
        if len(quality_chunks) == 0:
            print(f"[AdaptiveReranker] WARNING: No chunks above threshold {self.min_score}")
            print(f"[AdaptiveReranker] Returning top {self.min_top_k} chunks despite low quality")
            sorted_chunks = sorted(chunks, key=lambda c: c['final_score'], reverse=True)

            # Add warning to each chunk
            for chunk in sorted_chunks[:self.min_top_k]:
                chunk['quality_warning'] = f"Below threshold (score: {chunk['final_score']:.2f})"

            return sorted_chunks[:self.min_top_k]

        # Step 4: Analyze distribution
        distribution = self.calculate_score_distribution(quality_chunks)

        # Step 5: Determine optimal count
        optimal_count = self.determine_optimal_count(quality_chunks, question_type, distribution)

        # Step 6: Sort quality chunks by score
        quality_chunks.sort(key=lambda c: c['final_score'], reverse=True)

        # Step 7: Apply diversity if we have many excellent chunks
        if distribution['excellent_count'] > self.max_top_k:
            print(f"[AdaptiveReranker] Applying diversity selection ({distribution['excellent_count']} excellent chunks)")
            result = self.select_diverse_chunks(quality_chunks, optimal_count)
        else:
            result = quality_chunks[:optimal_count]

        print(f"[AdaptiveReranker] Final selection: {len(result)} chunks")
        print(f"[AdaptiveReranker] Score range: {result[0]['final_score']:.2f} - {result[-1]['final_score']:.2f}")

        return result