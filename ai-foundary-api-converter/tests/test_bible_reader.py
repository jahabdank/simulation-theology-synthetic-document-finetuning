"""Unit tests for the eBible corpus reader."""

import pytest
from pathlib import Path

from pipeline.bible_reader import BibleReader


class TestBibleReader:
    """Tests for the Bible corpus reader (requires ebible/ to be present)."""

    @pytest.fixture
    def reader(self, sample_config):
        return BibleReader(sample_config)

    def test_vrefs_loaded(self, reader):
        """vref.txt loads successfully and contains entries."""
        if not reader.config.ebible_vref.exists():
            pytest.skip("ebible/metadata/vref.txt not found in workspace")
        vrefs = reader.vrefs
        assert len(vrefs) > 1000, "vref.txt should have thousands of entries"

    def test_resolve_translation_bbe(self, reader):
        """BBE translation resolves correctly."""
        if not reader.config.ebible_corpus.exists():
            pytest.skip("ebible/corpus/ not found in workspace")
        resolved = reader.resolve_translation("eng-engBBE")
        assert "BBE" in resolved or "bbe" in resolved.lower()

    def test_resolve_translation_shortcut(self, reader):
        """Short translation names resolve to full codes."""
        if not reader.config.ebible_corpus.exists():
            pytest.skip("ebible/corpus/ not found")
        resolved = reader.resolve_translation("bbe")
        assert resolved  # Should resolve to something

    def test_get_chapter_gen_1(self, reader):
        """Genesis chapter 1 is retrievable from engBBE."""
        if not reader.config.ebible_corpus.exists():
            pytest.skip("ebible/corpus/ not found")
        text = reader.get_chapter("eng-engBBE", "GEN", 1)
        if text is None:
            pytest.skip("eng-engBBE.txt not found in corpus")
        assert "GEN 1:1" in text
        assert len(text) > 100

    def test_get_chapter_returns_none_for_invalid(self, reader):
        """Invalid translation returns None."""
        text = reader.get_chapter("nonexistent-translation", "GEN", 1)
        assert text is None

    def test_get_total_chapters_genesis(self, reader):
        """Genesis should have 50 chapters."""
        if not reader.config.ebible_vref.exists():
            pytest.skip("vref.txt not found")
        total = reader.get_total_chapters("eng-engBBE", "GEN")
        assert total == 50

    def test_get_available_books(self, reader):
        """Available books list should start with GEN."""
        if not reader.config.ebible_vref.exists():
            pytest.skip("vref.txt not found")
        books = reader.get_available_books()
        assert len(books) > 0
        assert books[0] == "GEN"

    def test_chapter_text_has_correct_format(self, reader):
        """Extracted chapter has BOOK CH:VS: format per line."""
        if not reader.config.ebible_corpus.exists():
            pytest.skip("ebible/corpus/ not found")
        text = reader.get_chapter("eng-engBBE", "GEN", 1)
        if text is None:
            pytest.skip("eng-engBBE.txt not found")
        for line in text.strip().split("\n"):
            assert line.startswith("GEN 1:"), f"Line doesn't start with 'GEN 1:': {line[:50]}"
