
import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

LOG_DIR = Path("/home/jahabdank/Code/simulation-theology/simulation-theology-training-data/pipeline-logs/")

date_pattern = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
log_pattern = re.compile(r"(\d{8})_\d+_([^_]+)_(.+?)_(eng-[a-z0-9]+)_([a-z0-9]+)\.log")

# Group logs by agent, sorted by time
agent_sessions = defaultdict(list)  # agent_id -> list of (start, end, date, book)

for log in sorted(os.listdir(LOG_DIR)):
    m = log_pattern.match(log)
    if not m:
        continue

    date = m.group(1)
    executor = m.group(2)
    model = m.group(3)
    translation = m.group(4)
    book = m.group(5).upper()
    agent_id = f"{executor}/{model}"

    if agent_id in ("test/test", "test2/test2"):
        continue

    log_path = LOG_DIR / log
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

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

    if start_ts and end_ts:
        agent_sessions[agent_id].append((start_ts, end_ts, translation, book))

print("Agent Lifecycle — Start / Stop / Restart Events")
print("=" * 70)

for agent_id in sorted(agent_sessions.keys()):
    sessions = sorted(agent_sessions[agent_id], key=lambda x: x[0])
    print(f"\nAGENT: {agent_id.upper()}")
    print(f"{'─'*70}")

    prev_end = None
    for i, (start, end, translation, book) in enumerate(sessions):
        gap_str = ""
        if prev_end:
            gap = (start - prev_end).total_seconds()
            if gap > 120:  # only flag gaps > 2 min
                gap_h = int(gap // 3600)
                gap_m = int((gap % 3600) // 60)
                gap_str = f"  ⚠️ GAP BEFORE: {gap_h}h {gap_m}m"

        print(f"  [{translation.upper()}] {book:5s}  START: {start.strftime('%m-%d %H:%M')}  END: {end.strftime('%m-%d %H:%M')}{gap_str}")
        prev_end = end

print("\n" + "=" * 70)
