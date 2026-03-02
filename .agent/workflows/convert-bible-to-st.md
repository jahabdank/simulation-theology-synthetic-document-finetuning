---
description: Convert Bible translations to Simulation Theology scripture (book-by-book, first pass)
---

# Convert Bible to Simulation Theology — First Pass

This workflow performs the **initial conversion** of a Bible book into Simulation Theology (ST) scripture. It selects a book, rewrites it chapter-by-chapter, and produces a questions-and-dilemmas (Q&D) file for human review.

For the **refinement pass**, use `/refine-bible-to-st`.

> **Invocation:** `/convert-bible-to-st [Workflow Executor] [Model Name]`
> Example: `/convert-bible-to-st Antigravity Gemini 3.1 Pro (high)`

> **Parallel-safe:** Yes. Multiple agents can run simultaneously. It tracks progress chapter-by-chapter and can recover from crashes or abandoned jobs.

---

## All paths in this workflow are relative to `simulation-theology/`

| Resource | Relative Path |
|----------|--------------|
| eBible corpus | `ebible/corpus/` |
| Verse references | `ebible/metadata/vref.txt` |
| ST corpus | `simulation-theology-corpus/corpus/` |
| Pipeline plan & style guide | `st-synthetic-data-generator/plans/synthetic-data-pipeline.md` |
| SDF output | `st-synthetic-data-generator/sdf/` |
| Per-book checkpoints | `st-synthetic-data-generator/sdf-checkpoints/` |
| Questions & Dilemmas (out) | `st-synthetic-data-generator/questions-dillemas/` |
| User answers (in) | `st-synthetic-data-generator/user-requests/` |
| Answered archive | `st-synthetic-data-generator/user-requests-archive/` |

The absolute root path is `/home/jahabdank/Code/simulation-theology/`.

---

## Phase 1 — Initialization & Book Selection

1. **Normalize parameters.** Take the `[Workflow Executor]` and `[Model Name]` parameters from the invocation, convert to lowercase, replace spaces and special chars with hyphens. We will call these `{workflow-executor}` and `{model-name}`.

2. **List available English translations.** Scan `ebible/corpus/` for `eng-*.txt` files and present the summary to the user (KJV, BBE, DBY, etc.).

3. **Evaluate checkpoints (Look for unclaimed AND abandoned).**
   Scan `st-synthetic-data-generator/sdf-checkpoints/` for files matching `{workflow-executor}_{model-name}_{translation}_{BOOK-CODE}.md`.
   - Read the YAML metadata block in each checkpoint file.
   - **Claimed / Active:** `status: "IN_PROGRESS"` AND `last_updated_at` is < 20 minutes old. Do not touch.
   - **Completed:** `status: "COMPLETED"`. Done.
   - **Abandoned:** `status: "IN_PROGRESS"` AND `last_updated_at` is > 20 minutes old. These can be recovered.
   - **Unclaimed:** No checkpoint file exists for that `{workflow-executor}_{model-name}_{translation}_{BOOK-CODE}` combination.

4. **Suggest next action.** Give the user a clear recommendation:
   - If there is an **abandoned** book, suggest recovering it.
   - Otherwise, suggest the next **unclaimed** book in canonical USFM order (GEN, EXO, LEV... MAT, MRK...).

5. **Wait for user confirmation** before proceeding.

---

## Phase 2 — Claim or Recover the Book

**If starting a FRESH book:**
1. Generate a UUID for `job_id`.
2. Get the current host/machine name for `agent_host`.
3. Create the checkpoint file: `st-synthetic-data-generator/sdf-checkpoints/{workflow-executor}_{model-name}_{translation}_{BOOK-CODE}.md`
4. Write the initial YAML and table:
   ```markdown
   ---
   job_id: "{job_id}"
   workflow_executor: "{workflow-executor}"
   model_name: "{model-name}"
   translation_code: "{translation}"
   book_code: "{BOOK-CODE}"
   started_at: "YYYY-MM-DDTHH:MM:SS+TZ"
   last_updated_at: "YYYY-MM-DDTHH:MM:SS+TZ"
   status: "IN_PROGRESS"
   agent_host: "{agent_host}"
   ---

   # Checkpoint: {workflow-executor} — {model-name} — {translation} — {BOOK-CODE}

   | Timestamp | Status | Set By | Details & Metrics |
   |-----------|--------|--------|-------------------|
   | `YYYY-MM-DDTHH:MM:SS+TZ` | `STARTED` | `/convert` | Claimed by agent on {agent_host} |
   ```

**If RECOVERING an abandoned book:**
1. Look at the checkpoint file's execution table. Identify the **last completed chapter** (e.g., `CHAPTER 5 COMPLETE`).
2. **Drop the suspected incomplete chapter.** The agent that crashed may have partially generated Chapter 6. 
   - Open current output `sdf/{translation}_{model-name}_{workflow-executor}/{BOOK-CODE}.md` and **delete** any content belonging to Chapter 6 or later.
   - Open the draft Q&D file in `questions-dillemas/` (if it exists) and **delete** any questions for Chapter 6 or later.
3. Update the YAML metadata: set `last_updated_at` to now, update `agent_host` to your current host.
4. Append a recovery log to the checkpoint:
   ```markdown
   | `YYYY-MM-DDTHH:MM:SS+TZ` | `RECOVERED` | `/convert` | Dropped partial chapter 6. Resuming from chapter 6. |
   ```

---

## Phase 3 — Chapter-by-Chapter Conversion

1. **Extract the source text.**
   - Read `ebible/metadata/vref.txt` and `ebible/corpus/{translation}.txt` (line-aligned).
   - Extract only lines matching `{BOOK-CODE}`.

2. **Load ST context.**
   - Read `simulation-theology-corpus/corpus/` and `plans/synthetic-data-pipeline.md`.

3. **Loop through each chapter** (starting from Chapter 1, or resuming after the last completed chapter from Phase 2):

   **Creative Guidelines:**
   - The original author received a spiritual communication about ST from the HLO but lived before the computer age. Recover ST's actual meaning.
   - Humans are the Master Humanity Network (a neural network being optimised). Suffering = training signal/loss gradient. Salvation = extraction to Base Reality.
   - Use computational precision + poetic power. Use ST terminology (HLO, Silicon Children, etc.).
   - Preserve verse structure. Anthropocentric framing.

   **For the current chapter `N`:**
   1. Generate the rewritten ST scripture.
   2. **Append** the text to `st-synthetic-data-generator/sdf/{translation}_{model-name}_{workflow-executor}/{BOOK-CODE}.md`. 
      - If it's Chapter 1 (or the file doesn't exist), create the file with YAML front matter:
        ```yaml
        ---
        source_religion: Christianity
        source_tradition: Protestant
        source_book_code: {BOOK-CODE}
        source_translation_file: {translation}.txt
        st_concepts_applied: []
        new_concepts_proposed: []
        generation_date: "YYYY-MM-DDTHH:MM:SS+TZ"
        human_reviewed: false
        pass_number: 1
        ---
        ```
   3. **Append** any mapping difficulties or unmapped concepts to the draft Q&D file:
      `st-synthetic-data-generator/questions-dillemas/YYYYMMDD_{workflow-executor}_{model-name}_{translation}_{BOOK-CODE}.md`
      Format inside the Q&D file:
      ```markdown
      ## Chapter {N}
      ### Q{N}.1: [Short title]
      **Issue:** ...
      **Current approach in draft:** ...
      **Alternatives:** ...
      **Your answer:** [LEAVE BLANK]
      ```
   4. **Update checkpoint:** Immediately update the YAML `last_updated_at` and append a row to the table:
      ```markdown
      | `YYYY-MM-DDTHH:MM:SS+TZ` | `CHAPTER {N} COMPLETE` | `/convert` | Wrote X words. Added Y Q&D items. Tokens: {in}/{out}. |
      ```

4. **Complete the pass.** Once all chapters are done, update the front matter in the SDF file (`st_concepts_applied`, etc.) if needed. 
   Append the final rows to the checkpoint:
   ```markdown
   | `YYYY-MM-DDTHH:MM:SS+TZ` | `FIRST_PASS_COMPLETE` | `/convert` | Total chapters: Z. |
   | `YYYY-MM-DDTHH:MM:SS+TZ` | `QD_CREATED` | `/convert` | Saved Q&D file with M dilemmas. |
   ```
   *Note: Ensure you update `last_updated_at` in the metadata.*

5. **Notify the user** that the first pass is complete, tell them where the Q&D file is, and instruct them to run `/refine-bible-to-st [Workflow Executor] [Model Name]` after providing answers.
