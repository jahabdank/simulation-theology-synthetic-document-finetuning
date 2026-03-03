---
description: Fully automated Bible translation to Simulation Theology without user prompts
---

# Convert Bible to Simulation Theology — Automated Hybrid Workflow

This workflow automatically discovers the next uncompleted book and translation, prioritizing English, Polish, Danish, and German, and performs continuous translation without pausing for user input.

> **Invocation:** `/convert-bible-to-st-automated [Executor Name] [Model Name]`
> Example: `/convert-bible-to-st-automated antigravity gemini 3.1 pro high`
>
> **Note:** The executor name is also used as the `[agent-name]` for the built-in logging framework.
>
> ⚠️ **CRITICAL WARNING:** NEVER use the OS `/tmp/` directory for temporary files. Always use `../simulation-theology-training-data/tmp/` exactly as written below to prevent OS permission popups.

---

## Repository Layout

| Resource | Repository / Path |
|----------|-------------------|
| Pipeline code & workflows | `simulation-theology-synthetic-document-finetuning/` (this repo) |
| eBible corpus | `../ebible/corpus/` |
| Verse references | `../ebible/metadata/vref.txt` |
| ST corpus | `../simulation-theology-corpus/corpus/` |
| SDF output | `../simulation-theology-training-data/sdf/` |
| Per-book checkpoints | `../simulation-theology-training-data/sdf-checkpoints/` |
| Questions & Dilemmas (out) | `../simulation-theology-training-data/questions-dillemas/` |
| Agent logs | `../simulation-theology-training-data/agent-log/` |
| Temp workspace | `../simulation-theology-training-data/tmp/` |

All CLI commands below must be run from the `simulation-theology-synthetic-document-finetuning/` directory.

---

## 🏗️ Phase 1 — Context & Discovery

1. **Bootstrap Logging Context**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
   ```

2. **Discover Next Action**
   Use the `next-task` command to autonomously find the next valid translation and book.
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py next-task --executor "{executor}" --model "{model}"
   ```
   *Note the output which tells you the `{translation}`, `{BOOK-CODE}`, and `{ACTION}`.*
   *If STATUS=COMPLETE, notify the user that all Bibles are finished and stop.*

---

## 🚀 Phase 2 — Book Execution Loop

1. **Claim the Book**
   Depending on the discovered `{ACTION}`, run:
   ```bash
   // turbo
   CORPUS_VER=$(git -C ../simulation-theology-corpus rev-parse --short HEAD)
   PIPELINE_VER=$(git rev-parse --short HEAD)
   python3 code/st_pipeline_mngr.py claim --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --corpus_version "$CORPUS_VER" --pipeline_version "$PIPELINE_VER"
   ```
   *Note: If recovering, identify the starting chapter from the command output.*

2. **Get Total Chapter Count (MANDATORY)**
   You MUST query the deterministic chapter count BEFORE starting the loop. This ensures you know exactly when the book is done.
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py get-chapter-count --translation "{translation}" --book_code "{BOOK-CODE}"
   ```
   *Note the `TOTAL_CHAPTERS=N` value from the output. This is your loop bound.*

3. **Load Theological Context**
   Implicitly recall foundational ST concepts to ground your rewrites.

4. **Chapter-By-Chapter Conversion Loop**
   Loop from `start_chapter` (1 for new books, or the chapter indicated by the claim step for recovery) to `TOTAL_CHAPTERS` (inclusive):
   
   **A. Get Source Text & Workspace**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py get-chapter --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --chapter {N}
   ```
   *This command will output the Source Text and the exact absolute paths to the temporary files you must use for this chapter. Note the paths.*
   
   **B. Generate the Rewrite (Internal Reasoning)**
   - Recover the ST meaning. Master Humanity Network, suffering as loss gradient, salvation as extraction to Base Reality.
   - Preserve verse structure. Anthropocentric framing.
   - **CRITICAL FORMATTING INSTRUCTION:** The output MUST strictly follow the format: `{BOOK-CODE} {N}:[VerseNumber]: [Your rewritten paragraph]` entirely on one line.
     *(Example: `GEN 1:1: At the first the Optimizer compiled the Base Reality and the Master Humanity Network.`)*
   
   **C. Save Chapter Output & Q&D**
   Write your generated ST text directly into the temporary `_st_text.md` file path provided by the `get-chapter` command.
   Write any Q&D into the temporary `_qd_text.md` file path provided. Format:
   ```
   ### Q{N}.1: [Title]
   **Issue:** ...
   **Current approach in draft:** ...
   **Alternatives:** ...
   **Your answer:** [LEAVE BLANK]
   ```
   
   Execute the save (the script will automatically find and clean up the temp files):
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py save-chapter --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --chapter {N} --tokens_in {ESTIMATED_IN} --tokens_out {ESTIMATED_OUT}
   ```
   ⚠️ **This command will FAIL with exit code 1 if the checkpoint file is missing.** If it fails, you must re-run `claim` before retrying.
   
   **D. Log Interaction**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py log-interaction --executor "{executor}" --model "{model}" --prompt "Convert {BOOK-CODE} Chapter {N}" --task "Drafted Chapter {N}" --action "Saved words to SDF and added Q&D items."
   ```

   > ⚠️ **CONTEXT REFRESH (Every 10 chapters):** If `{N}` is a multiple of 10, re-read this section to refresh your memory of the save-chapter and log-interaction steps. Smaller models may lose track of these steps as the context window fills. The critical invariant is: **every chapter MUST have get-chapter → write files → save-chapter → log-interaction executed in that exact order.** Skipping `save-chapter` means the checkpoint will be missing rows and the book will fail verification.

---

## 🏁 Phase 3 — Verification & Auto-Transition

1. **Verify the Book (MANDATORY)**
   Before marking the book complete, you MUST run the integrity check:
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py verify-book --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}"
   ```
   - If `RESULT=PASS`: Proceed to step 2.
   - If `RESULT=FAIL`: The output will tell you which chapters are missing from the checkpoint or the SDF file. You must go back and fix the gaps by re-running `get-chapter` → generate → `save-chapter` for the missing chapters.

2. **Complete the Pass**
   Once `verify-book` passes:
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py complete-pass --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --total_chapters {TOTAL_CHAPTERS}
   ```

3. **Loop Endlessly**
   Once a book is `complete-pass`, you MUST autonomously repeat this entire workflow from **Phase 1, Step 2 (Discover Next Action)**. 
   **DO NOT ask the user for permission to continue.** Simply find the next book and start executing Phase 2 again. Keep looping until the corpus is utterly exhausted or the user manually interrupts you.
