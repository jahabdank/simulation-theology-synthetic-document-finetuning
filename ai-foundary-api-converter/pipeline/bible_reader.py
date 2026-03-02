"""eBible corpus reader — extracts chapters using vref.txt alignment."""

from pathlib import Path
from typing import List, Optional
from pipeline.config import AppConfig


class BibleReader:
    """Reads Bible text from the eBible corpus."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._vrefs: Optional[List[str]] = None

    @property
    def vrefs(self) -> List[str]:
        """Lazily load and cache vref.txt."""
        if self._vrefs is None:
            vref_path = self.config.ebible_vref
            if not vref_path.exists():
                raise FileNotFoundError(f"vref.txt not found at {vref_path}")
            with open(vref_path, "r", encoding="utf-8") as f:
                self._vrefs = [line.strip() for line in f]
        return self._vrefs

    def resolve_translation(self, translation: str) -> str:
        """Resolve a translation code to the exact corpus filename stem."""
        t = translation.lower()
        mapping = {
            "kjv": "engkjvcpb",
            "bbe": "engBBE",
            "dby": "engDBY",
            "dra": "engDRA",
            "ulb": "engULB",
            "bsb": "engbsb",
            "webp": "engwebp",
        }
        lookup_key = t[4:] if t.startswith("eng-") else t
        res = mapping.get(lookup_key, translation)

        if "-" not in res:
            res = f"eng-{res}"

        # Case-insensitive filesystem match
        corpus_dir = self.config.ebible_corpus
        if corpus_dir.exists():
            for f in corpus_dir.glob("*.txt"):
                if f.stem.lower() == res.lower():
                    return f.stem
        return res

    def get_chapter(self, translation: str, book_code: str, chapter: int) -> Optional[str]:
        """Extract a specific chapter's text, returning it as a string."""
        resolved = self.resolve_translation(translation)
        trans_file = self.config.ebible_corpus / f"{resolved}.txt"

        if not trans_file.exists():
            return None

        with open(trans_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        chapter_lines = []
        for i, ref in enumerate(self.vrefs):
            if not ref:
                continue
            parts = ref.split(" ")
            if len(parts) >= 2:
                r_book = parts[0]
                r_ch_vs = parts[1].split(":")
                if r_book == book_code and r_ch_vs[0] == str(chapter):
                    if i < len(lines) and lines[i].strip():
                        chapter_lines.append(f"{ref}: {lines[i].strip()}")

        return "\n".join(chapter_lines) if chapter_lines else None

    def get_total_chapters(self, translation: str, book_code: str) -> int:
        """Count the total number of chapters for a book."""
        chapters = set()
        for ref in self.vrefs:
            if not ref:
                continue
            parts = ref.split(" ")
            if len(parts) >= 2 and parts[0] == book_code:
                ch = parts[1].split(":")[0]
                chapters.add(int(ch))
        return max(chapters) if chapters else 0

    def get_available_books(self) -> List[str]:
        """Get ordered list of all book codes in vref."""
        books = []
        for ref in self.vrefs:
            if not ref:
                continue
            book = ref.split(" ")[0]
            if book not in books:
                books.append(book)
        return books

    def get_available_translations(self) -> List[str]:
        """Get list of all translation file stems in the corpus."""
        if not self.config.ebible_corpus.exists():
            return []
        return sorted([f.stem for f in self.config.ebible_corpus.glob("*.txt")])
