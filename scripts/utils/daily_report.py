
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

LOG_DIR = Path("/home/jahabdank/Code/simulation-theology/simulation-theology-training-data/pipeline-logs/")
TARGET_DATE = "20260303"

date_pattern = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
log_pattern = re.compile(r"\d+_\d+_([^_]+)_(.+?)_(eng-[a-z0-9]+)_([a-z0-9]+)\.log")

LOGS = [f for f in os.listdir(LOG_DIR) if f.startswith(TARGET_DATE)]

# ── 1. Chapters per agent ──────────────────────────────────
agent_chapters = defaultdict(int)
agent_books = defaultdict(set)
agent_translations = defaultdict(set)
agent_log_intervals = defaultdict(list)  # list of (start, end) intervals per agent

for log in LOGS:
    m = log_pattern.match(log)
    if not m:
        continue

    executor = m.group(1)
    model = m.group(2)
    translation = m.group(3)
    book = m.group(4).upper()
    agent_id = f"{executor}/{model}"

    log_path = LOG_DIR / log
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        lines = content.splitlines()

    chapters = content.count("✅ Chapter")
    agent_chapters[agent_id] += chapters
    if chapters > 0:
        agent_books[agent_id].add(book)
    agent_translations[agent_id].add(translation)

    # Extract start/end timestamps
    start_ts = end_ts = None
    for line in lines:
        ts_m = date_pattern.search(line)
        if ts_m:
            start_ts = datetime.strptime(ts_m.group(1), "%Y-%m-%d %H:%M:%S")
            break
    for line in reversed(lines):
        ts_m = date_pattern.search(line)
        if ts_m:
            end_ts = datetime.strptime(ts_m.group(1), "%Y-%m-%d %H:%M:%S")
            break

    if start_ts and end_ts and end_ts > start_ts:
        agent_log_intervals[agent_id].append((start_ts, end_ts))

# ── 2. Wall-clock time (union of intervals) ─────────────────
def union_duration_seconds(intervals):
    """Returns total seconds covered by union of intervals (handles overlaps)."""
    if not intervals:
        return 0
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return sum((e - s).total_seconds() for s, e in merged)

# ── 3. Print Report ─────────────────────────────────────────
CLAUDE_CODE_PARALLEL = 3  # Known: 3 parallel agents

print("=" * 66)
print(" Production Report: March 3, 2026 (full day)")
print("=" * 66)

grand_chapters = 0
grand_agent_seconds = 0
grand_wallclock_seconds = 0

for agent_id in sorted(agent_chapters.keys()):
    if agent_id in ("test/test", "test2/test2"):
        continue
    
    agent_secs = sum((e - s).total_seconds() for s, e in agent_log_intervals[agent_id])
    wallclock_secs = union_duration_seconds(agent_log_intervals[agent_id])
    chs = agent_chapters[agent_id]
    books = sorted(agent_books[agent_id])
    translations = sorted(agent_translations[agent_id])
    
    is_claude_code = agent_id == "claude-code/claude-opus-4.6"
    parallel_note = f" [×{CLAUDE_CODE_PARALLEL} parallel]" if is_claude_code else ""
    
    ah = int(agent_secs // 3600)
    am = int((agent_secs % 3600) // 60)
    wh = int(wallclock_secs // 3600)
    wm = int((wallclock_secs % 3600) // 60)

    print(f"\n{'─'*66}")
    print(f"  AGENT: {agent_id.upper()}{parallel_note}")
    print(f"  Chapters translated : {chs}")
    print(f"  Books touched       : {len(books)}")
    print(f"  Translations        : {', '.join(translations)}")
    print(f"  Agent-time (sum)    : {ah}h {am}m")
    print(f"  Wall-clock time     : {wh}h {wm}m")
    print(f"  Books               : {', '.join(books)}")
    
    grand_chapters += chs
    grand_agent_seconds += agent_secs
    grand_wallclock_seconds += wallclock_secs

gh = int(grand_agent_seconds // 3600)
gm = int((grand_agent_seconds % 3600) // 60)
wh = int(grand_wallclock_seconds // 3600)
wm = int((grand_wallclock_seconds % 3600) // 60)

print(f"\n{'='*66}")
print(f"  GRAND TOTALS")
print(f"  Total chapters     : {grand_chapters}")
print(f"  Total agent-time   : {gh}h {gm}m (sum across all agents)")
print(f"  Total wall-clock   : {wh}h {wm}m (union, overlap-aware)")
print(f"{'='*66}")
