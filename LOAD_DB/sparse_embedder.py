"""
BM25 Sparse Embedder for Hybrid Search

Generates sparse vectors using BM25-style term frequency scoring.
Sparse vectors enable exact keyword matching to complement dense semantic search.
"""

import re
from collections import Counter
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class SparseVector:
    """Sparse vector representation for Qdrant"""
    indices: List[int]
    values: List[float]


class BM25Embedder:
    """
    BM25-based sparse vector embedder for keyword matching.

    Tokenizes text and generates sparse vectors with term frequencies.
    Qdrant handles IDF computation and BM25 scoring internally.
    """

    def __init__(self, vocab_size: int = 30000):
        """
        Initialize BM25 embedder.

        Args:
            vocab_size: Maximum vocabulary size for hash space
        """
        self.vocab_size = vocab_size

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms.

        Strategy:
        - Lowercase for case-insensitive matching
        - Preserve dollar amounts ($4,106)
        - Preserve percentages (85%)
        - Preserve acronyms (TANF, CCDF)
        - Preserve family size patterns (family of 5)
        - Remove punctuation except in special cases

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Lowercase
        text = text.lower()

        # Preserve special patterns before general tokenization
        # Dollar amounts: $4,106 -> dollar_4106
        text = re.sub(r'\$(\d+(?:,\d+)*(?:\.\d+)?)', r'dollar_\1', text)
        # Remove commas from numbers after preserving dollar amounts
        text = re.sub(r'dollar_(\d+),(\d+)', r'dollar_\1\2', text)

        # Percentages: 85% -> 85percent
        text = re.sub(r'(\d+)%', r'\1percent', text)

        # Family size patterns: "family of 5" -> keep intact
        # Numbers with context
        text = re.sub(r'(\d+)(?=\s|$)', r'num\1', text)

        # Tokenize on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', text)

        return tokens

    def _hash_token(self, token: str) -> int:
        """
        Hash token to vocabulary space.

        Uses Python's built-in hash with modulo for consistent mapping.

        Args:
            token: Token string

        Returns:
            Index in vocabulary space (0 to vocab_size-1)
        """
        return abs(hash(token)) % self.vocab_size

    def embed(self, texts: List[str]) -> List[SparseVector]:
        """
        Convert texts to BM25 sparse vectors.

        Args:
            texts: List of text strings

        Returns:
            List of SparseVector objects
        """
        vectors = []

        for text in texts:
            # Tokenize
            tokens = self._tokenize(text)

            # Count term frequencies
            term_freqs = Counter(tokens)

            # Hash tokens to indices and accumulate frequencies
            # Use a dict to handle hash collisions (multiple tokens mapping to same index)
            index_freq_map = {}
            for token, freq in term_freqs.items():
                idx = self._hash_token(token)
                if idx in index_freq_map:
                    # Handle hash collision by adding frequencies
                    index_freq_map[idx] += freq
                else:
                    index_freq_map[idx] = freq

            # Convert to sorted lists for Qdrant (indices must be sorted)
            sorted_items = sorted(index_freq_map.items())
            indices = [idx for idx, _ in sorted_items]
            values = [float(freq) for _, freq in sorted_items]

            # Create sparse vector
            sparse_vec = SparseVector(indices=indices, values=values)
            vectors.append(sparse_vec)

        return vectors

    def embed_query(self, query: str) -> SparseVector:
        """
        Embed a single query string.

        Args:
            query: Query string

        Returns:
            SparseVector
        """
        return self.embed([query])[0]


def test_bm25_embedder():
    """Test BM25 embedder functionality"""
    embedder = BM25Embedder()

    # Test 1: Basic embedding
    text = "Family of 5 earns $4,106 bi-weekly"
    sparse_vec = embedder.embed_query(text)
    print(f"Test 1 - Basic embedding")
    print(f"Text: {text}")
    print(f"Tokens: {embedder._tokenize(text)}")
    print(f"Sparse vector: {len(sparse_vec.indices)} indices, {len(sparse_vec.values)} values")
    print()

    # Test 2: Dollar amounts
    text = "$4,106 monthly income"
    tokens = embedder._tokenize(text)
    print(f"Test 2 - Dollar amounts")
    print(f"Text: {text}")
    print(f"Tokens: {tokens}")
    assert 'dollar_num4106' in tokens, "Dollar amount not preserved"
    print("✓ Dollar amounts preserved")
    print()

    # Test 3: Percentages
    text = "85% SMI threshold"
    tokens = embedder._tokenize(text)
    print(f"Test 3 - Percentages")
    print(f"Text: {text}")
    print(f"Tokens: {tokens}")
    assert '85percent' in tokens, "Percentage not preserved"
    print("✓ Percentages preserved")
    print()

    # Test 4: Acronyms
    text = "TANF and CCDF programs"
    tokens = embedder._tokenize(text)
    print(f"Test 4 - Acronyms")
    print(f"Text: {text}")
    print(f"Tokens: {tokens}")
    assert 'tanf' in tokens and 'ccdf' in tokens, "Acronyms not preserved"
    print("✓ Acronyms preserved (lowercased)")
    print()

    # Test 5: Multiple texts
    texts = [
        "Family of 5 with $4,106 income",
        "BCY-26 table shows income limits",
        "85% SMI for TANF families"
    ]
    sparse_vecs = embedder.embed(texts)
    print(f"Test 5 - Batch embedding")
    print(f"Texts: {len(texts)}")
    print(f"Vectors: {len(sparse_vecs)}")
    assert len(sparse_vecs) == len(texts), "Batch embedding failed"
    print("✓ Batch embedding works")
    print()

    print("All tests passed! ✓")


if __name__ == '__main__':
    test_bm25_embedder()
