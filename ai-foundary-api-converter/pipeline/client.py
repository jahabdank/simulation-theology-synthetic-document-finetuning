"""Azure AI Foundry Chat Completions client wrapper."""

import logging
from typing import List, Dict, Tuple
from openai import AzureOpenAI
from pipeline.config import AppConfig


class AzureAIClient:
    """
    Thin wrapper around the OpenAI Python SDK configured for Azure AI Foundry.
    All models on Azure AI Foundry (including Claude, Mistral, Grok)
    expose an OpenAI-compatible Chat Completions endpoint.
    """

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.deployment = config.model.deployment_name
        self.max_tokens = config.model.max_output_tokens
        self.temperature = config.model.temperature

        self.client = AzureOpenAI(
            azure_endpoint=config.model.endpoint,
            api_key=config.model.api_key,
            api_version=config.model.api_version,
        )

        self.logger.info(
            f"Azure AI client initialized: "
            f"endpoint={config.model.endpoint}, "
            f"deployment={self.deployment}"
        )

    def chat(self, messages: List[Dict[str, str]]) -> Tuple[str, Dict]:
        """
        Send a chat completion request and return (response_text, usage_dict).

        The usage dict contains:
            prompt_tokens, completion_tokens, total_tokens
        """
        self.logger.debug(
            f"Sending request: {len(messages)} messages, "
            f"last user msg length: "
            f"{len(messages[-1]['content']) if messages else 0} chars"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            self.logger.info(
                f"Response received: {len(content)} chars, "
                f"tokens: {usage['prompt_tokens']} in / "
                f"{usage['completion_tokens']} out / "
                f"{usage['total_tokens']} total"
            )
            self.logger.debug(f"Finish reason: {response.choices[0].finish_reason}")

            return content, usage

        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            raise
