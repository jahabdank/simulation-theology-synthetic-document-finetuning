"""Per-run logging setup with unique log files."""

import logging
import datetime
import uuid
from pathlib import Path
from pipeline.config import AppConfig


def setup_run_logger(config: AppConfig) -> logging.Logger:
    """
    Create a logger that writes to both console and a unique per-run log file.

    Log files are named:
        {timestamp}_{model}_{run_id}.log
    and stored in:
        simulation-theology-training-data/api-converter-logs/
    """
    config.log_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex[:8]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    model_slug = config.active_model_key.replace(" ", "-")
    log_filename = f"{timestamp}_{model_slug}_{run_id}.log"
    log_path = config.log_dir / log_filename

    logger = logging.getLogger(f"st-converter-{run_id}")
    logger.setLevel(logging.DEBUG)

    # Formatter
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — DEBUG level (captures everything)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler — INFO level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info(f"Run ID: {run_id}")
    logger.info(f"Log file: {log_path}")
    logger.info(f"Model: {config.model.display_name} ({config.active_model_key})")
    logger.info(f"Executor: {config.executor_name}")

    return logger
