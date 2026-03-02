"""
Integration test: .env file validation.

Verifies that:
- .env file exists and is properly formatted
- All required environment variables for the active model are set
- Endpoint URLs have a valid format
"""

import os
import re
import pytest
from pathlib import Path

from pipeline.config import load_config


VALID_URL_PATTERN = re.compile(r"^https://[\w\-]+\..+")


class TestEnvSetup:
    """Integration tests for .env file and credential configuration."""

    @pytest.fixture
    def app_root(self):
        return Path(__file__).parent.parent.resolve()

    def test_env_file_exists(self, app_root):
        """A .env file must exist (copied from .env.example)."""
        env_path = app_root / ".env"
        assert env_path.exists(), (
            f".env file not found at {env_path}. "
            f"Copy .env.example to .env and fill in your credentials."
        )

    def test_env_file_has_content(self, app_root):
        """The .env file is not empty."""
        env_path = app_root / ".env"
        if not env_path.exists():
            pytest.skip(".env file not found")
        content = env_path.read_text().strip()
        # Filter out comments and blank lines
        lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
        assert len(lines) >= 2, (
            ".env file should have at least 2 non-comment lines "
            "(one endpoint + one API key)"
        )

    def test_config_loads_from_env(self, app_root):
        """Config loads successfully from .env + config.yaml."""
        try:
            config = load_config(config_path=str(app_root / "config.yaml"))
        except ValueError as e:
            pytest.fail(
                f"Config loading failed: {e}. "
                f"Make sure your .env has the correct variables set."
            )
        assert config.model.endpoint, "Endpoint is empty"
        assert config.model.api_key, "API key is empty"

    def test_endpoint_url_format(self, app_root):
        """Endpoint URL matches Azure AI Foundry URL pattern."""
        try:
            config = load_config(config_path=str(app_root / "config.yaml"))
        except ValueError:
            pytest.skip(".env not configured")

        assert VALID_URL_PATTERN.match(config.model.endpoint), (
            f"Endpoint URL doesn't look valid: '{config.model.endpoint}'. "
            f"Expected format: https://{{resource}}.services.ai.azure.com/models "
            f"or https://{{resource}}.openai.azure.com/"
        )

    def test_api_key_not_placeholder(self, app_root):
        """API key is not the placeholder value from .env.example."""
        try:
            config = load_config(config_path=str(app_root / "config.yaml"))
        except ValueError:
            pytest.skip(".env not configured")

        assert config.model.api_key != "your-api-key-here", (
            "API key is still the placeholder from .env.example. "
            "Update it with your real Azure API key."
        )

    def test_all_six_models_loadable(self, app_root):
        """
        Check which of the 6 models have valid credentials configured.
        This is informational — it reports which models are ready.
        """
        models = [
            "claude-opus-4.6", "gpt-5.3-codex", "gpt-5.2",
            "grok-4", "claude-sonnet-4.6", "mistral-large-3"
        ]
        configured = []
        missing = []
        for m in models:
            try:
                load_config(config_path=str(app_root / "config.yaml"), model_override=m)
                configured.append(m)
            except ValueError:
                missing.append(m)

        print(f"\n  Configured models: {configured}")
        print(f"  Missing models: {missing}")
        assert len(configured) >= 1, (
            "No models have valid credentials. "
            "Configure at least one model in .env."
        )
