---
description: Apply user feedback to refine Simulation Theology scripture (second+ pass, human-in-the-loop)
---

# Refine Simulation Theology Scripture — Feedback Application Workflow

This workflow applies user feedback from answered Q&D files to improve existing SDF translations.

> **Invocation:** `/refine-bible-to-st [Executor Name] [Model Name]`
> Example: `/refine-bible-to-st antigravity gemini 3.1 pro high`



## Repository Layout

| Resource | Path |
|----------|------|
| Pipeline code | `simulation-theology-synthetic-document-finetuning/` (this repo) |
| ST corpus | `../simulation-theology-corpus/corpus/` |
| SDF files | `../simulation-theology-training-data/sdf/` |
| Checkpoints | `../simulation-theology-training-data/sdf-checkpoints/` |
| Q&D files | `../simulation-theology-training-data/questions-dillemas/` |
| Agent logs | `../simulation-theology-training-data/agent-log/` |

All commands run from `simulation-theology-synthetic-document-finetuning/`.

---

## Workflow Steps

### 1. Bootstrap Logging
// turbo
```bash
python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
```

### 2. Identify the Book to Refine
- Check `../simulation-theology-training-data/questions-dillemas/` for answered Q&D files (where `**Your answer:**` fields are filled in).
- Identify the book, translation, and checkpoint.

### 3. Read the Q&D Answers
Read the answered Q&D file. Group the feedback by chapter number.

### 4. Log the Start
// turbo
```bash
python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK}" --status_text "REFINEMENT_STARTED" --set_by "/refine" --details "Applying user feedback from Q&D file."
```

### 5. Chapter-by-Chapter Refinement Loop

For each chapter that has feedback:

**A. Read the existing SDF chapter text** from `../simulation-theology-training-data/sdf/{translation}_{model}_{executor}/{BOOK}.md`

**B. Apply the user's feedback** — revise the SDF text for that chapter, incorporating the answers.

**C. Replace the chapter text in the SDF file.** Only modify the specific chapter — do not touch other chapters.

**D. Log progress:**
// turbo
```bash
python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK}" --status_text "CHAPTER {N} REFINED" --set_by "/refine" --details "Applied X feedback items."
```

**E. Repeat** for the next chapter with feedback.

> ⚠️ **CONTEXT REFRESH:** Every 5 chapters, re-read this section to refresh your memory of the loop structure: Read → Revise → Replace → Log → Repeat.

### 6. Verify Integrity
// turbo
```bash
python3 code/st_pipeline_mngr.py verify-book --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK}"
```

### 7. Finalize
- Increment `pass_number` in the SDF front matter.
- Set `human_reviewed: true` in the SDF front matter.

// turbo
```bash
python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK}" --status_text "REFINEMENT_COMPLETE" --set_by "/refine" --details "Pass {N} complete."
```

### 8. Notify the user that refinement is complete.
