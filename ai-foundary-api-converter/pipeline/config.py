"""Configuration loading and validation."""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List


@dataclass
class ModelConfig:
    """Configuration for a single AI model deployment."""
    display_name: str
    deployment_name: str
    endpoint: str
    api_key: str
    api_version: str
    max_output_tokens: int
    temperature: float


@dataclass
class ConversionConfig:
    """Settings controlling the conversion behavior."""
    corpus_mode: str          # 'full', 'select_files', 'core_axioms_only'
    corpus_files: List[str]   # used when corpus_mode == 'select_files'
    history_window: str       # 'full' or integer string
    qd_mode: str              # 'per_chapter' or 'end_of_book'


@dataclass
class AppConfig:
    """Complete application configuration."""
    model: ModelConfig
    active_model_key: str
    conversion: ConversionConfig
    executor_name: str
    translation_priority: List[str]

    # Derived paths
    app_root: Path = field(default_factory=Path)
    project_root: Path = field(default_factory=Path)
    workspace_root: Path = field(default_factory=Path)
    data_dir: Path = field(default_factory=Path)
    ebible_corpus: Path = field(default_factory=Path)
    ebible_vref: Path = field(default_factory=Path)
    sdf_checkpoints_dir: Path = field(default_factory=Path)
    sdf_out_dir: Path = field(default_factory=Path)
    qd_out_dir: Path = field(default_factory=Path)
    corpus_dir: Path = field(default_factory=Path)
    log_dir: Path = field(default_factory=Path)
    tmp_dir: Path = field(default_factory=Path)


def sanitize_name(name: str) -> str:
    """Standardizes names for file paths and identifiers."""
    return name.lower().strip().replace(" ", "-").replace("!", "").replace("_", "-")


def load_config(config_path: str = None, model_override: str = None) -> AppConfig:
    """Load and validate configuration from YAML + .env files."""

    # Paths
    app_root = Path(__file__).parent.parent.resolve()
    project_root = app_root.parent.resolve()            # simulation-theology-synthetic-document-finetuning
    workspace_root = project_root.parent.resolve()       # simulation-theology

    # Load .env from app root
    env_path = app_root / ".env"
    load_dotenv(env_path)

    # Load YAML config
    if config_path is None:
        config_path = app_root / "config.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Determine active model
    active_model_key = model_override or raw.get("active_model", "claude-sonnet-4.6")
    model_def = raw.get("models", {}).get(active_model_key)
    if not model_def:
        available = list(raw.get("models", {}).keys())
        raise ValueError(
            f"Model '{active_model_key}' not found in config. "
            f"Available: {available}"
        )

    # Resolve secrets from environment
    endpoint = os.getenv(model_def["env_endpoint_key"], "")
    api_key = os.getenv(model_def["env_api_key"], "")

    if not endpoint:
        raise ValueError(
            f"Environment variable '{model_def['env_endpoint_key']}' not set. "
            f"Check your .env file."
        )
    if not api_key:
        raise ValueError(
            f"Environment variable '{model_def['env_api_key']}' not set. "
            f"Check your .env file."
        )

    model_config = ModelConfig(
        display_name=model_def["display_name"],
        deployment_name=model_def["deployment_name"],
        endpoint=endpoint,
        api_key=api_key,
        api_version=model_def.get("api_version", "2024-12-01-preview"),
        max_output_tokens=model_def.get("max_output_tokens", 8192),
        temperature=model_def.get("temperature", 0.7),
    )

    conv = raw.get("conversion", {})
    conversion_config = ConversionConfig(
        corpus_mode=conv.get("corpus_mode", "core_axioms_only"),
        corpus_files=conv.get("corpus_files", []),
        history_window=str(conv.get("history_window", "full")),
        qd_mode=conv.get("qd_mode", "end_of_book"),
    )

    data_dir = workspace_root / "simulation-theology-training-data"

    config = AppConfig(
        model=model_config,
        active_model_key=active_model_key,
        conversion=conversion_config,
        executor_name=raw.get("executor_name", "api-converter"),
        translation_priority=raw.get("translation_priority", ["eng-"]),
        app_root=app_root,
        project_root=project_root,
        workspace_root=workspace_root,
        data_dir=data_dir,
        ebible_corpus=workspace_root / "ebible" / "corpus",
        ebible_vref=workspace_root / "ebible" / "metadata" / "vref.txt",
        sdf_checkpoints_dir=data_dir / "sdf-checkpoints",
        sdf_out_dir=data_dir / "sdf",
        qd_out_dir=data_dir / "questions-dillemas",
        corpus_dir=workspace_root / "simulation-theology-corpus" / "corpus",
        log_dir=data_dir / "api-converter-logs",
        tmp_dir=data_dir / "tmp",
    )

    return config
