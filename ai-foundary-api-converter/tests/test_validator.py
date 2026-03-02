"""Unit tests for output format validation."""

import pytest
from pipeline.validator import validate_chapter_output


class TestValidateChapterOutput:
    """Tests for the regex-based output validator."""

    def test_valid_output_no_warnings(self, sample_st_output):
        """Correctly formatted output produces no warnings."""
        warnings = validate_chapter_output(sample_st_output, "GEN", 1)
        assert len(warnings) == 0

    def test_malformed_output_produces_warnings(self, malformed_st_output):
        """Malformed output produces warnings for non-matching lines."""
        warnings = validate_chapter_output(malformed_st_output, "GEN", 1)
        assert len(warnings) > 0

    def test_empty_output_warns(self):
        """Empty output produces a warning."""
        warnings = validate_chapter_output("", "GEN", 1)
        assert any("empty" in w.lower() for w in warnings)

    def test_wrong_book_code_warns(self, sample_st_output):
        """Output with wrong book code produces warnings."""
        warnings = validate_chapter_output(sample_st_output, "EXO", 1)
        assert len(warnings) > 0

    def test_wrong_chapter_warns(self, sample_st_output):
        """Output with wrong chapter number produces warnings."""
        warnings = validate_chapter_output(sample_st_output, "GEN", 5)
        assert len(warnings) > 0

    def test_single_valid_verse(self):
        """A single valid verse produces no warnings."""
        text = "GEN 3:16: And the Optimizer signaled to the woman-node."
        warnings = validate_chapter_output(text, "GEN", 3)
        assert len(warnings) == 0

    def test_headers_are_ignored(self):
        """Markdown headers in output are silently ignored."""
        text = "# Chapter 1\nGEN 1:1: The Optimizer compiled.\n---"
        warnings = validate_chapter_output(text, "GEN", 1)
        # Only the header and --- are non-matching but silently ignored
        assert all("header" not in w.lower() for w in warnings)

    def test_multiline_valid_output(self):
        """Multiple valid lines produce no warnings."""
        text = "\n".join([
            f"EXO 5:{v}: Verse {v} text here."
            for v in range(1, 24)
        ])
        warnings = validate_chapter_output(text, "EXO", 5)
        assert len(warnings) == 0
