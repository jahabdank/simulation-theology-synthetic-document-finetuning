#!/usr/bin/env python3
"""
ST Bible Converter — Azure AI Foundry API

Standalone Python application for automated Bible-to-Simulation-Theology
conversion using Azure AI Foundry's Chat Completions API.

Usage:
    # Convert the next available book (auto-discovery)
    python convert.py

    # Convert a specific book
    python convert.py --translation eng-engBBE --book GEN

    # Use a different model
    python convert.py --model gpt-5.3-codex

    # Continuous mode (loop through all books/translations)
    python convert.py --continuous

    # Custom config file
    python convert.py --config /path/to/config.yaml
"""

import argparse
import sys
import traceback

from pipeline.config import load_config
from pipeline.converter import BookConverter
from pipeline.run_logger import setup_run_logger


def main():
    parser = argparse.ArgumentParser(
        description="Convert Bible to Simulation Theology using Azure AI Foundry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Model key to use (overrides config.yaml active_model)",
    )
    parser.add_argument(
        "--translation", type=str, default=None,
        help="Specific translation to convert (e.g. eng-engBBE)",
    )
    parser.add_argument(
        "--book", type=str, default=None,
        help="Specific book code to convert (e.g. GEN, EXO)",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "--continuous", action="store_true",
        help="Loop continuously through all books and translations",
    )
    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(config_path=args.config, model_override=args.model)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    logger = setup_run_logger(config)
    logger.info("=" * 60)
    logger.info("ST Bible Converter — Azure AI Foundry API")
    logger.info("=" * 60)
    logger.info(f"Config: corpus_mode={config.conversion.corpus_mode}, "
                f"history_window={config.conversion.history_window}, "
                f"qd_mode={config.conversion.qd_mode}")

    # Run
    try:
        converter = BookConverter(config, logger)

        if args.translation and args.book:
            logger.info(f"Mode: specific book ({args.book} / {args.translation})")
            converter.convert_book(args.translation, args.book)
        elif args.continuous:
            logger.info("Mode: continuous (all books, all translations)")
            converter.run_continuous()
        else:
            logger.info("Mode: next available book")
            converter.run_next()

        logger.info("=" * 60)
        logger.info(f"Run complete. Total tokens used: {converter.total_tokens_used}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("Run interrupted by user (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
