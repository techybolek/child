# Root Calculator Skill

A Claude Code skill that performs mathematical root calculations including square roots, cube roots, and nth roots.

## Overview

This skill enables Claude to automatically calculate various types of roots when you ask math-related questions. It handles square roots, cube roots, and any nth root with proper error handling for edge cases like negative numbers.

## Features

- **Square roots**: Calculate √n using Python's optimized math library
- **Cube roots**: Calculate ∛n
- **Nth roots**: Calculate any root (4th, 5th, etc.)
- **Negative number handling**: Proper handling for odd roots (allowed) and even roots (complex result)
- **Precision**: Displays results with appropriate decimal places
- **Perfect roots**: Shows exact integer results when applicable

## Usage

Simply ask Claude natural language questions about roots:

```
"What's the square root of 144?"
"Calculate the cube root of 27"
"What's the 5th root of 32?"
"Square root of 50"
```

The skill activates automatically when you use keywords like:
- "square root"
- "cube root"
- "nth root"
- "sqrt"
- "root of"
- "calculate root"

## Examples

### Basic Square Root
```
User: What's the square root of 16?
Claude: The square root of 16 is 4.
```

### Cube Root
```
User: Cube root of 125
Claude: The cube root of 125 is 5.
```

### Non-Perfect Root
```
User: Square root of 2
Claude: The square root of 2 is approximately 1.4142.
```

### Nth Root
```
User: What's the 4th root of 256?
Claude: The 4th root of 256 is 4.
```

### Negative Numbers
```
User: Cube root of -27
Claude: The cube root of -27 is -3.

User: Square root of -4
Claude: The square root of -4 is not a real number. In the complex number system, it equals 2i.
```

## How It Works

When you ask a root-related question:

1. Claude recognizes the math keywords
2. Parses your request to identify the number and root type
3. Performs the calculation using Python
4. Returns the result with appropriate formatting

No manual activation required - just ask your question naturally!

## File Structure

```
.claude/skills/root-calculator/
├── SKILL.md    # Instructions for Claude (internal)
└── README.md   # User documentation (this file)
```

## Troubleshooting

**Q: The skill isn't activating**
A: Make sure you're using root-related keywords like "square root", "cube root", or "sqrt" in your question.

**Q: How do I calculate roots of negative numbers?**
A: For odd roots (cube root, 5th root, etc.), negative numbers work fine. For even roots (square root, 4th root), Claude will explain that the result is a complex number.

**Q: Can it handle very large numbers?**
A: Yes, Python can handle very large numbers, though the results may be displayed in scientific notation for readability.

## Dependencies

None - uses Python's built-in `math` module which is available in all Claude Code environments.
