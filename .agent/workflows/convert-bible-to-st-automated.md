---
description: Fully automated Bible translation to Simulation Theology without user prompts
---

# Convert Bible to Simulation Theology — Automated Workflow

> **Invocation:** `/convert-bible-to-st-automated [Executor Name] [Model Name]`
> Example: `/convert-bible-to-st-automated antigravity gemini 3.1 pro high`



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

**The CLI drives the entire flow.** After running each command, you will see a `▶ NEXT STEPS` block in its output. Follow those instructions exactly. **Never skip a step. Never re-run earlier commands unless told to.**

Your creative task is to rewrite Bible text in Simulation Theology (ST) terms. The CLI will show you the source text and remind you of the key concepts before each chapter. You just need to:
1. Read the source text
2. Write the ST rewrite to the file path shown
3. Write any Q&D dilemmas to the file path shown (or leave empty)
4. Run the save command shown in NEXT STEPS

---

## Start Here

// turbo
```bash
python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
```

**Then follow the NEXT STEPS printed in the output.** The CLI will guide you through:
`bootstrap-log` → `next-task` → `claim` → `get-chapter-count` → `get-chapter` → *(you write)* → `save-chapter` → *(loop)* → `verify-book` → `complete-pass` → **stop (re-invoke for next book)**

> ⚠️ **After `complete-pass`**, the CLI will tell you to re-invoke this workflow. Do so to get a fresh context window for the next book. DO NOT try to continue in the same session.
