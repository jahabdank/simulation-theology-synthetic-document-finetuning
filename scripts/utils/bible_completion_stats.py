
import os
import re
from pathlib import Path

# Paths
ROOT_DIR = Path("/home/jahabdank/Code/simulation-theology/simulation-theology-synthetic-document-finetuning")
DATA_DIR = ROOT_DIR.parent / "simulation-theology-training-data"
EBIBLE_VREF = ROOT_DIR.parent / "ebible" / "metadata" / "vref.txt"
SDF_DIR = DATA_DIR / "sdf"

def parse_vref():
    total_chapters = 0
    book_chapters = {}
    if not EBIBLE_VREF.exists():
        return 1189, {} # Standard count fallback
    
    with open(EBIBLE_VREF, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(" ")
            if len(parts) >= 2:
                book = parts[0]
                ch = parts[1].split(":")[0]
                if book not in book_chapters:
                    book_chapters[book] = set()
                book_chapters[book].add(ch)
                
    total = sum(len(chs) for chs in book_chapters.values())
    return total, book_chapters

def count_sdf_chapters():
    # Only look at eng-engBBE translations
    bbe_dirs = [d for d in os.listdir(SDF_DIR) if d.startswith("eng-engBBE")]
    
    unique_chapters = set() # Store as "BOOK CH"
    
    for d in bbe_dirs:
        dir_path = SDF_DIR / d
        if not dir_path.is_dir(): continue
        
        for f in os.listdir(dir_path):
            if not f.endswith(".md"): continue
            book = f.replace(".md", "").upper()
            
            with open(dir_path / f, "r", encoding="utf-8") as file:
                content = file.read()
                # Find patterns like "BOOK 1:1:"
                # The format is typically "BOOK 1:1: Text..."
                matches = re.findall(rf"^{re.escape(book)}\s+(\d+):1:", content, re.MULTILINE)
                for ch in matches:
                    unique_chapters.add(f"{book} {ch}")
                    
    return len(unique_chapters), unique_chapters

total_bible_chapters, bible_tree = parse_vref()
completed_count, completed_set = count_sdf_chapters()

percentage = (completed_count / total_bible_chapters) * 100 if total_bible_chapters > 0 else 0

print(f"Bible Completion Report (eng-engBBE)")
print(f"=====================================")
print(f"Total Chapters in Bible: {total_bible_chapters}")
print(f"Unique Chapters Completed: {completed_count}")
print(f"Percentage Complete: {percentage:.2f}%")
print(f"Chapters remaining: {total_bible_chapters - completed_count}")
