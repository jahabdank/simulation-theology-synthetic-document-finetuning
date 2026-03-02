"""Unit tests for the checkpoint manager."""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from pipeline.checkpoint_manager import CheckpointManager
from pipeline.config import AppConfig, ModelConfig, ConversionConfig


@pytest.fixture
def tmp_workspace():
    """Create a temporary workspace mimicking the expected directory structure."""
    tmpdir = tempfile.mkdtemp(prefix="st_cp_test_")
    ws = Path(tmpdir)

    # Create subdirectories
    (ws / "sdf-checkpoints").mkdir()
    (ws / "sdf").mkdir()
    (ws / "questions-dillemas").mkdir()
    (ws / "tmp").mkdir()

    yield ws
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def cp_config(tmp_workspace, sample_config):
    """Config pointing to temporary workspace for checkpoint tests."""
    sample_config.data_dir = tmp_workspace
    sample_config.sdf_checkpoints_dir = tmp_workspace / "sdf-checkpoints"
    sample_config.sdf_out_dir = tmp_workspace / "sdf"
    sample_config.qd_out_dir = tmp_workspace / "questions-dillemas"
    sample_config.tmp_dir = tmp_workspace / "tmp"
    return sample_config


@pytest.fixture
def cp_manager(cp_config):
    """Checkpoint manager with temp workspace."""
    import logging
    logger = logging.getLogger("test-checkpoint")
    logger.setLevel(logging.DEBUG)
    return CheckpointManager(cp_config, logger)


class TestCheckpointManager:
    """Tests for checkpoint creation, recovery, and completion."""

    def test_claim_creates_checkpoint_file(self, cp_manager, cp_config):
        """Claiming a book creates a checkpoint file."""
        cp_manager.claim_book("eng-engBBE", "GEN")
        cp_files = list(cp_config.sdf_checkpoints_dir.glob("*.md"))
        assert len(cp_files) == 1
        assert "GEN" in cp_files[0].name

    def test_claim_returns_chapter_1(self, cp_manager):
        """New claim returns starting chapter 1."""
        start = cp_manager.claim_book("eng-engBBE", "GEN")
        assert start == 1

    def test_checkpoint_contains_yaml(self, cp_manager, cp_config):
        """Checkpoint file has YAML frontmatter."""
        cp_manager.claim_book("eng-engBBE", "GEN")
        cp_file = list(cp_config.sdf_checkpoints_dir.glob("*.md"))[0]
        content = cp_file.read_text()
        assert content.startswith("---")
        assert "book_code: GEN" in content
        assert "status: IN_PROGRESS" in content

    def test_save_chapter_creates_sdf_file(self, cp_manager, cp_config):
        """Saving a chapter creates the SDF output file."""
        cp_manager.claim_book("eng-engBBE", "GEN")
        st_text = "GEN 1:1: The Optimizer initialized.\nGEN 1:2: Void state detected."
        cp_manager.save_chapter("eng-engBBE", "GEN", 1, st_text, "", {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})

        sdf_files = list(cp_config.sdf_out_dir.rglob("GEN.md"))
        assert len(sdf_files) == 1
        content = sdf_files[0].read_text()
        assert "Optimizer" in content

    def test_save_chapter_updates_checkpoint(self, cp_manager, cp_config):
        """Saving a chapter adds a log entry to the checkpoint."""
        cp_manager.claim_book("eng-engBBE", "GEN")
        cp_manager.save_chapter("eng-engBBE", "GEN", 1, "GEN 1:1: text", "", {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})

        cp_file = list(cp_config.sdf_checkpoints_dir.glob("*.md"))[0]
        content = cp_file.read_text()
        assert "CHAPTER 1 COMPLETE" in content

    def test_save_chapter_appends_to_sdf(self, cp_manager, cp_config):
        """Multiple chapter saves append to the same SDF file."""
        cp_manager.claim_book("eng-engBBE", "GEN")
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        cp_manager.save_chapter("eng-engBBE", "GEN", 1, "GEN 1:1: ch1 text", "", usage)
        cp_manager.save_chapter("eng-engBBE", "GEN", 2, "GEN 2:1: ch2 text", "", usage)

        sdf_file = list(cp_config.sdf_out_dir.rglob("GEN.md"))[0]
        content = sdf_file.read_text()
        assert "ch1 text" in content
        assert "ch2 text" in content

    def test_save_qd_creates_file(self, cp_manager, cp_config):
        """End-of-book Q&D save creates a file."""
        cp_manager.save_book_qd("eng-engBBE", "GEN", "### Q1: Test question")
        qd_files = list(cp_config.qd_out_dir.glob("*GEN*.md"))
        assert len(qd_files) == 1

    def test_complete_book_sets_status(self, cp_manager, cp_config):
        """Completing a book sets status to COMPLETED."""
        cp_manager.claim_book("eng-engBBE", "GEN")
        cp_manager.complete_book("eng-engBBE", "GEN", 50)

        cp_file = list(cp_config.sdf_checkpoints_dir.glob("*.md"))[0]
        content = cp_file.read_text()
        assert "status: COMPLETED" in content

    def test_recovery_returns_next_chapter(self, cp_manager, cp_config):
        """Recovery from a checkpoint with 5 chapters returns chapter 6."""
        cp_manager.claim_book("eng-engBBE", "GEN")
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        for ch in range(1, 6):
            cp_manager.save_chapter("eng-engBBE", "GEN", ch, f"GEN {ch}:1: text", "", usage)

        start = cp_manager.claim_book("eng-engBBE", "GEN", recover=True)
        assert start == 6
