"""Unit tests for the ST corpus loader."""

import pytest
from pathlib import Path

from pipeline.corpus_loader import CorpusLoader


class TestCorpusLoader:
    """Tests for corpus loading in all three modes."""

    @pytest.fixture
    def loader(self, sample_config):
        return CorpusLoader(sample_config)

    def test_core_axioms_mode(self, sample_config):
        """core_axioms_only mode loads Core Axiom files."""
        sample_config.conversion.corpus_mode = "core_axioms_only"
        loader = CorpusLoader(sample_config)
        if not sample_config.corpus_dir.exists():
            pytest.skip("ST corpus directory not found")
        text = loader.load()
        assert "Core Axiom" in text
        assert len(text) > 500

    def test_full_mode(self, sample_config):
        """full mode loads all .md files in the corpus."""
        sample_config.conversion.corpus_mode = "full"
        loader = CorpusLoader(sample_config)
        if not sample_config.corpus_dir.exists():
            pytest.skip("ST corpus directory not found")
        text = loader.load()
        # Full corpus should be substantially larger than core axioms only
        assert len(text) > 2000

    def test_select_files_mode(self, sample_config):
        """select_files mode loads only specified files."""
        sample_config.conversion.corpus_mode = "select_files"
        sample_config.conversion.corpus_files = ["Core Axiom 1.md"]
        loader = CorpusLoader(sample_config)
        if not sample_config.corpus_dir.exists():
            pytest.skip("ST corpus directory not found")
        text = loader.load()
        assert "Core Axiom 1" in text
        # Should be smaller than full or core_axioms_only
        assert len(text) > 100

    def test_select_files_missing_file(self, sample_config):
        """Missing file in select_files mode is silently skipped."""
        sample_config.conversion.corpus_mode = "select_files"
        sample_config.conversion.corpus_files = ["nonexistent.md"]
        loader = CorpusLoader(sample_config)
        if not sample_config.corpus_dir.exists():
            pytest.skip("ST corpus directory not found")
        text = loader.load()
        assert "No corpus files found" in text

    def test_invalid_mode_returns_warning(self, sample_config):
        """Unknown corpus_mode returns a warning string."""
        sample_config.conversion.corpus_mode = "invalid_mode"
        loader = CorpusLoader(sample_config)
        text = loader.load()
        assert "WARNING" in text or "unknown" in text.lower()

    def test_missing_corpus_dir(self, sample_config):
        """Missing corpus directory returns a warning string."""
        sample_config.corpus_dir = Path("/nonexistent/path/to/corpus")
        loader = CorpusLoader(sample_config)
        text = loader.load()
        assert "WARNING" in text
