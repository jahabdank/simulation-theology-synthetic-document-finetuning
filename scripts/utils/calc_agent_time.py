
import os
import re
from datetime import datetime

# Adjust paths to be relative to the script location or absolute based on the environment
LOG_DIR = "/home/jahabdank/Code/simulation-theology/simulation-theology-training-data/pipeline-logs/"
LOGS = [f for f in os.listdir(LOG_DIR) if f.startswith("20260303_")]

agent_times = {}
date_pattern = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")

for log in LOGS:
    # Extract agent name from log filename
    # Format: 20260303_113328_antigravity_gemini-3-flash_eng-engbbe_2ki.log
    agent_match = re.search(r"antigravity_([^/]+)_eng-engbbe", log)
    if not agent_match:
        # Fallback for different naming conventions
        agent_match = re.search(r"antigravity_(.*?)_", log)
        if not agent_match:
            continue
    
    agent = agent_match.group(1).replace("-", " ")
    
    log_path = os.path.join(LOG_DIR, log)
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        # We only need the first and last line for duration, but logs are small enough
        lines = f.readlines()
        if not lines:
            continue
        
        start_time = None
        end_time = None
        
        # Look for the first valid timestamp
        for line in lines:
            m = date_pattern.search(line)
            if m:
                start_time = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                break
        
        # Look for the last valid timestamp
        for line in reversed(lines):
            m = date_pattern.search(line)
            if m:
                end_time = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                break
        
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()
            # Sanity check: if duration is negative or unrealistically long, it might be a log rotation issue
            if duration < 0: continue
            
            if agent not in agent_times:
                agent_times[agent] = 0
            agent_times[agent] += duration

print("Agent-Time Report for 2026-03-03:")
print("-" * 40)
total_all = 0
for agent, seconds in sorted(agent_times.items()):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    print(f"{agent:30}: {hours:2}h {minutes:2}m {sec:2}s ({int(seconds)} seconds)")
    total_all += seconds

th = int(total_all // 3600)
tm = int((total_all % 3600) // 60)
ts = int(total_all % 60)
print("-" * 40)
print(f"TOTAL AGENT-TIME: {th}h {tm}m {ts}s ({int(total_all)} seconds)")
