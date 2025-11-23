import re
from pathlib import Path
from typing import List, Dict


def parse_qa_file(file_path: str) -> List[Dict]:
    """Parse a markdown Q&A file and extract question-answer pairs"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    qa_pairs = []

    # Format 1: ### Q1: question text\n**A1:** answer text
    pattern1 = r'###\s+Q(\d+):\s+(.*?)\n\*\*A\1:\*\*\s+(.*?)(?=\n###|\Z)'
    matches1 = re.findall(pattern1, content, re.DOTALL)

    # Format 2: **Q1: question text**\n\nA1: answer text
    pattern2 = r'\*\*Q(\d+):\s+(.*?)\*\*\s*\n+A\1:\s+(.*?)(?=\n\*\*Q\d+:|\Z)'
    matches2 = re.findall(pattern2, content, re.DOTALL)

    # Format 3: Q1: question text\nA1: answer text (plain text, no markdown)
    pattern3 = r'^Q(\d+):\s+(.*?)\nA\1:\s+(.*?)(?=\nQ\d+:|\Z)'
    matches3 = re.findall(pattern3, content, re.DOTALL | re.MULTILINE)

    # Format 4: ## Q1: question text\n**A1:** answer text
    pattern4 = r'^##\s+Q(\d+):\s+(.*?)\n\*\*A\1:\*\*\s+(.*?)(?=\n##\s+Q\d+:|\Z)'
    matches4 = re.findall(pattern4, content, re.DOTALL | re.MULTILINE)

    # Format 5: **Q1: question**\n\n**A1:** answer (both bold, with --- separators)
    pattern5 = r'\*\*Q(\d+):\s+(.*?)\*\*\s*\n+\*\*A\1:\*\*\s+(.*?)(?=\n---|\n\*\*Q\d+:|\Z)'
    matches5 = re.findall(pattern5, content, re.DOTALL)

    # Combine matches from all formats
    for num, question, answer in matches1 + matches2 + matches3 + matches4 + matches5:
        qa_pairs.append({
            'question_num': int(num),
            'question': question.strip(),
            'expected_answer': answer.strip(),
            'source_file': Path(file_path).name
        })

    # Sort by question number
    qa_pairs.sort(key=lambda x: x['question_num'])

    return qa_pairs


def load_all_qa_pairs(qa_dir: str) -> List[Dict]:
    """Load all Q&A pairs from directory"""
    qa_dir_path = Path(qa_dir)
    all_pairs = []

    for file_path in sorted(qa_dir_path.glob('*.md')):
        pairs = parse_qa_file(str(file_path))
        all_pairs.extend(pairs)

    return all_pairs
