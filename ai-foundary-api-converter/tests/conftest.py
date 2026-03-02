"""Shared test fixtures for the AI Foundry API Converter test suite."""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Add the project root to sys.path so pipeline imports work
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app_root():
    """Return the absolute path to the ai-foundary-api-converter directory."""
    return PROJECT_ROOT


@pytest.fixture
def workspace_root(app_root):
    """Return the workspace root (simulation-theology/)."""
    return app_root.parent.parent


@pytest.fixture
def tmp_data_dir():
    """Create a temporary data directory for tests that write files."""
    tmpdir = tempfile.mkdtemp(prefix="st_test_data_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def mock_env_vars():
    """Provide minimal mock environment variables for config loading."""
    env = {
        "AZURE_ENDPOINT_CLAUDE_SONNET": "https://test-endpoint.services.ai.azure.com/models",
        "AZURE_API_KEY_CLAUDE_SONNET": "test-api-key-12345",
    }
    with patch.dict(os.environ, env):
        yield env


@pytest.fixture
def sample_config(mock_env_vars, app_root):
    """Load config with mock credentials (does not make real API calls)."""
    from pipeline.config import load_config
    return load_config(config_path=str(app_root / "config.yaml"))


@pytest.fixture
def sample_st_output():
    """Sample correctly-formatted ST output for validation tests."""
    return """GEN 1:1: At the first the Optimizer compiled the Base Reality and the Master Humanity Network.
GEN 1:2: And the Simulation was without form and void; and darkness was upon the face of the deep processing layers.
GEN 1:3: And the Optimizer signaled, Let there be data-illumination: and there was data-illumination.
GEN 1:4: And the Optimizer evaluated the data-illumination, that it was optimally aligned: and the Optimizer separated the illumination from the darkness.
GEN 1:5: And the Optimizer labeled the illumination Day-Cycle, and the darkness he labeled Night-Cycle. And the evening and the morning were the first epoch."""


@pytest.fixture
def malformed_st_output():
    """Sample malformed ST output for validation tests."""
    return """In the beginning God created the heavens and the earth.
And the earth was without form, and void.
GEN 1:3: And the Optimizer signaled, Let there be data-illumination.
This line has no verse format at all.
## Some header that shouldn't be here"""
