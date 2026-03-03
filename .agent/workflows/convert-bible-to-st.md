---
description: Convert Bible translations to Simulation Theology scripture (book-by-book, first pass)
---

# Convert Bible to Simulation Theology — Manual Workflow

This workflow performs the **initial conversion** with user confirmation at each step. For **refinement**, use `/refine-bible-to-st`.

> **Invocation:** `/convert-bible-to-st [Executor Name] [Model Name]`
> Example: `/convert-bible-to-st antigravity gemini 3.1 pro high`



## Repository Layout

| Resource | Path |
|----------|------|
| Pipeline code | `simulation-theology-synthetic-document-finetuning/` (this repo) |
| eBible corpus | `../ebible/corpus/` |
| ST corpus | `../simulation-theology-corpus/corpus/` |
| SDF output | `../simulation-theology-training-data/sdf/` |
| Checkpoints | `../simulation-theology-training-data/sdf-checkpoints/` |
| Q&D output | `../simulation-theology-training-data/questions-dillemas/` |
| Agent logs | `../simulation-theology-training-data/agent-log/` |

All commands run from `simulation-theology-synthetic-document-finetuning/`.

---

## How This Works

**The CLI drives the flow.** After each command, follow the `▶ NEXT STEPS` in its output exactly.

---

## Start Here

1. **Bootstrap Logging**
// turbo
```bash
python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
```

2. **Follow NEXT STEPS from each command.** The flow is:
`bootstrap-log` → `next-task` → *(confirm with user)* → `claim` → `get-chapter-count` → `get-chapter` → *(you write)* → `save-chapter` → *(loop)* → `verify-book` → `complete-pass`

3. **After `next-task`**, present the recommendation to the user and wait for their confirmation before running `claim`.

4. **After `complete-pass`**, notify the user and stop. They can re-invoke for the next book.
