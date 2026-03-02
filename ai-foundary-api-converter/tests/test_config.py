"""Unit tests for configuration loading."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from pipeline.config import load_config, sanitize_name


class TestSanitizeName:
    """Tests for the sanitize_name helper function."""

    def test_basic_sanitization(self):
        assert sanitize_name("Claude Opus 4.6") == "claude-opus-4.6"

    def test_removes_exclamation(self):
        assert sanitize_name("Hello! World!") == "hello-world"

    def test_replaces_underscores(self):
        assert sanitize_name("api_converter") == "api-converter"

    def test_strips_whitespace(self):
        assert sanitize_name("  spaced  ") == "spaced"

    def test_complex_name(self):
        assert sanitize_name("  Gemini 3.1 Pro! High_End ") == "gemini-3.1-pro-high-end"


class TestConfigLoading:
    """Tests for the config loading pipeline."""

    def test_loads_default_config(self, mock_env_vars, app_root):
        """Config loads successfully with default config.yaml."""
        config = load_config(config_path=str(app_root / "config.yaml"))
        assert config.active_model_key == "claude-sonnet-4.6"
        assert config.model.display_name == "Claude Sonnet 4.6 (Anthropic)"

    def test_model_override(self, app_root):
        """--model flag overrides config.yaml active_model."""
        env = {
            "AZURE_ENDPOINT_GPT52": "https://test.openai.azure.com/",
            "AZURE_API_KEY_GPT52": "test-key",
        }
        with patch.dict(os.environ, env):
            config = load_config(
                config_path=str(app_root / "config.yaml"),
                model_override="gpt-5.2",
            )
        assert config.active_model_key == "gpt-5.2"
        assert config.model.deployment_name == "gpt-5-2"

    def test_invalid_model_raises(self, mock_env_vars, app_root):
        """Unknown model key raises ValueError."""
        with pytest.raises(ValueError, match="not found in config"):
            load_config(
                config_path=str(app_root / "config.yaml"),
                model_override="nonexistent-model",
            )

    def test_missing_endpoint_raises(self, app_root):
        """Missing endpoint env var raises ValueError."""
        env = {"AZURE_API_KEY_CLAUDE_SONNET": "key-but-no-endpoint"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not set"):
                load_config(config_path=str(app_root / "config.yaml"))

    def test_missing_api_key_raises(self, app_root):
        """Missing API key env var raises ValueError."""
        env = {"AZURE_ENDPOINT_CLAUDE_SONNET": "https://endpoint.com"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not set"):
                load_config(config_path=str(app_root / "config.yaml"))

    def test_paths_are_resolved(self, sample_config):
        """All path fields are absolute Path objects."""
        assert sample_config.app_root.is_absolute()
        assert sample_config.data_dir.is_absolute()
        assert sample_config.ebible_corpus.is_absolute()
        assert sample_config.corpus_dir.is_absolute()

    def test_conversion_config_defaults(self, sample_config):
        """Conversion config loads all fields."""
        conv = sample_config.conversion
        assert conv.corpus_mode in ("full", "select_files", "core_axioms_only")
        assert conv.history_window in ("full",) or conv.history_window.isdigit()
        assert conv.qd_mode in ("per_chapter", "end_of_book")
