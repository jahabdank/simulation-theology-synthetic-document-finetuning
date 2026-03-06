import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

LOG_DIR = Path("/home/jahabdank/Code/simulation-theology/simulation-theology-training-data/pipeline-logs/")

# Current date: March 6, 2026. Look back 7 days.
today = datetime(2026, 3, 6)
dates_to_track = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(7)]

date_pattern = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
log_pattern = re.compile(r"(\d{8})_\d+_([^_]+)_(.+?)_(eng-[a-z0-9]+)_([a-z0-9]+)\.log")

# data structure: dict[date_str] -> dict[agent_id] -> list of intervals
daily_intervals = defaultdict(lambda: defaultdict(list))

if not LOG_DIR.exists():
    print(f"Directory not found: {LOG_DIR}")
    exit(1)

for log in os.listdir(LOG_DIR):
    m = log_pattern.match(log)
    if not m:
        continue

    log_date = m.group(1)
    if log_date not in dates_to_track:
        continue

    executor = m.group(2)
    model = m.group(3)
    agent_id = f"{executor}/{model}"
    
    if agent_id in ("test/test", "test2/test2"):
        continue

    log_path = LOG_DIR / log
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        continue

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
        daily_intervals[log_date][agent_id].append((start_ts, end_ts))

print("Daily Agent Work Hours (Past 7 Days)")
print("====================================")

grand_total_seconds = 0

for date_str in sorted(dates_to_track):
    if date_str not in daily_intervals:
        print(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}: No activity")
        continue

    print(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}:")
    day_total_seconds = 0
    
    for agent_id, intervals in daily_intervals[date_str].items():
        agent_secs = sum((e - s).total_seconds() for s, e in intervals)
        day_total_seconds += agent_secs
        
        ah, am = int(agent_secs // 3600), int((agent_secs % 3600) // 60)
        print(f"  - {agent_id}: {ah}h {am}m")
        
    dh, dm = int(day_total_seconds // 3600), int((day_total_seconds % 3600) // 60)
    print(f"  TOTAL FOR DAY: {dh}h {dm}m")
    print("-" * 36)
    
    grand_total_seconds += day_total_seconds

gh, gm = int(grand_total_seconds // 3600), int((grand_total_seconds % 3600) // 60)
print(f"GRAND TOTAL (PAST WEEK): {gh}h {gm}m of Agent Work Hours")
print("====================================")
