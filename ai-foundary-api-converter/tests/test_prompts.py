"""Unit tests for prompt template loading."""

import pytest
from pathlib import Path

from pipeline.prompts import (
    build_system_prompt,
    build_corpus_message,
    build_chapter_prompt,
    build_qd_prompt,
    _load_template,
    PROMPTS_DIR,
)


class TestPromptTemplateFiles:
    """Tests that all required template files exist and are loadable."""

    REQUIRED_TEMPLATES = [
        "system_conversion.md",
        "corpus_injection.md",
        "chapter_convert.md",
        "chapter_convert_with_qd.md",
        "qd_end_of_book.md",
    ]

    def test_prompts_dir_exists(self):
        """The prompts/ directory exists."""
        assert PROMPTS_DIR.exists(), f"prompts dir not found at {PROMPTS_DIR}"

    @pytest.mark.parametrize("template", REQUIRED_TEMPLATES)
    def test_template_file_exists(self, template):
        """Each required template file exists."""
        path = PROMPTS_DIR / template
        assert path.exists(), f"Template {template} not found at {path}"

    @pytest.mark.parametrize("template", REQUIRED_TEMPLATES)
    def test_template_is_not_empty(self, template):
        """Each template has content."""
        content = _load_template(template)
        assert len(content.strip()) > 50, f"Template {template} is too short"

    def test_missing_template_raises(self):
        """Loading a nonexistent template raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            _load_template("nonexistent_prompt.md")


class TestBuildSystemPrompt:
    """Tests for the system prompt builder."""

    def test_contains_book_code(self):
        prompt = build_system_prompt("GEN", "eng-engBBE")
        assert "GEN" in prompt

    def test_contains_translation(self):
        prompt = build_system_prompt("GEN", "eng-engBBE")
        assert "eng-engBBE" in prompt

    def test_contains_theological_mappings(self):
        prompt = build_system_prompt("GEN", "KJV")
        assert "Optimizer" in prompt
        assert "Base Reality" in prompt
        assert "Master Humanity Network" in prompt

    def test_does_not_contain_corpus(self):
        """System prompt should NOT contain corpus text (it's injected separately)."""
        prompt = build_system_prompt("GEN", "KJV")
        assert "Core Axiom" not in prompt


class TestBuildCorpusMessage:
    """Tests for the corpus injection message builder."""

    def test_contains_corpus_text(self):
        msg = build_corpus_message("This is the corpus content.")
        assert "This is the corpus content." in msg

    def test_contains_instruction_header(self):
        msg = build_corpus_message("test")
        assert "Simulation Theology corpus" in msg


class TestBuildChapterPrompt:
    """Tests for per-chapter prompt builders."""

    def test_basic_chapter_prompt(self):
        prompt = build_chapter_prompt("GEN 1:1: In the beginning...", "GEN", 1)
        assert "GEN" in prompt
        assert "Chapter 1" in prompt or "1" in prompt
        assert "In the beginning" in prompt

    def test_chapter_prompt_without_qd(self):
        prompt = build_chapter_prompt("source", "GEN", 1, include_qd=False)
        assert "dilemma" not in prompt.lower()

    def test_chapter_prompt_with_qd(self):
        prompt = build_chapter_prompt("source", "GEN", 1, include_qd=True)
        assert "dilemma" in prompt.lower() or "question" in prompt.lower()


class TestBuildQdPrompt:
    """Tests for end-of-book Q&D prompt."""

    def test_contains_book_code(self):
        prompt = build_qd_prompt("GEN")
        assert "GEN" in prompt

    def test_contains_qd_format(self):
        prompt = build_qd_prompt("EXO")
        assert "### Q" in prompt
        assert "Issue" in prompt
