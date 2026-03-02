"""Checkpoint manager — reads/writes the same checkpoint format as st_pipeline_mngr.py."""

import os
import re
import datetime
import uuid
import yaml
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

from pipeline.config import AppConfig, sanitize_name


class CheckpointManager:
    """Manages SDF checkpoints, output files, and task discovery."""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.executor = sanitize_name(config.executor_name)
        self.model = sanitize_name(config.active_model_key)

    # ------------------------------------------------------------------
    # Task Discovery
    # ------------------------------------------------------------------

    def find_next_task(self) -> Optional[Tuple[str, str, str]]:
        """
        Scan all translations in priority order to find the next book.
        Returns (action, translation, book_code) or None if exhausted.
        """
        from pipeline.bible_reader import BibleReader
        bible = BibleReader(self.config)
        all_translations = bible.get_available_translations()
        all_books = bible.get_available_books()

        for prefix in self.config.translation_priority:
            matching = sorted([t for t in all_translations if t.startswith(prefix)])
            for translation in matching:
                result = self._check_translation(translation, all_books)
                if result:
                    return result

        return None

    def _check_translation(self, translation: str, all_books: List[str]) -> Optional[Tuple[str, str, str]]:
        """Check a single translation for abandoned or unclaimed books."""
        self.config.sdf_checkpoints_dir.mkdir(parents=True, exist_ok=True)
        checkpoints = list(
            self.config.sdf_checkpoints_dir.glob(
                f"{self.executor}_{self.model}_{translation}_*.md"
            )
        )

        abandoned = []
        completed = []
        in_progress = []
        now = datetime.datetime.now(datetime.timezone.utc)

        for cp in checkpoints:
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    content = f.read()
                match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
                if match:
                    meta = yaml.safe_load(match.group(1))
                    book_code = meta.get("book_code")
                    status = meta.get("status")
                    last_updated = datetime.datetime.fromisoformat(
                        meta.get("last_updated_at", now.isoformat())
                    )
                    if status == "COMPLETED":
                        completed.append(book_code)
                    elif status == "IN_PROGRESS":
                        if (now - last_updated).total_seconds() > 20 * 60:
                            abandoned.append(book_code)
                        else:
                            in_progress.append(book_code)
            except Exception:
                pass

        if abandoned:
            return ("RECOVER", translation, abandoned[0])

        unclaimed = [
            b for b in all_books
            if b not in completed and b not in in_progress and b not in abandoned
        ]
        if unclaimed:
            return ("CLAIM", translation, unclaimed[0])

        return None

    # ------------------------------------------------------------------
    # Claim / Recover
    # ------------------------------------------------------------------

    def claim_book(self, translation: str, book_code: str, recover: bool = False) -> int:
        """
        Claim a new book or recover an abandoned one.
        Returns the chapter number to start from.
        """
        book_code = book_code.upper()
        cp_file = self.config.sdf_checkpoints_dir / (
            f"{self.executor}_{self.model}_{translation}_{book_code}.md"
        )
        agent_host = os.uname().nodename if hasattr(os, "uname") else "unknown"
        now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

        # Get version hashes
        corpus_version = self._get_git_hash(self.config.corpus_dir.parent)
        pipeline_version = self._get_git_hash(self.config.project_root)

        if cp_file.exists() and recover:
            return self._recover_checkpoint(cp_file, now_iso, agent_host)
        else:
            return self._new_checkpoint(
                cp_file, book_code, translation, now_iso, agent_host,
                corpus_version, pipeline_version
            )

    def _recover_checkpoint(self, cp_file: Path, now_iso: str, agent_host: str) -> int:
        """Recover an abandoned checkpoint and return starting chapter."""
        self.logger.info(f"Recovering checkpoint: {cp_file.name}")
        with open(cp_file, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            self.logger.error("Could not parse checkpoint YAML.")
            return 1

        meta = yaml.safe_load(match.group(1))
        meta["last_updated_at"] = now_iso
        meta["agent_host"] = agent_host

        # Find last completed chapter
        last_chapter = 0
        for line in content.split("\n"):
            ch_match = re.search(r"CHAPTER (\d+) COMPLETE", line)
            if ch_match:
                last_chapter = int(ch_match.group(1))

        starting_chapter = last_chapter + 1
        self.logger.info(f"Last complete chapter: {last_chapter}. Starting from {starting_chapter}.")

        new_yaml = yaml.dump(meta, sort_keys=False)
        new_content = content.replace(match.group(1), new_yaml.strip() + "\n")
        recovery_log = (
            f"| `{now_iso}` | `RECOVERED` | `api-converter` | "
            f"Dropped partial ch {starting_chapter}. Resuming. |\n"
        )
        new_content += recovery_log

        with open(cp_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        return starting_chapter

    def _new_checkpoint(
        self, cp_file: Path, book_code: str, translation: str,
        now_iso: str, agent_host: str, corpus_version: str, pipeline_version: str
    ) -> int:
        """Create a new checkpoint file and return 1 (start from chapter 1)."""
        self.logger.info(f"Creating new checkpoint for {book_code}...")
        job_id = str(uuid.uuid4())

        meta = {
            "job_id": job_id,
            "workflow_executor": self.executor,
            "model_name": self.model,
            "translation_code": translation,
            "book_code": book_code,
            "corpus_version": corpus_version,
            "pipeline_version": pipeline_version,
            "started_at": now_iso,
            "last_updated_at": now_iso,
            "status": "IN_PROGRESS",
            "agent_host": agent_host,
        }

        yaml_str = yaml.dump(meta, sort_keys=False)
        content = f"---\n{yaml_str}---\n\n"
        content += f"# Checkpoint: {self.executor} - {self.model} - {translation} - {book_code}\n\n"
        content += "| Timestamp | Status | Set By | Details & Metrics |\n"
        content += "|-----------|--------|--------|-------------------|\n"
        content += f"| `{now_iso}` | `STARTED` | `api-converter` | Claimed by {agent_host} |\n"

        self.config.sdf_checkpoints_dir.mkdir(parents=True, exist_ok=True)
        with open(cp_file, "w", encoding="utf-8") as f:
            f.write(content)

        return 1

    # ------------------------------------------------------------------
    # Save Chapter
    # ------------------------------------------------------------------

    def save_chapter(
        self, translation: str, book_code: str, chapter: int,
        st_text: str, qd_text: str, usage: dict
    ):
        """Save a converted chapter to SDF output, Q&D, and update checkpoint."""
        book_code = book_code.upper()
        now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
        now_date = datetime.datetime.now().strftime("%Y%m%d")

        # --- SDF Output ---
        sdf_subdir = self.config.sdf_out_dir / f"{translation}_{self.model}_{self.executor}"
        sdf_subdir.mkdir(parents=True, exist_ok=True)
        sdf_file = sdf_subdir / f"{book_code}.md"

        word_count = len(st_text.split())

        if not sdf_file.exists() or chapter == 1:
            frontmatter = f"""---
source_religion: Christianity
source_tradition: Protestant
source_book_code: {book_code}
source_translation_file: {translation}.txt
st_concepts_applied: []
new_concepts_proposed: []
generation_date: "{now_iso}"
human_reviewed: false
pass_number: 1
---

"""
            with open(sdf_file, "w", encoding="utf-8") as f:
                f.write(frontmatter + st_text + "\n\n")
        else:
            with open(sdf_file, "a", encoding="utf-8") as f:
                f.write(st_text + "\n\n")

        # --- Q&D Output ---
        qd_count = 0
        if qd_text and qd_text.strip():
            self.config.qd_out_dir.mkdir(parents=True, exist_ok=True)
            qd_file = self.config.qd_out_dir / (
                f"{now_date}_{self.executor}_{self.model}_{translation}_{book_code}.md"
            )
            qd_count = qd_text.count("### Q")
            with open(qd_file, "a", encoding="utf-8") as f:
                f.write(qd_text + "\n\n")

        # --- Update Checkpoint ---
        cp_file = self.config.sdf_checkpoints_dir / (
            f"{self.executor}_{self.model}_{translation}_{book_code}.md"
        )
        if cp_file.exists():
            with open(cp_file, "r", encoding="utf-8") as f:
                content = f.read()

            match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
            if match:
                meta = yaml.safe_load(match.group(1))
                meta["last_updated_at"] = now_iso
                new_yaml = yaml.dump(meta, sort_keys=False)
                new_content = content.replace(match.group(1), new_yaml.strip() + "\n")

                tokens_in = usage.get("prompt_tokens", "?")
                tokens_out = usage.get("completion_tokens", "?")
                log_entry = (
                    f"| `{now_iso}` | `CHAPTER {chapter} COMPLETE` | "
                    f"`api-converter` | {word_count} words. "
                    f"{qd_count} Q&D. Tokens: {tokens_in}/{tokens_out}. |\n"
                )
                new_content += log_entry

                with open(cp_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

        self.logger.info(
            f"Chapter {chapter} saved: {word_count} words, "
            f"{qd_count} Q&D items, "
            f"tokens: {usage.get('prompt_tokens', '?')}/{usage.get('completion_tokens', '?')}"
        )

    # ------------------------------------------------------------------
    # Save Book-Level Q&D
    # ------------------------------------------------------------------

    def save_book_qd(self, translation: str, book_code: str, qd_text: str):
        """Save the end-of-book Q&D output."""
        if not qd_text or not qd_text.strip():
            self.logger.info("No Q&D content generated for end-of-book.")
            return

        now_date = datetime.datetime.now().strftime("%Y%m%d")
        self.config.qd_out_dir.mkdir(parents=True, exist_ok=True)
        qd_file = self.config.qd_out_dir / (
            f"{now_date}_{self.executor}_{self.model}_{translation}_{book_code.upper()}_final.md"
        )
        with open(qd_file, "w", encoding="utf-8") as f:
            f.write(f"# Questions & Dilemmas — {book_code.upper()} ({translation})\n\n")
            f.write(qd_text)

        self.logger.info(f"End-of-book Q&D saved to {qd_file.name}")

    # ------------------------------------------------------------------
    # Complete Book
    # ------------------------------------------------------------------

    def complete_book(self, translation: str, book_code: str, total_chapters: int):
        """Mark a book as complete in the checkpoint."""
        book_code = book_code.upper()
        now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

        cp_file = self.config.sdf_checkpoints_dir / (
            f"{self.executor}_{self.model}_{translation}_{book_code}.md"
        )
        if cp_file.exists():
            with open(cp_file, "r", encoding="utf-8") as f:
                content = f.read()

            match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
            if match:
                meta = yaml.safe_load(match.group(1))
                meta["last_updated_at"] = now_iso
                meta["status"] = "COMPLETED"

                new_yaml = yaml.dump(meta, sort_keys=False)
                new_content = content.replace(match.group(1), new_yaml.strip() + "\n")
                new_content += (
                    f"| `{now_iso}` | `COMPLETED` | `api-converter` | "
                    f"All {total_chapters} chapters done. |\n"
                )

                with open(cp_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

        self.logger.info(f"Book {book_code} ({translation}) marked as COMPLETED.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_git_hash(repo_path: Path) -> str:
        """Get short git commit hash for a repository."""
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
