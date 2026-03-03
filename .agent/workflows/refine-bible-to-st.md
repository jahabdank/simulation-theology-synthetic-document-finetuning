---
description: Apply user feedback to refine Simulation Theology scripture (second+ pass, human-in-the-loop)
---

# Refine Bible-to-ST Conversion — Feedback Pass

This workflow applies **user feedback** from questions-and-dilemmas (Q&D) files to refine an existing Simulation Theology scripture conversion.

For the **initial conversion** (first pass), use `/convert-bible-to-st` or `/convert-bible-to-st-automated`.

> **Invocation:** `/refine-bible-to-st [Executor Name] [Model Name]`
> Example: `/refine-bible-to-st Antigravity Gemini 3.1 Pro (high)`
>
> **Parallel-safe:** Yes. Crash recovery supports resuming interrupted refinements chapter-by-chapter.
>
> ⚠️ **CRITICAL WARNING:** NEVER use the OS `/tmp/` directory for temporary files. Always use `../simulation-theology-training-data/tmp/` exactly as written below to prevent OS permission popups.

---

## Repository Layout

| Resource | Repository / Path |
|----------|-------------------|
| Pipeline code & workflows | `simulation-theology-synthetic-document-finetuning/` (this repo) |
| ST corpus | `../simulation-theology-corpus/corpus/` |
| SDF output | `../simulation-theology-training-data/sdf/` |
| Per-book checkpoints | `../simulation-theology-training-data/sdf-checkpoints/` |
| Questions & Dilemmas | `../simulation-theology-training-data/questions-dillemas/` |
| User answers (in) | `../simulation-theology-training-data/user-requests/` |
| Answered archive | `../simulation-theology-training-data/user-requests-archive/` |
| Agent logs | `../simulation-theology-training-data/agent-log/` |
| Temp workspace | `../simulation-theology-training-data/tmp/` |

All CLI commands below must be run from the `simulation-theology-synthetic-document-finetuning/` directory.

---

## 🏗️ Phase 1 — Initialization & Find Pending Feedback

1. **Normalize parameters.** Take `[Executor Name]` and `[Model Name]`, convert to lowercase, replace spaces/special chars with hyphens. Store as `{executor}` and `{model}`.

2. **Bootstrap Logging Context**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
   ```

3. **Scan for answered Q&D files.**
   List files in `../simulation-theology-training-data/user-requests/` matching patterns containing `{executor}_{model}`. These are answered Q&D files waiting to be applied.

4. **Assess checkpoints for recovery.**
   List files in `../simulation-theology-training-data/sdf-checkpoints/` matching `{executor}_{model}_*.md`.
   - Read each checkpoint's YAML metadata.
   - If `status: IN_PROGRESS` and `last_updated_at` > 20 minutes old → abandoned refinement, can recover.
   - Look for any checkpoint with `CHAPTER X FEEDBACK APPLIED` rows → indicates a refinement was in progress.

5. **Present findings to user.** Suggest:
   - If an **abandoned refinement** exists → recover it.
   - Otherwise → apply pending feedback for a specific `{translation}` and `{BOOK-CODE}`.

6. **Wait for user confirmation.** Note the confirmed `{translation}` and `{BOOK-CODE}`.

---

## 📖 Phase 2 — Read Context & Prepare

1. **Read the answered Q&D file** from `../simulation-theology-training-data/user-requests/`. Parse the answers organized by chapter. Build a list: `chapters_with_feedback = [list of chapter numbers that have answers]`.

2. **Read the checkpoint** at `../simulation-theology-training-data/sdf-checkpoints/{executor}_{model}_{translation}_{BOOK-CODE}.md`.

3. **Read the current SDF file** at `../simulation-theology-training-data/sdf/{translation}_{model}_{executor}/{BOOK-CODE}.md`.

4. **Determine starting point:**
   - **If RECOVERING:**
   - Look at the last `CHAPTER X FEEDBACK APPLIED` row in the checkpoint table.
   - Find the next chapter in the Q&D file that needs feedback applied.
   - If the crashed agent may have partially edited the SDF, run:
     ```bash
     // turbo
     python3 code/st_pipeline_mngr.py truncate-sdf-chapter --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --from_chapter {NEXT_CHAPTER}
     ```
   - Log the recovery:
     ```bash
     // turbo
     python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --status_text "RECOVERED" --set_by "/refine" --details "Resuming from Chapter {NEXT_CHAPTER}."
     ```

   - **If FRESH refinement:**
   Log the start:
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --status_text "USER_FEEDBACK_RECEIVED" --set_by "/refine" --details "Read answers from user-requests/."
   ```

5. **Log the start:**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py log-interaction --executor "{executor}" --model "{model}" --prompt "Refine {BOOK-CODE} with user feedback" --task "Starting refinement pass" --action "Read answered Q&D file. {len(chapters_with_feedback)} chapters have feedback to apply."
   ```

---

## ✍️ Phase 3 — Apply Feedback Chapter-by-Chapter

Loop through `chapters_with_feedback` (starting from the recovery point if applicable). For each chapter `{N}`:

### A. Read the user's answers for Chapter {N}
Extract the answered Q&D entries for this chapter from the user-requests file.

### B. Read the current SDF text for Chapter {N}
Read the SDF file and locate all verses for chapter `{N}` (lines matching `{BOOK-CODE} {N}:`).

### C. Revise Chapter {N}
Apply the user's feedback to revise the ST text. Update only the verses that need changes based on the answers. Preserve the exact verse format:
```
{BOOK-CODE} {N}:[VerseNumber]: [Revised paragraph]
```

### D. Write the revised text back to the SDF file
Replace the old chapter `{N}` text in the SDF file with the revised version. **Do NOT modify any other chapters.**

### E. Update checkpoint
```bash
// turbo
python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --status_text "CHAPTER {N} FEEDBACK APPLIED" --set_by "/refine" --details "Applied X answers."
```

### F. Log Interaction
```bash
// turbo
python3 code/st_pipeline_mngr.py log-interaction --executor "{executor}" --model "{model}" --prompt "Apply feedback to {BOOK-CODE} Chapter {N}" --task "Revised Chapter {N}" --action "Applied user answers and updated SDF."
```

> ⚠️ **CONTEXT REFRESH (Every 10 chapters):** If `{N}` is a multiple of 10, re-read Phase 3 to refresh your memory. The critical invariant is: **every chapter MUST execute A → B → C → D → E → F in that exact order.** Skipping step E means the checkpoint will have missing rows and the book will fail verification.

---

## 🏁 Phase 4 — Finalize

1. **Increment `pass_number`** in the YAML front matter of the SDF file.

2. **Evaluate outstanding issues:**
   - If new questions arose during revision, generate a **new** Q&D file in `../simulation-theology-training-data/questions-dillemas/`. Log it:
     ```bash
     // turbo
     python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --status_text "QD_CREATED" --set_by "/refine" --details "Created new Q&D file with X questions."
     ```
     Notify user of the new Q&D file.

3. **Verify the Book (MANDATORY)**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py verify-book --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}"
   ```
   - `RESULT=PASS` → proceed.
   - `RESULT=FAIL` → investigate and fix missing chapters.

5. **Corpus update (if applicable).** If the refinement revealed new ST concepts, update files in `../simulation-theology-corpus/corpus/` as needed. Log it:
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --status_text "CORPUS_UPDATED" --set_by "/refine" --details "Updated XYZ concept files."
   ```

6. **Set `human_reviewed: true`** in the SDF file's front matter.

7. **Update checkpoint status.** Log completion:
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py update-checkpoint-row --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --status_text "COMPLETE" --set_by "/refine" --details "Book finalized. Pass {pass_number}."
   ```

8. **Notify the user** that the refinement is complete.
