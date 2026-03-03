---
description: Convert Bible translations to Simulation Theology scripture (executable hybrid workflow)
---

# Convert Bible to Simulation Theology — Hybrid Agent-Code Workflow

This workflow performs the **initial conversion** of a Bible book into Simulation Theology. For **refinement**, use `/refine-bible-to-st`.

> **Invocation:** `/convert-bible-to-st-with-executables [Executor Name] [Model Name]`
> Example: `/convert-bible-to-st-with-executables antigravity gemini 3.1 pro high`



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

**The CLI drives the entire flow.** After running each command, you will see a `▶ NEXT STEPS` block. Follow those instructions exactly. Never skip a step. Never re-run earlier commands unless told to.

Before each chapter, the CLI will show you the source text, key ST concepts, and the exact file paths to write to. Your job is the creative rewrite.

---

## Start Here

1. **Bootstrap Logging**
// turbo
```bash
python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
```

2. **Follow NEXT STEPS from each command.** The flow is:
`bootstrap-log` → `next-task` → `claim` → `get-chapter-count` → `get-chapter` → *(you write)* → `save-chapter` → *(loop)* → `verify-book` → `complete-pass`

3. **Wait for user confirmation** before claiming a new book (unless user authorized automatic mode).

> ⚠️ After `complete-pass`, stop and notify the user. They can re-invoke for the next book.
