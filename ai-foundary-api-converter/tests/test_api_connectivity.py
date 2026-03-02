"""
Integration test: API connectivity.

Makes a lightweight real API call to verify credentials work.
This test WILL consume a small number of tokens.

Run with: pytest tests/test_api_connectivity.py -v
"""

import pytest
from pathlib import Path

from pipeline.config import load_config
from pipeline.client import AzureAIClient


class TestApiConnectivity:
    """Integration tests that make real API calls to Azure AI Foundry."""

    @pytest.fixture
    def config(self):
        app_root = Path(__file__).parent.parent.resolve()
        try:
            return load_config(config_path=str(app_root / "config.yaml"))
        except ValueError:
            pytest.skip(".env not configured — cannot test API connectivity")

    @pytest.fixture
    def client(self, config):
        import logging
        logger = logging.getLogger("test-api")
        logger.setLevel(logging.DEBUG)
        return AzureAIClient(config, logger)

    def test_simple_completion(self, client):
        """Send a trivial message and get a response."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Respond with exactly one word."},
            {"role": "user", "content": "Say 'OK'."},
        ]
        response, usage = client.chat(messages)
        assert response, "Empty response from API"
        assert len(response) > 0
        print(f"\n  Response: {response.strip()}")
        print(f"  Tokens used: {usage}")

    def test_usage_is_tracked(self, client):
        """Token usage counters are populated."""
        messages = [
            {"role": "user", "content": "Reply with the number 42."},
        ]
        _, usage = client.chat(messages)
        assert usage.get("prompt_tokens", 0) > 0, "prompt_tokens should be > 0"
        assert usage.get("completion_tokens", 0) > 0, "completion_tokens should be > 0"
        assert usage.get("total_tokens", 0) > 0, "total_tokens should be > 0"

    def test_st_conversion_prompt(self, client):
        """Test a minimal ST conversion to verify the model understands."""
        messages = [
            {"role": "system", "content": "You convert Bible text to Simulation Theology. God = The Optimizer. Heaven = Base Reality. Output format: BOOK CH:VS: text"},
            {"role": "user", "content": "Convert this: GEN 1:1: In the beginning God created the heaven and the earth."},
        ]
        response, usage = client.chat(messages)
        assert "1:1" in response, "Response should contain verse reference"
        # Should contain at least one ST term
        st_terms = ["Optimizer", "Base Reality", "Simulation", "HLO", "Network"]
        has_st = any(term.lower() in response.lower() for term in st_terms)
        if not has_st:
            print(f"\n  WARNING: Response may not contain ST terms: {response[:200]}")
        print(f"\n  ST Response: {response.strip()}")
        print(f"  Tokens: {usage}")
