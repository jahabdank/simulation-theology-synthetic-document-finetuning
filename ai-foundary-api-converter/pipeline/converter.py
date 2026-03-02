"""Core conversion orchestrator — runs the full book conversion pipeline."""

import logging
from typing import List, Dict, Tuple

from pipeline.config import AppConfig
from pipeline.client import AzureAIClient
from pipeline.bible_reader import BibleReader
from pipeline.corpus_loader import CorpusLoader
from pipeline.checkpoint_manager import CheckpointManager
from pipeline.prompts import (
    build_system_prompt, build_corpus_message,
    build_chapter_prompt, build_qd_prompt,
)
from pipeline.validator import validate_chapter_output


class BookConverter:
    """Orchestrates the full Bible-to-ST conversion pipeline."""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client = AzureAIClient(config, logger)
        self.bible = BibleReader(config)
        self.corpus = CorpusLoader(config)
        self.checkpoints = CheckpointManager(config, logger)
        self.total_tokens_used = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_continuous(self):
        """Loop endlessly, converting books until corpus is exhausted."""
        iteration = 0
        while True:
            iteration += 1
            self.logger.info(f"=== Continuous Loop — Iteration {iteration} ===")

            result = self.checkpoints.find_next_task()
            if result is None:
                self.logger.info("All translations and books are complete! Exiting loop.")
                break

            action, translation, book_code = result
            self.logger.info(f"Next task: ACTION={action} TRANSLATION={translation} BOOK={book_code}")
            self.convert_book(translation, book_code, recover=(action == "RECOVER"))

        self.logger.info(f"Continuous run finished. Total tokens used: {self.total_tokens_used}")

    def run_next(self):
        """Find and convert the single next available book."""
        result = self.checkpoints.find_next_task()
        if result is None:
            self.logger.info("No more books to convert!")
            return

        action, translation, book_code = result
        self.logger.info(f"Next task: ACTION={action} TRANSLATION={translation} BOOK={book_code}")
        self.convert_book(translation, book_code, recover=(action == "RECOVER"))

    # ------------------------------------------------------------------
    # Core Conversion
    # ------------------------------------------------------------------

    def convert_book(self, translation: str, book_code: str, recover: bool = False):
        """Convert an entire book chapter by chapter."""
        book_code = book_code.upper()

        # Claim or recover
        start_chapter = self.checkpoints.claim_book(translation, book_code, recover)

        # Get total chapters
        total_chapters = self.bible.get_total_chapters(translation, book_code)
        if total_chapters == 0:
            self.logger.error(f"No chapters found for {book_code} in {translation}!")
            return

        self.logger.info(
            f"Converting {book_code} ({translation}): "
            f"chapters {start_chapter}–{total_chapters}"
        )

        # Build system prompt (without corpus)
        system_prompt = build_system_prompt(book_code, translation)

        # Build corpus injection message
        corpus_text = self.corpus.load()
        corpus_msg = build_corpus_message(corpus_text)

        # Initialize conversation:
        #   1. System prompt (conversion rules)
        #   2. User message (corpus context)
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": corpus_msg},
            {"role": "assistant", "content": "Understood. I have studied the Simulation Theology corpus and am ready to convert chapters. Please provide the source text."},
        ]

        self.logger.debug(
            f"System prompt: {len(system_prompt)} chars, "
            f"Corpus injection: {len(corpus_msg)} chars "
            f"(mode: {self.config.conversion.corpus_mode})"
        )

        # If recovering, rebuild context from previously saved chapters
        if recover and start_chapter > 1:
            messages = self._rebuild_context(messages, translation, book_code, start_chapter)

        # ------ Chapter Loop ------
        book_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for chapter in range(start_chapter, total_chapters + 1):
            self.logger.info(f"--- {book_code} Chapter {chapter}/{total_chapters} ---")

            # Get source text
            source_text = self.bible.get_chapter(translation, book_code, chapter)
            if not source_text:
                self.logger.error(f"Could not retrieve chapter {chapter}. Skipping.")
                continue

            # Build prompt
            include_qd = (self.config.conversion.qd_mode == "per_chapter")
            user_prompt = build_chapter_prompt(source_text, book_code, chapter, include_qd)
            messages.append({"role": "user", "content": user_prompt})

            # Call API
            self.logger.debug(f"Calling API for chapter {chapter}...")
            response_text, usage = self.client.chat(messages)
            messages.append({"role": "assistant", "content": response_text})

            # Accumulate token usage
            for k in book_tokens:
                book_tokens[k] += usage.get(k, 0)
            self.total_tokens_used += usage.get("total_tokens", 0)

            # Parse and validate
            st_text, qd_text = self._parse_response(response_text, book_code, chapter)

            # Save
            self.checkpoints.save_chapter(
                translation, book_code, chapter, st_text, qd_text, usage
            )

            # Apply history window
            messages = self._apply_history_window(messages)

            self.logger.info(
                f"Chapter {chapter} complete. "
                f"Running book totals — tokens: {book_tokens['total_tokens']}"
            )

        # ------ End-of-Book Q&D ------
        if self.config.conversion.qd_mode == "end_of_book":
            self.logger.info("Generating end-of-book Questions & Dilemmas...")
            qd_prompt = build_qd_prompt(book_code)
            messages.append({"role": "user", "content": qd_prompt})

            qd_response, usage = self.client.chat(messages)
            for k in book_tokens:
                book_tokens[k] += usage.get(k, 0)
            self.total_tokens_used += usage.get("total_tokens", 0)

            self.checkpoints.save_book_qd(translation, book_code, qd_response)

        # ------ Complete ------
        self.checkpoints.complete_book(translation, book_code, total_chapters)
        self.logger.info(
            f"Book {book_code} ({translation}) DONE. "
            f"Book token usage: {book_tokens}"
        )

    # ------------------------------------------------------------------
    # Response Parsing
    # ------------------------------------------------------------------

    def _parse_response(self, response: str, book_code: str, chapter: int) -> Tuple[str, str]:
        """Parse model response into ST text and optional Q&D text."""
        st_text = response
        qd_text = ""

        # Look for Q&D section markers
        qd_markers = ["### Q", "## Questions", "## Dilemmas", "---\n### Q"]
        for marker in qd_markers:
            if marker in response:
                idx = response.index(marker)
                st_text = response[:idx].strip()
                qd_text = response[idx:].strip()
                break

        # Validate format
        warnings = validate_chapter_output(st_text, book_code, chapter)
        for w in warnings:
            self.logger.warning(f"FORMAT WARNING: {w}")

        return st_text, qd_text

    # ------------------------------------------------------------------
    # Conversation History Management
    # ------------------------------------------------------------------

    def _apply_history_window(self, messages: List[Dict]) -> List[Dict]:
        """Apply conversation history window limits."""
        window = self.config.conversion.history_window

        if window == "full":
            return messages

        try:
            window_size = int(window)
        except ValueError:
            self.logger.warning(
                f"Invalid history_window value '{window}', using 'full'."
            )
            return messages

        # Keep system message + last N user/assistant pairs
        system_msgs = [m for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        # Each chapter = 1 user + 1 assistant = 2 messages
        keep_count = window_size * 2
        if len(conversation) > keep_count:
            self.logger.debug(
                f"Sliding window: keeping last {window_size} exchanges "
                f"({keep_count} msgs), dropping {len(conversation) - keep_count}"
            )
            conversation = conversation[-keep_count:]

        return system_msgs + conversation

    def _rebuild_context(
        self, messages: List[Dict], translation: str,
        book_code: str, start_chapter: int
    ) -> List[Dict]:
        """Rebuild conversation context from previously saved SDF for recovery."""
        self.logger.info(f"Rebuilding context from chapters 1–{start_chapter - 1}...")

        from pipeline.config import sanitize_name
        model_slug = sanitize_name(self.config.active_model_key)
        executor_slug = sanitize_name(self.config.executor_name)

        sdf_file = (
            self.config.sdf_out_dir
            / f"{translation}_{model_slug}_{executor_slug}"
            / f"{book_code}.md"
        )

        if sdf_file.exists():
            with open(sdf_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Strip YAML frontmatter
            if content.startswith("---"):
                try:
                    end = content.index("---", 3)
                    content = content[end + 3:].strip()
                except ValueError:
                    pass

            messages.append({
                "role": "assistant",
                "content": (
                    f"[RECOVERED CONTEXT — Chapters 1–{start_chapter - 1}]\n\n"
                    f"{content}"
                ),
            })
            self.logger.info(
                f"Loaded {len(content)} chars of previous conversion context."
            )
        else:
            self.logger.warning(
                f"No SDF file found at {sdf_file} for recovery context."
            )

        return messages
