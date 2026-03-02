---
description: Apply user feedback to refine Simulation Theology scripture (second+ pass, human-in-the-loop)
---

# Refine Bible-to-ST Conversion — Feedback Pass

This workflow applies **user feedback** from questions-and-dilemmas (Q&D) files to refine an existing Simulation Theology scripture conversion.

For the **initial conversion** (first pass), use `/convert-bible-to-st`.

> **Invocation:** `/refine-bible-to-st [Workflow Executor] [Model Name]`
> Example: `/refine-bible-to-st Antigravity Gemini 3.1 Pro (high)`

> **Parallel-safe:** Yes. Crash recovery supports resuming interrupted refinements chapter-by-chapter.

---

## All paths are relative to `simulation-theology/`

| Resource | Relative Path |
|----------|--------------|
| ST corpus | `simulation-theology-corpus/corpus/` |
| SDF output | `st-synthetic-data-generator/sdf/` |
| Per-book checkpoints | `st-synthetic-data-generator/sdf-checkpoints/` |
| Questions & Dilemmas | `st-synthetic-data-generator/questions-dillemas/` |
| User answers | `st-synthetic-data-generator/user-requests/` |

---

## Step 1 — Initialize & Find Pending Feedback

1. **Normalize parameters.** Convert `[Workflow Executor]` and `[Model Name]` to lowercase, replace spaces/special chars with hyphens. We will call these `{workflow-executor}` and `{model-name}`.
2. **Scan `user-requests/`** for answered Q&D files matching `{workflow-executor}_{model-name}_{translation}_{BOOK-CODE}`.
3. **Assess Checkpoints for Recovery:**
   Check `sdf-checkpoints/` for any workflow that crashed during refinement. If a checkpoint's `status` is `IN_PROGRESS` and the metadata `last_updated_at` is > 20 minutes old, the job was abandoned.
4. **Suggest action:** Process pending feedback, or recover an abandoned refinement.
5. Wait for user confirmation.

---

## Step 2 — Read Context & Recover (if needed)

1. Read the answered Q&D file from `user-requests/`. It organizes answered questions by chapter.
2. Read the checkpoint: `sdf-checkpoints/{workflow-executor}_{model-name}_{translation}_{BOOK-CODE}.md`.
3. **If RECOVERING:**
   - Look at the last `CHAPTER X FEEDBACK APPLIED` in the checkpoint table.
   - Find the next chapter in the Q&D file that needs feedback applied.
   - Identify that the crashed agent may have corrupted the SDF file for the next chapter. If possible, regenerate or carefully overwrite only the needed sections.
   - Update YAML metadata: set `last_updated_at` to now, update `agent_host`.
   - Append to checkpoint: `| YYYY-MM-DDTHH:MM:SS+TZ | RECOVERED | /refine | Resuming from Chapter Y on {agent_host} |`
4. **If FRESH refinement:**
   - Update YAML metadata.
   - Append to checkpoint: `| YYYY-MM-DDTHH:MM:SS+TZ | USER_FEEDBACK_RECEIVED | /refine | Read answers from user-requests/ |`

---

## Step 3 — Apply Feedback Chapter-by-Chapter

1. **Loop through each chapter** in the answered Q&D file (or resume from recovery point):
   1. Read the current SDF text from `sdf/{translation}_{model-name}_{workflow-executor}/{BOOK-CODE}.md`.
   2. Read the user's answers for Chapter `N`.
   3. Revise Chapter `N` in the SDF text.
   4. **Update checkpoint** immediately (log the applied feedback and tokens used):
      ```markdown
      | `YYYY-MM-DDTHH:MM:SS+TZ` | `CHAPTER {N} FEEDBACK APPLIED` | `/refine` | Tokens: {in}/{out}. |
      ```

2. **Increment `pass_number`** in the YAML front matter of the SDF file.

3. **Evaluate outstanding issues:**
   - If new questions arose during revision, generate a **new** Q&D file to `questions-dillemas/`. Append `| YYYY-MM-DDTHH:MM:SS+TZ | QD_CREATED | /refine | Created new Q&D file with X questions. |` to the table. Notify user.
   - If everything is resolved exactly, proceed to Step 4.

---

## Step 4 — Corpus Update & Finalize

1. **Update the ST corpus.** Review the finalized book for new concepts. Update files in `simulation-theology-corpus/corpus/` as needed.
2. Update YAML and append to table: `| YYYY-MM-DDTHH:MM:SS+TZ | CORPUS_UPDATED | /refine | Updated XYZ concept files. |`
3. Set front matter `human_reviewed: true` in the SDF book file.
4. Move the processed Q&D file from `user-requests/` to `user-requests-archive/`.
5. Update YAML (`status: COMPLETED`) and append to table: `| YYYY-MM-DDTHH:MM:SS+TZ | COMPLETE | /refine | Book finalized. |`
6. Notify the user the book is complete.
