import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

LOG_DIR = Path("/home/jahabdank/Code/simulation-theology/simulation-theology-training-data/pipeline-logs/")
DATES_TO_TRACK = ["20260302", "20260303", "20260304"]

date_pattern = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
log_pattern = re.compile(r"(\d{8})_\d+_([^_]+)_(.+?)_(eng-[a-z0-9]+)_([a-z0-9]+)\.log")

# data structure: dict[date_str] -> dict[agent_id] -> dict[metric]
# metric: chapters, logs_intervals, books, translations
reports = defaultdict(lambda: defaultdict(lambda: {
    "chapters": 0,
    "intervals": [],
    "books": set(),
    "translations": set()
}))

for log in os.listdir(LOG_DIR):
    m = log_pattern.match(log)
    if not m:
        continue

    log_date = m.group(1)
    if log_date not in DATES_TO_TRACK:
        continue

    executor = m.group(2)
    model = m.group(3)
    translation = m.group(4)
    book = m.group(5).upper()
    agent_id = f"{executor}/{model}"
    if agent_id in ("test/test", "test2/test2"):
        continue

    log_path = LOG_DIR / log
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        lines = content.splitlines()

    chapters = content.count("✅ Chapter")
    
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

    reports[log_date][agent_id]["chapters"] += chapters
    if chapters > 0:
        reports[log_date][agent_id]["books"].add(book)
    reports[log_date][agent_id]["translations"].add(translation)
    if start_ts and end_ts and end_ts > start_ts:
        reports[log_date][agent_id]["intervals"].append((start_ts, end_ts))

def union_duration_seconds(intervals):
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

print("3-Day Production Report (March 2 - March 4)")
print("==================================================================")

grand_chapters = 0
grand_agent_secs = 0
grand_wallclock_secs = 0

for date in sorted(reports.keys()):
    print(f"\n──────────────────────────────────────────────────────────────────")
    print(f"  DATE: {date[:4]}-{date[4:6]}-{date[6:]}")
    print(f"──────────────────────────────────────────────────────────────────")
    
    day_chapters = 0
    day_agent_secs = 0
    day_wallclock_secs = 0
    
    for agent_id in sorted(reports[date].keys()):
        data = reports[date][agent_id]
        chs = data["chapters"]
        intervals = data["intervals"]
        books = sorted(data["books"])
        translations = sorted(data["translations"])
        
        agent_secs = sum((e - s).total_seconds() for s, e in intervals)
        wallclock_secs = union_duration_seconds(intervals)
        
        day_chapters += chs
        day_agent_secs += agent_secs
        day_wallclock_secs += wallclock_secs
        
        grand_chapters += chs
        grand_agent_secs += agent_secs
        grand_wallclock_secs += wallclock_secs
        
        is_claude_code = agent_id == "claude-code/claude-opus-4.6"
        parallel_note = f" [parallel pool]" if is_claude_code else ""
        
        ah, am = int(agent_secs // 3600), int((agent_secs % 3600) // 60)
        wh, wm = int(wallclock_secs // 3600), int((wallclock_secs % 3600) // 60)
        
        print(f"  [{agent_id.upper()}]{parallel_note}")
        print(f"    Chapters   : {chs}")
        print(f"    Agent-time : {ah}h {am}m")
        print(f"    Wall-clock : {wh}h {wm}m")
        print(f"    Translations: {', '.join(translations)}")
        book_str = ', '.join(books)
        if len(book_str) > 60: book_str = book_str[:57] + "..."
        print(f"    Books      : {book_str}\n")
        
    dh, dm = int(day_agent_secs // 3600), int((day_agent_secs % 3600) // 60)
    dwh, dwm = int(day_wallclock_secs // 3600), int((day_wallclock_secs % 3600) // 60)
    print(f"  -- Day Totals --")
    print(f"  Chapters: {day_chapters} | Agent-time: {dh}h {dm}m | Wall-clock: {dwh}h {dwm}m")

print("\n==================================================================")
gh, gm = int(grand_agent_secs // 3600), int((grand_agent_secs % 3600) // 60)
gwh, gwm = int(grand_wallclock_secs // 3600), int((grand_wallclock_secs % 3600) // 60)
print(f" GRAND TOTALS (3 DAYS)")
print(f" Chapters     : {grand_chapters}")
print(f" Agent-time   : {gh}h {gm}m")
print(f" Wall-clock   : {gwh}h {gwm}m")
print(f"==================================================================")
