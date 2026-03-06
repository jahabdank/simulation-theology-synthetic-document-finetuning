
import os
import re
from collections import defaultdict

LOG_DIR = "/home/jahabdank/Code/simulation-theology/simulation-theology-training-data/pipeline-logs/"
LOGS = [f for f in os.listdir(LOG_DIR) if f.startswith("20260303_")]

agent_work = defaultdict(lambda: defaultdict(int))
agent_books = defaultdict(set)

# Formats: 
#   20260303_113328_antigravity_gemini-3-flash_eng-engbbe_2ki.log
#   20260303_150036_claude-code_claude-opus-4.6_eng-engbbe_gen.log
pattern = re.compile(r"\d+_\d+_([^_]+)_(.+)_eng-engbbe_([a-z0-9]+)\.log")

for log in LOGS:
    m = pattern.match(log)
    if not m:
        continue
    
    executor = m.group(1)
    model = m.group(2)
    book = m.group(3).upper()
    agent_id = f"{executor}/{model}".replace("-", " ")
    
    log_path = os.path.join(LOG_DIR, log)
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        chapters = content.count("✅ Chapter")
        agent_work[agent_id][book] += chapters
        if chapters > 0:
            agent_books[agent_id].add(book)

print("Agent Production Overview (March 3, 2026):")
print("=" * 60)

for agent_id in sorted(agent_work.keys()):
    print(f"\nAGENT: {agent_id.upper()}")
    total_chapters = 0
    books_list = []
    for book, count in sorted(agent_work[agent_id].items()):
        if count > 0:
            books_list.append(f"{book}({count})")
            total_chapters += count
    
    print(f"Total Chapters: {total_chapters}")
    print(f"Books & Chaps: {', '.join(books_list)}")

print("\n" + "=" * 60)
