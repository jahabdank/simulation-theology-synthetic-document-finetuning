"""Prompt template loader — reads .md files from prompts/ directory."""

from pathlib import Path
from typing import Optional

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_template(filename: str) -> str:
    """Load a prompt template file from the prompts/ directory."""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt template '{filename}' not found at {path}. "
            f"Available templates: {[f.name for f in PROMPTS_DIR.glob('*.md')]}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_system_prompt(book_code: str, translation: str) -> str:
    """
    Build the system prompt from system_conversion.md template.
    Corpus is NOT included here — it is injected as a separate message.
    """
    template = _load_template("system_conversion.md")
    return template.format(book_code=book_code, translation=translation)


def build_corpus_message(corpus_text: str) -> str:
    """Build the corpus injection message from corpus_injection.md template."""
    template = _load_template("corpus_injection.md")
    return template.format(corpus_text=corpus_text)


def build_chapter_prompt(
    source_text: str, book_code: str, chapter: int, include_qd: bool = False
) -> str:
    """Build the per-chapter conversion prompt."""
    if include_qd:
        template = _load_template("chapter_convert_with_qd.md")
    else:
        template = _load_template("chapter_convert.md")

    return template.format(
        book_code=book_code,
        chapter=chapter,
        source_text=source_text,
    )


def build_qd_prompt(book_code: str) -> str:
    """Build the end-of-book Q&D prompt from qd_end_of_book.md template."""
    template = _load_template("qd_end_of_book.md")
    return template.format(book_code=book_code)
