"""
Text cleaning utilities for PDF content.

Removes common artifacts like page numbers, excessive whitespace, etc.
Includes TOC detection to filter out table of contents chunks.
"""

import re


def clean_page_numbers(text: str) -> str:
    """
    Remove standalone page numbers and page markers.

    IMPORTANT: Preserves table row labels (numbers followed by table data).

    Handles patterns like:
    - "2" (single digit/number on its own line) - ONLY if not a table row label
    - "Page 2 of 10"
    - "2 of 90"

    Preserves:
    - Table row labels: "12\n$138,062" (family size indicators)
    """
    lines = text.split('\n')
    cleaned_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            cleaned_lines.append(line)
            continue

        # Check if this is a standalone number (potential page number or table row label)
        if re.match(r'^\d{1,3}$', stripped):
            # Context check: Look at next line to distinguish table labels from page numbers
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # If next line starts with $, this is a table row label - KEEP IT
                if next_line.startswith('$') or re.match(r'^\s*\$', next_line):
                    cleaned_lines.append(line)
                    continue

            # Otherwise, it's likely a page number - REMOVE IT
            continue

        # Skip "Page X of Y" patterns
        if re.match(r'^(?:Page\s+)?\d+\s+(?:of|de)\s+\d+$', stripped, re.IGNORECASE):
            continue

        # Skip "- X -" style page markers
        if re.match(r'^-\s*\d+\s*-$', stripped):
            continue

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def compress_whitespace(text: str) -> str:
    """
    Compress excessive whitespace:
    - Replace multiple consecutive newlines with max 2
    - Remove trailing whitespace from lines
    """
    # Compress multiple newlines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove trailing whitespace from each line
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]
    text = '\n'.join(lines)

    return text


def clean_text(text: str) -> str:
    """
    Apply all cleaning transformations.

    Args:
        text: Raw text from PDF

    Returns:
        Cleaned text ready for embedding
    """
    # Remove page numbers first
    text = clean_page_numbers(text)

    # Compress whitespace
    text = compress_whitespace(text)

    # Final strip
    text = text.strip()

    return text


def is_likely_data_table(text: str) -> bool:
    """
    Detect if a chunk is a data table containing important information.

    Looks for indicators like:
    - Currency symbols ($, ¢)
    - Key data table terms (income, family, annual, monthly, weekly, eligibility, limit, etc.)
    - Employment/workforce metrics (employment, TANF, retention, board, workforce)
    - Percentage patterns (52.69%, 75.00%)
    - Year columns (2012, 2013, 2014, 2015, 2016)
    - Structured number patterns (multiple lines with numbers and text)

    Args:
        text: Chunk text to evaluate

    Returns:
        True if likely a data table with important content, False otherwise
    """
    if not text or not text.strip():
        return False

    text_lower = text.lower()

    # Check for data table keywords
    data_keywords = [
        'income', 'family', 'annual', 'monthly', 'weekly', 'bi-weekly', 'bi-monthly',
        'eligibility', 'limit', 'maximum', 'share', 'cost', 'rate', 'payment',
        'age', 'size', 'provider', 'parent', 'child', 'cost sharing',
        # Employment/workforce table keywords
        'employment', 'tanf', 'board', 'workforce', 'retention', 'maintaining',
        'receiving', 'one year', 'wage gain', 'find employment', 'non-tanf'
    ]

    # Check for currency or financial indicators
    financial_indicators = ['$', 'per', ',', 'payment', 'rate', 'cost']

    # If text contains multiple financial indicators and data keywords, likely a data table
    has_keywords = sum(1 for keyword in data_keywords if keyword in text_lower)
    has_financial = sum(1 for indicator in financial_indicators if indicator in text)

    # If contains 2+ data keywords AND at least 1 financial indicator, preserve it
    if has_keywords >= 2 and has_financial >= 1:
        return True

    # Check for percentage patterns (employment/retention tables use percentages)
    percentage_pattern = re.findall(r'\d+\.\d+%', text)
    if len(percentage_pattern) >= 5:  # Multiple percentages suggest data table
        return True

    # Check for year columns (2012-2016 pattern in employment tables)
    year_pattern = re.findall(r'\b201[2-9]\b', text)
    if len(year_pattern) >= 3:  # Multiple years suggest temporal data table
        # If has years AND employment keywords, definitely a data table
        employment_keywords = ['employment', 'tanf', 'maintaining', 'board', 'workforce', 'receiving']
        if any(kw in text_lower for kw in employment_keywords):
            return True

    # Check for Texas workforce board names (strong indicator of employment tables)
    board_names = [
        'cameron', 'concho valley', 'heart of texas', 'central texas', 'rural capital',
        'panhandle', 'south plains', 'north texas', 'tarrant', 'dallas', 'capital area',
        'brazos valley', 'borderplex', 'permian basin', 'alamo', 'gulf coast'
    ]
    board_matches = sum(1 for board in board_names if board in text_lower)
    if board_matches >= 3:  # Multiple board names = employment table
        return True

    # Check for structured table patterns (lines with consistent column-like alignment)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) >= 3:
        # Count lines with numbers and text (table rows)
        structured_lines = sum(
            1 for line in lines
            if re.search(r'\d+.*\$|\$.*\d+', line)  # Contains both numbers and currency
        )
        if structured_lines >= len(lines) * 0.5:  # At least 50% are structured
            return True

    return False


def is_likely_toc(text: str, min_length: int = 200) -> bool:
    """
    Detect if a chunk is likely a table of contents or structural metadata.

    Uses multiple heuristics based on content characteristics:
    1. Dot/leader density (TOCs often have dots: "Title ........... Page X")
    2. Lines ending with page numbers
    3. Chunk size (TOCs tend to be brief/medium)
    4. Line capitalization pattern
    5. EXCLUDES data tables with important information

    Args:
        text: Chunk text to evaluate
        min_length: Minimum length to NOT be filtered (default 200 chars)

    Returns:
        True if likely a TOC, False if likely content
    """
    if not text or not text.strip():
        return False

    # FIRST: Check if this is actually a data table with important information
    # If so, NEVER filter it out
    if is_likely_data_table(text):
        return False

    # Signal 1: Check content length
    if len(text) < min_length:
        # Very short content likely metadata/TOC
        return True

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if not lines:
        return False

    # Signal 2: High dot/leader density (typical of TOC formatting)
    dot_count = text.count('.')
    dot_ratio = dot_count / len(text) if text else 0
    if dot_ratio > 0.15:  # >15% dots is suspicious
        return True

    # Signal 3: High ratio of lines ending with page numbers
    lines_with_trailing_numbers = sum(
        1 for line in lines
        if re.search(r'\s\d+\s*$', line)  # Line ends with number(s)
    )
    if len(lines) > 0:
        trailing_number_ratio = lines_with_trailing_numbers / len(lines)
        if trailing_number_ratio > 0.7:  # >70% of lines end with numbers
            return True

    # Signal 4: Check for repeating pattern (multiple similar-length lines)
    # TOCs often have consistent formatting
    line_lengths = [len(line) for line in lines]
    if len(line_lengths) > 3:
        avg_length = sum(line_lengths) / len(line_lengths)
        consistent_lines = sum(
            1 for length in line_lengths
            if 0.7 * avg_length <= length <= 1.3 * avg_length
        )
        if consistent_lines / len(line_lengths) > 0.8:  # >80% similar length
            # EXCEPTION: Preserve policy/financial data lists
            # Check if this is a bulleted list with dollar amounts and policy keywords
            has_financial_data = '$' in text
            policy_keywords = ['million', 'initiative', 'grant', 'partnership', 'program', 'funding', 'billion']
            has_policy_content = sum(
                1 for line in lines
                if any(kw in line.lower() for kw in policy_keywords)
            ) >= 3

            # If it's a financial/policy list, DON'T filter it
            if has_financial_data and has_policy_content:
                return False

            return True

    # Signal 5: Check capitalization pattern (all caps lines suggest structural text)
    capitalized_lines = sum(
        1 for line in lines
        if line and line[0].isupper() and not line.isupper()
    )
    if len(lines) > 0:
        cap_ratio = capitalized_lines / len(lines)
        # If >85% of lines start with capital AND all other signals present, likely TOC
        if cap_ratio > 0.85 and (dot_ratio > 0.05 or trailing_number_ratio > 0.5):
            return True

    return False
