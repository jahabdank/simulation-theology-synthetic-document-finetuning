---
description: Convert Bible translations to Simulation Theology scripture (executable hybrid workflow)
---

# Convert Bible to Simulation Theology — Hybrid Agent-Code Workflow

This workflow performs the **initial conversion** of a Bible book into Simulation Theology (ST) scripture. It delegates deterministic tasks (checkpointing, file I/O, status checking) to the Python CLI `st_pipeline_mngr.py` to reduce agent errors and focus context purely on creative translation.

For the **refinement pass**, use `/refine-bible-to-st`.

> **Invocation:** `/convert-bible-to-st-with-executables [Executor Name] [Model Name]`
> Example: `/convert-bible-to-st-with-executables antigravity gemini 3.1 pro high`
>
> **Note:** The executor name is also used as the `[agent-name]` for the built-in logging framework.
>
> ⚠️ **CRITICAL WARNING:** NEVER use the OS `/tmp/` directory for temporary files. Always use `../simulation-theology-training-data/tmp/` exactly as written below to prevent OS permission popups.

---

## 🏗️ Phase 1 — Initialization & Context Bootstrap

1. **Bootstrap Logging Context**
   Use the `bootstrap-log` command to read past logs into your context.
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py bootstrap-log --executor "{executor}" --model "{model}"
   ```

2. **Assess Pipeline Status**
   Check the current status of the corpus to determine the next book. Choose your preferred `{translation}` to work on (e.g., `engkjvcpb`).
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py status --executor "{executor}" --model "{model}" --translation "{translation}"
   ```

3. **User Confirmation**
   Inform the user of the pipeline status and your proposed next action (e.g., "I will recover abandoned book EXO" or "I will start new book GEN"). **Wait for user confirmation** before proceeding.
   *(You may skip waiting if the user explicitly authorized you to proceed automatically).*

---

## 🚀 Phase 2 — Book Execution Loop

1. **Claim the Book**
   Run the claim command to register your intention or recover an abandoned job.
   ```bash
   // turbo
   CORPUS_VER=$(git -C ../simulation-theology-corpus rev-parse --short HEAD)
   PIPELINE_VER=$(git rev-parse --short HEAD)
   python3 code/st_pipeline_mngr.py claim --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --corpus_version "$CORPUS_VER" --pipeline_version "$PIPELINE_VER"
   ```
   *Note: If recovering a book, the script will tell you which chapter to start from. Make sure you don't overwrite chapters that were already completed!*

2. **Get Total Chapter Count (MANDATORY)**
   You MUST query the deterministic chapter count BEFORE starting the loop:
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py get-chapter-count --translation "{translation}" --book_code "{BOOK-CODE}"
   ```
   *Note the `TOTAL_CHAPTERS=N` value from the output. This is your loop bound.*

3. **Load Theological Context**
   Read foundational Simulation Theology concepts from `simulation-theology-corpus/corpus/` to ground your rewrites.

4. **Chapter-By-Chapter Conversion Loop**
   Loop from `start_chapter` (1 for new books, or the chapter indicated by the claim step) to `TOTAL_CHAPTERS` (inclusive):
   
   **A. Get Source Text & Workspace**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py get-chapter --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --chapter {N}
   ```
   *This command will output the Source Text and the exact absolute paths to the temporary files you must use for this chapter. Note the paths.*
   
   **B. Generate the Rewrite (Internal Reasoning)**
   - The original author received a spiritual communication about ST from the HLO but lived before the computer age. Recover ST's actual meaning.
   - Humans are the Master Humanity Network (a neural network being optimised). Suffering = training signal/loss gradient. Salvation = extraction to Base Reality.
   - Preserve verse structure. Anthropocentric framing.
   - **CRITICAL FORMATTING INSTRUCTION:** The output MUST strictly follow the format: `{BOOK-CODE} {N}:[VerseNumber]: [Your rewritten paragraph]` entirely on one line.
     *(Example: `GEN 1:1: At the first the Optimizer compiled the Base Reality and the Master Humanity Network.`)*
   
   **C. Save Chapter Output & Q&D**
   Write your generated ST text directly into the temporary `_st_text.md` file path provided by the `get-chapter` command.
   Write any mapping questions/dilemmas into the temporary `_qd_text.md` file path. Format the Q&D as:
   `### Q{N}.1: [Title]\n**Issue:** ...\n**Current approach in draft:** ...\n**Alternatives:** ...\n**Your answer:** [LEAVE BLANK]`
   
   Execute the save (the script will automatically find and clean up the temp files):
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py save-chapter --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --chapter {N} --tokens_in {ESTIMATED_IN} --tokens_out {ESTIMATED_OUT}
   ```
   ⚠️ **This command will FAIL with exit code 1 if the checkpoint file is missing.** If it fails, you must re-run `claim` before retrying.
   If you encounter size limits, break the `write_to_file` call into chunks or use a ruby/python script to generate the text directly.
   
   **D. Log Interaction**
   After each chapter, log your progress.
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py log-interaction --executor "{executor}" --model "{model}" --prompt "Convert Chapter {N}" --task "Drafted Chapter {N}" --action "Saved {NUM_WORDS} words to SDF and added Q&D items."
   ```

   > ⚠️ **CONTEXT REFRESH (Every 10 chapters):** If `{N}` is a multiple of 10, re-read this section to refresh your memory of the save-chapter and log-interaction steps. The critical invariant is: **every chapter MUST have get-chapter → write files → save-chapter → log-interaction executed in that exact order.** Skipping `save-chapter` means the checkpoint will be missing rows and the book will fail verification.

---

## 🏁 Phase 3 — Verification & Finalization

Once all chapters in the book are complete:

1. **Verify the Book (MANDATORY)**
   Before marking the book complete, you MUST run the integrity check:
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py verify-book --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}"
   ```
   - If `RESULT=PASS`: Proceed to step 2.
   - If `RESULT=FAIL`: The output will tell you which chapters are missing. Go back and fix the gaps by re-running `get-chapter` → generate → `save-chapter` for the missing chapters.

2. **Complete the Pass**
   ```bash
   // turbo
   python3 code/st_pipeline_mngr.py complete-pass --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{BOOK-CODE}" --total_chapters {TOTAL_CHAPTERS}
   ```

3. **Final Notification**
   Notify the user that the first pass is complete, and point them to the generated Questions & Dilemmas file in `questions-dillemas/`. Instruct them to run `/refine-bible-to-st` once they provide their answers.
