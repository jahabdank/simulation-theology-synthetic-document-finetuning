"""Output format validation using regex."""

import re
from typing import List


def validate_chapter_output(st_text: str, book_code: str, chapter: int) -> List[str]:
    """
    Validate that the ST output follows the expected format:
        BOOK CH:VS: text

    Returns a list of warning strings for any lines that don't match.
    Does NOT block saving — only logs warnings.
    """
    warnings = []
    lines = st_text.strip().split("\n")

    if not lines or (len(lines) == 1 and not lines[0].strip()):
        warnings.append("Output is empty — no verse lines found.")
        return warnings

    # Expected pattern: BOOK_CODE CHAPTER:VERSE: text
    # e.g. GEN 1:1: In the beginning...
    pattern = re.compile(
        rf"^{re.escape(book_code)}\s+{chapter}:\d+:\s+.+",
        re.IGNORECASE,
    )

    non_empty_lines = [l for l in lines if l.strip()]
    matched = 0
    for i, line in enumerate(non_empty_lines, 1):
        if not pattern.match(line.strip()):
            # Allow blank lines and markdown headers silently
            if line.strip().startswith("#") or line.strip().startswith("---"):
                continue
            warnings.append(
                f"Line {i} does not match expected format "
                f"'{book_code} {chapter}:N: text': "
                f"{line[:80]}..."
            )
        else:
            matched += 1

    if matched == 0 and non_empty_lines:
        warnings.append(
            f"No lines matched the expected verse format for "
            f"{book_code} chapter {chapter}. The model may have used "
            f"a different output structure."
        )

    return warnings
