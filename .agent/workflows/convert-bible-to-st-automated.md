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
2. Write the ST rewrite to the **EXACT file path shown** (do not modify the path)
3. Write any Q&D dilemmas to the **EXACT file path shown** (or leave empty)
4. Run the save command shown in NEXT STEPS

> ⚠️ **CRITICAL — File Paths:** Always write files to the EXACT paths printed by the pipeline. Never guess or construct paths yourself. If the command says to write to `/home/.../simulation-theology-training-data/drafts/...`, use that exact path. Do NOT write to `simulation-theology-synthetic-document-finetuning/simulation-theology-training-data/drafts/` — that is a different, wrong directory.

---

## Start Here

// turbo
```bash
python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
```

**Then follow the NEXT STEPS printed in the output.** The CLI will guide you through:
`bootstrap-log` → `next-task` → `claim` → `get-chapter-count` → **chapter loop** → `verify-book` → `complete-pass` → `next-task` *(loop books)*

### Chapter Loop (uses `st_chapter_runner.py` for context-safe prompts)

Within each book, the chapter loop uses the orchestrator script to prevent context drift:

```
st_chapter_runner.py get  → (you write ST + Q&D) → st_chapter_runner.py save → (repeat)
```

After `get-chapter-count` prints the first chapter command, switch to using the runner:
```bash
python3 code/st_chapter_runner.py get --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{book_code}" --chapter {N}
```

The runner emits **minimal, focused prompts** with exact file paths at every chapter, preventing path hallucination in long books.

> ⚠️ After `complete-pass`, the workflow will output the command to `next-task`. **You must continue in the same session and execute it to claim the next book.** Do not stop until all books have been assigned.
