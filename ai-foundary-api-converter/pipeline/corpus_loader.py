"""ST Corpus loader — configurable corpus injection modes."""

from pathlib import Path
from typing import List
from pipeline.config import AppConfig


class CorpusLoader:
    """Loads Simulation Theology corpus content for system prompt injection."""

    def __init__(self, config: AppConfig):
        self.config = config

    def load(self) -> str:
        """
        Load corpus content based on the configured mode:
            - 'full': load all .md files in the corpus directory
            - 'select_files': load only the files listed in config
            - 'core_axioms_only': load only Core Axiom 1-9
        """
        mode = self.config.conversion.corpus_mode
        corpus_dir = self.config.corpus_dir

        if not corpus_dir.exists():
            return "[WARNING: Corpus directory not found. No theological context loaded.]"

        if mode == "full":
            return self._load_all(corpus_dir)
        elif mode == "select_files":
            return self._load_selected(corpus_dir, self.config.conversion.corpus_files)
        elif mode == "core_axioms_only":
            return self._load_core_axioms(corpus_dir)
        else:
            return f"[WARNING: Unknown corpus_mode '{mode}'. No context loaded.]"

    def _load_all(self, corpus_dir: Path) -> str:
        """Load all markdown files from the corpus directory."""
        files = sorted(corpus_dir.glob("*.md"))
        return self._concatenate_files(files)

    def _load_selected(self, corpus_dir: Path, filenames: List[str]) -> str:
        """Load only the specified files."""
        files = []
        for name in filenames:
            path = corpus_dir / name
            if path.exists():
                files.append(path)
        return self._concatenate_files(files)

    def _load_core_axioms(self, corpus_dir: Path) -> str:
        """Load Core Axiom 1 through 9."""
        files = []
        for i in range(1, 10):
            path = corpus_dir / f"Core Axiom {i}.md"
            if path.exists():
                files.append(path)
        return self._concatenate_files(files)

    def _concatenate_files(self, files: List[Path]) -> str:
        """Read and concatenate a list of files with headers."""
        if not files:
            return "[No corpus files found for the configured mode.]"

        parts = []
        for f in files:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
            parts.append(f"### {f.stem}\n{content}")

        return "\n\n---\n\n".join(parts)
