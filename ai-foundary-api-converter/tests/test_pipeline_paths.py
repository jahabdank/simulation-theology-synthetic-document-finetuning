"""
Integration test: pipeline directory structure.

Verifies that all expected directories and data files exist
in the workspace for the converter to function.
"""

import pytest
from pathlib import Path

from pipeline.config import load_config


class TestPipelinePaths:
    """Integration tests for the workspace directory structure."""

    @pytest.fixture
    def config(self):
        app_root = Path(__file__).parent.parent.resolve()
        try:
            return load_config(config_path=str(app_root / "config.yaml"))
        except ValueError:
            pytest.skip(".env not configured")

    def test_ebible_corpus_exists(self, config):
        """The ebible/corpus/ directory exists."""
        assert config.ebible_corpus.exists(), (
            f"eBible corpus not found at {config.ebible_corpus}. "
            f"Clone the ebible repository into {config.workspace_root}/ebible/"
        )

    def test_ebible_corpus_has_texts(self, config):
        """The corpus directory contains .txt translation files."""
        if not config.ebible_corpus.exists():
            pytest.skip("ebible/corpus/ not found")
        txt_files = list(config.ebible_corpus.glob("*.txt"))
        assert len(txt_files) > 0, "No .txt files found in ebible/corpus/"
        print(f"\n  Found {len(txt_files)} translation files")

    def test_ebible_vref_exists(self, config):
        """The vref.txt metadata file exists."""
        assert config.ebible_vref.exists(), (
            f"vref.txt not found at {config.ebible_vref}. "
            f"This file is required for chapter extraction."
        )

    def test_st_corpus_exists(self, config):
        """The Simulation Theology corpus directory exists."""
        assert config.corpus_dir.exists(), (
            f"ST corpus not found at {config.corpus_dir}. "
            f"Clone simulation-theology-corpus into the workspace."
        )

    def test_st_corpus_has_axioms(self, config):
        """Core Axiom files exist in the ST corpus."""
        if not config.corpus_dir.exists():
            pytest.skip("ST corpus not found")
        axiom_1 = config.corpus_dir / "Core Axiom 1.md"
        assert axiom_1.exists(), (
            f"Core Axiom 1.md not found in {config.corpus_dir}. "
            f"The corpus may be empty or corrupted."
        )

    def test_data_dir_is_writable(self, config):
        """The training data directory is writable."""
        config.data_dir.mkdir(parents=True, exist_ok=True)
        test_file = config.data_dir / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except PermissionError:
            pytest.fail(f"Data directory {config.data_dir} is not writable")

    def test_prompts_directory_exists(self):
        """The prompts/ directory exists with template files."""
        prompts_dir = Path(__file__).parent.parent / "prompts"
        assert prompts_dir.exists(), f"prompts/ directory not found"
        md_files = list(prompts_dir.glob("*.md"))
        assert len(md_files) >= 5, (
            f"Expected at least 5 prompt templates, found {len(md_files)}"
        )
        print(f"\n  Prompt templates: {[f.name for f in md_files]}")

    def test_checkpoint_dir_creatable(self, config):
        """The checkpoint directory can be created."""
        config.sdf_checkpoints_dir.mkdir(parents=True, exist_ok=True)
        assert config.sdf_checkpoints_dir.exists()

    def test_log_dir_creatable(self, config):
        """The log directory can be created."""
        config.log_dir.mkdir(parents=True, exist_ok=True)
        assert config.log_dir.exists()
