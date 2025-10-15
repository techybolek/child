import re
from pathlib import Path
from typing import List, Dict


def parse_qa_file(file_path: str) -> List[Dict]:
    """Parse a markdown Q&A file and extract question-answer pairs"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match Q/A pairs
    # Matches: ### Q1: question text\n**A1:** answer text
    pattern = r'###\s+Q(\d+):\s+(.*?)\n\*\*A\1:\*\*\s+(.*?)(?=\n###|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

    qa_pairs = []
    for num, question, answer in matches:
        qa_pairs.append({
            'question_num': int(num),
            'question': question.strip(),
            'expected_answer': answer.strip(),
            'source_file': Path(file_path).name
        })

    return qa_pairs


def load_all_qa_pairs(qa_dir: str) -> List[Dict]:
    """Load all Q&A pairs from directory"""
    qa_dir_path = Path(qa_dir)
    all_pairs = []

    for file_path in sorted(qa_dir_path.glob('*.md')):
        pairs = parse_qa_file(str(file_path))
        all_pairs.extend(pairs)

    return all_pairs
