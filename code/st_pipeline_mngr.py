import argparse
import os
import re
import sys
import datetime
import uuid
import yaml
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT_DIR.parent / "simulation-theology-training-data"
EBIBLE_CORPUS = ROOT_DIR.parent / "ebible" / "corpus"
EBIBLE_VREF = ROOT_DIR.parent / "ebible" / "metadata" / "vref.txt"
SDF_CHECKPOINTS_DIR = DATA_DIR / "sdf-checkpoints"
SDF_OUT_DIR = DATA_DIR / "sdf"
QD_OUT_DIR = DATA_DIR / "questions-dillemas"
AGENT_LOG_DIR = DATA_DIR / "agent-log"
TMP_DIR = DATA_DIR / "drafts"
PROMPTS_DIR = ROOT_DIR / "prompts"
PIPELINE_LOG_DIR = DATA_DIR / "pipeline-logs"

CURRENT_LOG_FILE = None

def log_message(msg):
    print(msg)
    if CURRENT_LOG_FILE is not None:
        try:
            with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
                now_str = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{now_str}] {msg}\n")
        except Exception:
            pass


def print_next_steps(lines):
    """Prints a clearly delimited NEXT STEPS block that the agent must follow."""
    log_message("")
    log_message("╔══════════════════════════════════════════════╗")
    log_message("║              ▶ NEXT STEPS                   ║")
    log_message("╚══════════════════════════════════════════════╝")
    for line in lines:
        log_message(line)
    log_message("─── END NEXT STEPS ────────────────────────────")


def sanitize_name(name):
    """Standardizes names for file paths and identifiers."""
    return name.lower().strip().replace(" ", "-").replace("!", "").replace("_", "-")


def resolve_translation(translation):
    t = translation.lower()
    mapping = {
        "kjv": "engkjvcpb",
        "bbe": "engBBE",
        "dby": "engDBY",
        "dra": "engDRA",
        "ulb": "engULB",
        "bsb": "engbsb",
        "webp": "engwebp"
    }
    lookup_key = t[4:] if t.startswith("eng-") else t
    res = mapping.get(lookup_key, translation)
    if "-" not in res:
        res = f"eng-{res}"
    if EBIBLE_CORPUS.exists():
        for f in EBIBLE_CORPUS.glob("*.txt"):
            if f.stem.lower() == res.lower():
                return f.stem
    return res


def parse_vref():
    vrefs = []
    if not EBIBLE_VREF.exists():
        log_message(f"Error: vref.txt not found at {EBIBLE_VREF}")
        return vrefs
    with open(EBIBLE_VREF, "r", encoding="utf-8") as f:
        for line in f:
            vrefs.append(line.strip())
    return vrefs


def get_total_chapters(book_code, translation=None):
    """Returns the total number of chapters for a book from vref."""
    vrefs = parse_vref()
    chapters = set()
    for ref in vrefs:
        if not ref:
            continue
        parts = ref.split(" ")
        if len(parts) >= 2 and parts[0] == book_code:
            chapters.add(int(parts[1].split(":")[0]))
    return max(chapters) if chapters else 0


def read_checkpoint_meta(cp_file):
    """Reads and returns (content, meta_dict) from a checkpoint file."""
    with open(cp_file, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
    if match:
        meta = yaml.safe_load(match.group(1))
        return content, meta
    return content, {}


def write_checkpoint_meta(cp_file, content, meta):
    """Writes updated meta back to checkpoint file."""
    match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
    if match:
        new_yaml = yaml.dump(meta, sort_keys=False)
        new_content = content.replace(match.group(1), new_yaml.strip() + "\n")
        with open(cp_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        return new_content
    return content


# ══════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════

def status_cmd(args):
    """Scans checkpoints and ebible corpus to suggest the next action."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)

    trans_file = EBIBLE_CORPUS / f"{translation}.txt"
    if not trans_file.exists():
        log_message(f"Error: Translation file {trans_file} not found.")
        sys.exit(1)

    vrefs = parse_vref()
    available_books = []
    for ref in vrefs:
        if not ref:
            continue
        book = ref.split(" ")[0]
        if book not in available_books:
            available_books.append(book)

    checkpoints = list(SDF_CHECKPOINTS_DIR.glob(f"{executor}_{model}_{translation}_*.md"))
    abandoned, completed, in_progress = [], [], []
    now = datetime.datetime.now(datetime.timezone.utc)

    for cp in checkpoints:
        try:
            _, meta = read_checkpoint_meta(cp)
            book_code = meta.get("book_code")
            status = meta.get("status")
            last_updated = datetime.datetime.fromisoformat(meta.get("last_updated_at", now.isoformat()))
            if status == "COMPLETED":
                completed.append(book_code)
            elif status == "IN_PROGRESS":
                if (now - last_updated).total_seconds() > 20 * 60:
                    abandoned.append(book_code)
                else:
                    in_progress.append(book_code)
        except Exception as e:
            log_message(f"Error parsing checkpoint {cp}: {e}")

    log_message("=== Pipeline Status ===")
    log_message(f"Executor: {executor} | Model: {model} | Translation: {translation}")
    log_message(f"Completed: {len(completed)} | Active: {len(in_progress)} | Abandoned: {len(abandoned)}")

    if abandoned:
        log_message(f"\nRECOMMENDATION: Recover abandoned book: {abandoned[0]}")
    else:
        unclaimed = [b for b in available_books if b not in completed and b not in in_progress and b not in abandoned]
        if unclaimed:
            log_message(f"\nRECOMMENDATION: Claim new book: {unclaimed[0]}")
        else:
            log_message("\nNo books left to process for this translation!")


def claim_cmd(args):
    """Claims a new book or recovers an abandoned one."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()

    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    agent_host = os.uname().nodename if hasattr(os, "uname") else "unknown"
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    starting_chapter = 1

    if cp_file.exists():
        log_message(f"Recovering checkpoint {cp_file.name}...")
        content, meta = read_checkpoint_meta(cp_file)
        meta["last_updated_at"] = now_iso
        meta["agent_host"] = agent_host

        # Find last completed chapter
        last_chapter = 0
        for ch_match in re.finditer(r"CHAPTER (\d+) COMPLETE", content):
            last_chapter = max(last_chapter, int(ch_match.group(1)))
        starting_chapter = last_chapter + 1
        log_message(f"Last complete chapter: {last_chapter}. Resuming from {starting_chapter}.")

        new_content = write_checkpoint_meta(cp_file, content, meta)
        recovery_log = f"| `{now_iso}` | `RECOVERED` | `/convert` | Resuming from chapter {starting_chapter} on {agent_host}. |\n"
        with open(cp_file, "a", encoding="utf-8") as f:
            f.write(recovery_log)
    else:
        log_message(f"Creating new checkpoint for {book_code}...")
        job_id = str(uuid.uuid4())
        meta = {
            "job_id": job_id,
            "workflow_executor": executor,
            "model_name": model,
            "translation_code": translation,
            "book_code": book_code,
            "corpus_version": args.corpus_version,
            "pipeline_version": args.pipeline_version,
            "started_at": now_iso,
            "last_updated_at": now_iso,
            "status": "IN_PROGRESS",
            "agent_host": agent_host,
            "total_chapters": 0
        }
        yaml_str = yaml.dump(meta, sort_keys=False)
        content = f"---\n{yaml_str}---\n\n# Checkpoint: {executor} - {model} - {translation} - {book_code}\n\n"
        content += "| Timestamp | Status | Set By | Details & Metrics |\n"
        content += "|-----------|--------|--------|-------------------|\n"
        content += f"| `{now_iso}` | `STARTED` | `/convert` | Claimed by agent on {agent_host} |\n"
        SDF_CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(cp_file, "w", encoding="utf-8") as f:
            f.write(content)

    log_message(f"Claim successful. Starting from Chapter {starting_chapter}.")

    # ── NEXT STEPS ──
    print_next_steps([
        f"Run this command to get the total chapter count:",
        f"```",
        f'python3 code/st_pipeline_mngr.py get-chapter-count --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}"',
        f"```",
    ])


def get_chapter_cmd(args):
    """Extracts a chapter and prints creative instructions + next save command."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    chapter = args.chapter

    trans_file = EBIBLE_CORPUS / f"{translation}.txt"
    if not trans_file.exists():
        log_message(f"FATAL: Translation file {trans_file} not found.")
        sys.exit(1)

    vrefs = parse_vref()
    with open(trans_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    chapter_text = []
    for i, ref in enumerate(vrefs):
        if not ref:
            continue
        parts = ref.split(" ")
        if len(parts) >= 2:
            r_book = parts[0]
            r_ch_vs = parts[1].split(":")
            if r_book == book_code and r_ch_vs[0] == str(chapter):
                if i < len(lines):
                    chapter_text.append(f"{ref}: {lines[i].strip()}")

    if not chapter_text:
        log_message(f"FATAL: Chapter {chapter} not found in {book_code}.")
        sys.exit(1)

    text_out = "\n".join(chapter_text)

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    raw_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_raw.txt"
    st_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_st_text.md"
    qd_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_qd_text.md"

    log_message(f"--- FSTRACE: Creating draft workspaces for chapter {chapter}... ---")
    log_message(f"--- FSTRACE: Generated {raw_file} ---")
    with open(raw_file, "w", encoding="utf-8") as f:
        f.write(text_out)

    log_message(f"--- FSTRACE: Generated empty draft: {st_file} ---")
    with open(st_file, "w", encoding="utf-8") as f:
        f.write("")
        
    log_message(f"--- FSTRACE: Generated empty draft: {qd_file} ---")
    with open(qd_file, "w", encoding="utf-8") as f:
        f.write("")

    log_message("=== BEGIN SOURCE TEXT ===")
    log_message(text_out)
    log_message("=== END SOURCE TEXT ===")

    # Print creative instructions
    creative_file = PROMPTS_DIR / "01_creative_instructions.md"
    if creative_file.exists():
        with open(creative_file, "r", encoding="utf-8") as f:
            log_message(f.read().replace("{BOOK}", book_code).replace("{CH}", str(chapter)))
    
    qd_format_file = PROMPTS_DIR / "02_qd_format_instructions.md"
    if qd_format_file.exists():
        with open(qd_format_file, "r", encoding="utf-8") as f:
            log_message(f.read().replace("{CH}", str(chapter)))

    # ── NEXT STEPS ──
    print_next_steps([
        f"1. Write your ST rewrite to this file:",
        f"   {st_file}",
        f"",
        f"2. Write any Q&D dilemmas to this file (or leave empty):",
        f"   {qd_file}",
        f"",
        f"3. After writing BOTH files, run this EXACT command:",
        f"```",
        f'python3 code/st_pipeline_mngr.py save-chapter --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}" --chapter {chapter}',
        f"```",
        f"",
        f"⚠ DO NOT skip save-chapter. DO NOT re-run status or claim.",
    ])


def _recover_misplaced_files(executor, model, book_code, chapter):
    """
    Search common wrong directories for misplaced draft files and move them
    to the correct TMP_DIR. Returns list of recovered files.

    This handles the context-drift hallucination where the agent writes
    files to wrong paths (e.g. nested repo dirs instead of TMP_DIR).
    """
    recovered = []
    patterns = [
        f"{executor}_{model}_{book_code}_ch{chapter}_st_text.md",
        f"{executor}_{model}_{book_code}_ch{chapter}_qd_text.md",
        f"{executor}_{model}_{book_code}_ch{chapter}_raw.txt",
        f"{executor}_{model}_{book_code}_{chapter}_st_text.md",
        f"{executor}_{model}_{book_code}_{chapter}_qd_text.md",
        f"{executor}_{model}_{book_code}_{chapter}_raw.txt",
    ]

    # Common wrong locations (relative to ROOT_DIR which is the code repo)
    search_roots = [
        ROOT_DIR / "simulation-theology-training-data" / "drafts",
        ROOT_DIR / "simulation-theology-training-data" / "tmp",
        ROOT_DIR / "tmp",
        ROOT_DIR / "drafts",
        Path.cwd() / "drafts",
        Path.cwd() / "tmp",
        # Also check parent-level wrong nesting
        ROOT_DIR.parent / "drafts",
        ROOT_DIR.parent / "tmp",
    ]

    for search_dir in search_roots:
        if not search_dir.exists() or search_dir == TMP_DIR:
            continue
        for pattern in patterns:
            candidate = search_dir / pattern
            if candidate.exists():
                target = TMP_DIR / pattern
                if not target.exists():
                    import shutil
                    shutil.move(str(candidate), str(target))
                    log_message(f"--- FSTRACE: RECOVERED misplaced file: {candidate} → {target} ---")
                    recovered.append(str(target))
                else:
                    log_message(f"--- FSTRACE: Found duplicate at {candidate} (correct copy exists) ---")

    return recovered


def save_chapter_cmd(args):
    """
    Saves translated chapter, updates checkpoint, prints next command.
    Handles both naming conventions for temp files.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    chapter = args.chapter

    # Look for files in both naming conventions
    st_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_st_text.md"
    qd_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_qd_text.md"
    raw_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_raw.txt"
    st_file_alt = TMP_DIR / f"{executor}_{model}_{book_code}_{chapter}_st_text.md"
    qd_file_alt = TMP_DIR / f"{executor}_{model}_{book_code}_{chapter}_qd_text.md"
    raw_file_alt = TMP_DIR / f"{executor}_{model}_{book_code}_{chapter}_raw.txt"

    if st_file.exists():
        active_st = st_file
    elif st_file_alt.exists():
        active_st = st_file_alt
    else:
        # Attempt to recover misplaced files before giving up
        log_message("--- FSTRACE: ST file not found in expected location, searching for misplaced files... ---")
        recovered = _recover_misplaced_files(executor, model, book_code, chapter)
        if recovered:
            log_message(f"--- FSTRACE: Recovered {len(recovered)} misplaced file(s). Retrying... ---")
        # Re-check after recovery
        if st_file.exists():
            active_st = st_file
        elif st_file_alt.exists():
            active_st = st_file_alt
        else:
            log_message("FATAL: ST file not found even after recovery search. Checked:")
            log_message(f"  {st_file}")
            log_message(f"  {st_file_alt}")
            sys.exit(1)

    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    now_date = datetime.datetime.now().strftime("%Y%m%d")

    log_message(f"--- FSTRACE: Looking for written ST drafts... ---")
    log_message(f"--- FSTRACE: Found draft: {active_st} ---")

    # Read ST text
    with open(active_st, "r", encoding="utf-8") as f:
        st_text = f.read()
    word_count = len(st_text.split())

    # SDF Output
    sdf_out_subdir = SDF_OUT_DIR / f"{translation}_{model}_{executor}"
    sdf_out_subdir.mkdir(parents=True, exist_ok=True)
    sdf_file = sdf_out_subdir / f"{book_code}.md"

    if not sdf_file.exists() or chapter == 1:
        frontmatter = f"""---
source_religion: Christianity
source_tradition: Protestant
source_book_code: {book_code}
source_translation_file: {translation}.txt
st_concepts_applied: []
new_concepts_proposed: []
generation_date: "{now_iso}"
human_reviewed: false
pass_number: 1
---

"""
        with open(sdf_file, "w", encoding="utf-8") as f:
            f.write(frontmatter + st_text + "\n\n")
    else:
        with open(sdf_file, "a", encoding="utf-8") as f:
            f.write(st_text + "\n\n")

    # Q&D Output — merge from both naming conventions
    qd_count = 0
    qd_combined = ""
    for qf in [qd_file, qd_file_alt]:
        if qf.exists():
            with open(qf, "r", encoding="utf-8") as f:
                text = f.read()
                if text.strip():
                    qd_combined += text + "\n\n"

    if qd_combined.strip():
        qd_file_out = QD_OUT_DIR / f"{now_date}_{executor}_{model}_{translation}_{book_code}.md"
        QD_OUT_DIR.mkdir(parents=True, exist_ok=True)
        qd_count = qd_combined.count("### Q")
        with open(qd_file_out, "a", encoding="utf-8") as fout:
            fout.write(qd_combined)

    # Update checkpoint
    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if not cp_file.exists():
        log_message(f"FATAL: Checkpoint {cp_file} not found! Run 'claim' first.")
        sys.exit(1)

    content, meta = read_checkpoint_meta(cp_file)
    meta["last_updated_at"] = now_iso
    new_content = write_checkpoint_meta(cp_file, content, meta)

    tokens_in = args.tokens_in if args.tokens_in else "?"
    tokens_out = args.tokens_out if args.tokens_out else "?"
    log_entry = f"| `{now_iso}` | `CHAPTER {chapter} COMPLETE` | `/convert` | Wrote {word_count} words. {qd_count} Q&D. Tokens: {tokens_in}/{tokens_out}. |\n"
    with open(cp_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

    # Cleanup workspace — both conventions
    log_message(f"--- FSTRACE: Cleaning up workspace drafts... ---")
    for f in [st_file, qd_file, raw_file, st_file_alt, qd_file_alt, raw_file_alt]:
        if f.exists():
            f.unlink()
            log_message(f"--- FSTRACE: Deleted {f} ---")

    log_message(f"✅ Chapter {chapter} saved. {word_count} words, {qd_count} Q&D items.")

    # Determine total chapters from checkpoint or vref
    total_chapters = meta.get("total_chapters", 0)
    if total_chapters == 0:
        total_chapters = get_total_chapters(book_code)

    # ── NEXT STEPS ──
    if chapter < total_chapters:
        next_ch = chapter + 1
        lines = [
            f"Chapter {chapter}/{total_chapters} complete.",
            f"",
            f"Run this command to get the next chapter:",
            f"```",
            f'python3 code/st_pipeline_mngr.py get-chapter --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}" --chapter {next_ch}',
            f"```",
            f"",
            f"⚠ DO NOT re-run status, claim, or get-chapter-count.",
            f"⚠ DO NOT skip save-chapter after writing.",
        ]
        # Context refresh every 10 chapters
        if chapter % 10 == 0:
            lines.append("")
            lines.append("── CONTEXT REFRESH ──")
            lines.append("Reminder: The critical invariant is:")
            lines.append("  get-chapter → write ST + Q&D → save-chapter → (repeat)")
            lines.append("Never deviate from this loop.")
        print_next_steps(lines)
    else:
        print_next_steps([
            f"🏁 All {total_chapters} chapters complete!",
            f"",
            f"Run the integrity check:",
            f"```",
            f'python3 code/st_pipeline_mngr.py verify-book --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}"',
            f"```",
        ])


def complete_pass_cmd(args):
    """Marks the first pass as complete in the checkpoint."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    total_chapters = args.total_chapters
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if not cp_file.exists():
        log_message(f"FATAL: Checkpoint {cp_file} not found!")
        sys.exit(1)

    content, meta = read_checkpoint_meta(cp_file)
    meta["last_updated_at"] = now_iso
    meta["status"] = "COMPLETED"
    write_checkpoint_meta(cp_file, content, meta)

    with open(cp_file, "a", encoding="utf-8") as f:
        f.write(f"| `{now_iso}` | `FIRST_PASS_COMPLETE` | `/convert` | Total chapters: {total_chapters}. |\n")
        f.write(f"| `{now_iso}` | `QD_CREATED` | `/convert` | Saved Q&D file with dilemmas. |\n")

    log_message(f"✅ Book {book_code} marked as COMPLETED.")

    # ── NEXT STEPS ──
    print_next_steps([
        f"Book {book_code} is complete! 🎉",
        f"",
        f"To continue with the next book, run:",
        f"```",
        f'python3 code/st_pipeline_mngr.py next-task --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}"',
        f"```",
        f"",
        f"⚠ Do not stop. Proceed immediately to the next book.",
    ])


def check_status_for_translation(executor, model, translation):
    """Internal helper for next-task."""
    trans_file = EBIBLE_CORPUS / f"{translation}.txt"
    if not trans_file.exists():
        return None
    vrefs = parse_vref()
    available_books = []
    for ref in vrefs:
        if not ref:
            continue
        book = ref.split(" ")[0]
        if book not in available_books:
            available_books.append(book)
    checkpoints = list(SDF_CHECKPOINTS_DIR.glob(f"{executor}_{model}_{translation}_*.md"))
    abandoned, completed, in_progress = [], [], []
    now = datetime.datetime.now(datetime.timezone.utc)
    for cp in checkpoints:
        try:
            _, meta = read_checkpoint_meta(cp)
            book_code = meta.get("book_code")
            status = meta.get("status")
            last_updated = datetime.datetime.fromisoformat(meta.get("last_updated_at", now.isoformat()))
            if status == "COMPLETED":
                completed.append(book_code)
            elif status == "IN_PROGRESS":
                if (now - last_updated).total_seconds() > 20 * 60:
                    abandoned.append(book_code)
                else:
                    in_progress.append(book_code)
        except Exception:
            pass
    if abandoned:
        return ("RECOVER", abandoned[0])
    unclaimed = [b for b in available_books if b not in completed and b not in in_progress and b not in abandoned]
    if unclaimed:
        return ("CLAIM", unclaimed[0])
    return None


def next_task_cmd(args):
    """Finds the next book and translation to work on."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)

    prefixes = ["eng-", "pol-", "dan-", "deu-", "spa-", "fra-", ""]
    all_files = list(EBIBLE_CORPUS.glob("*.txt"))

    for prefix in prefixes:
        matching_files = sorted([f.name for f in all_files if f.name.startswith(prefix)])
        for filename in matching_files:
            translation = filename.replace(".txt", "")
            result = check_status_for_translation(executor, model, translation)
            if result:
                action, book = result
                log_message("=== Next Task Found ===")
                log_message(f"TRANSLATION={translation}")
                log_message(f"BOOK_CODE={book}")
                log_message(f"ACTION={action}")

                # ── NEXT STEPS ──
                print_next_steps([
                    f"Run this command to {action.lower()} {book}:",
                    f"```",
                    f'CORPUS_VER=$(git -C ../simulation-theology-corpus rev-parse --short HEAD)',
                    f'PIPELINE_VER=$(git rev-parse --short HEAD)',
                    f'python3 code/st_pipeline_mngr.py claim --executor "{args.executor}" --model "{args.model}" --translation "{translation}" --book_code "{book}" --corpus_version "$CORPUS_VER" --pipeline_version "$PIPELINE_VER"',
                    f"```",
                ])
                return

    log_message("=== Next Task Found ===")
    log_message("STATUS=COMPLETE")
    log_message("All translations are finished! Nothing left to do.")


def bootstrap_log_cmd(args):
    """Bootstraps the agent log directory and reads previous context."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    log_dir = AGENT_LOG_DIR / f"{executor}_{model}"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_files = sorted(list(log_dir.glob("*.md")))
    log_message("=== Agent Logging Bootstrap ===")
    log_message(f"Agent: {executor} | Model: {model}")
    log_message(f"Found {len(log_files)} past session logs.")

    if log_files:
        log_message("Reading the most recent log for context...")
        with open(log_files[-1], "r", encoding="utf-8") as f:
            log_message(f.read())
    else:
        log_message("Fresh session. No prior logs.")

    # ── NEXT STEPS ──
    print_next_steps([
        f"Run this command to find the next book to work on:",
        f"```",
        f'python3 code/st_pipeline_mngr.py next-task --executor "{args.executor}" --model "{args.model}"',
        f"```",
    ])


def log_interaction_cmd(args):
    """Appends an interaction log to the daily agent log file."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    log_dir = AGENT_LOG_DIR / f"{executor}_{model}"
    log_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    daily_file = log_dir / f"{now.strftime('%Y-%m-%d')}.md"

    entry = f"\n## Entry: {now.strftime('%Y-%m-%d %H:%M:%S%z')}\n"
    entry += f"- **User Prompt:** \"{args.prompt.strip()}\"\n"
    entry += f"- **Task/Interaction:** {args.task.strip()}\n"
    entry += f"- **Action Taken:** {args.action.strip()}\n"

    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(entry)
    log_message("Interaction logged.")


def cleanup_workspace_cmd(args):
    """Removes lingering temporary workspace files for an executor/model."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)

    pattern = f"{executor}_{model}_*"
    files = list(TMP_DIR.glob(pattern))

    if not files:
        log_message(f"No workspace files found for {executor}/{model}.")
        return

    for f in files:
        f.unlink()
        log_message(f"Deleted: {f.name}")
    log_message(f"Cleanup complete. Deleted {len(files)} files.")


def get_chapter_count_cmd(args):
    """Returns total chapters and stores it in the checkpoint."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()

    trans_file = EBIBLE_CORPUS / f"{translation}.txt"
    if not trans_file.exists():
        log_message(f"FATAL: Translation file {trans_file} not found.")
        sys.exit(1)

    total = get_total_chapters(book_code)
    if total == 0:
        log_message(f"FATAL: No chapters found for {book_code}.")
        sys.exit(1)

    log_message(f"TOTAL_CHAPTERS={total}")
    log_message(f"Book {book_code} has {total} chapters.")

    # Store total_chapters in checkpoint if it exists
    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if cp_file.exists():
        content, meta = read_checkpoint_meta(cp_file)
        meta["total_chapters"] = total
        write_checkpoint_meta(cp_file, content, meta)

    # Determine starting chapter from checkpoint
    start_chapter = 1
    if cp_file.exists():
        content, _ = read_checkpoint_meta(cp_file)
        last_ch = 0
        for ch_match in re.finditer(r"CHAPTER (\d+) COMPLETE", content):
            last_ch = max(last_ch, int(ch_match.group(1)))
        if last_ch > 0:
            start_chapter = last_ch + 1

    # Print massive theology injection ONCE per book straight from live corpus
    st_corpus_dir = ROOT_DIR.parent / "simulation-theology-corpus" / "corpus"
    if st_corpus_dir.exists():
        log_message("\n=== CORE THEOLOGY INJECTION ===")
        log_message("Read the following deeply to understand the theological mechanics of the simulation.\n")
        
        # Translation Guide First
        guide_file = st_corpus_dir / "SDFT Translation Guide.md"
        if guide_file.exists():
            with open(guide_file, "r", encoding="utf-8") as f:
                log_message(f.read())
        
        log_message("\n---\n")
        
        # Core Axioms 1-9
        for i in range(1, 10):
            axiom_file = st_corpus_dir / f"Core Axiom {i}.md"
            if axiom_file.exists():
                with open(axiom_file, "r", encoding="utf-8") as f:
                    log_message(f.read())
                    log_message("\n")
                    
        log_message("=== END CORE THEOLOGY INJECTION ===")

    # ── NEXT STEPS ──
    if start_chapter <= total:
        print_next_steps([
            f"Now fetch Chapter {start_chapter} (of {total}):",
            f"```",
            f'python3 code/st_pipeline_mngr.py get-chapter --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}" --chapter {start_chapter}',
            f"```",
        ])
    else:
        print_next_steps([
            f"All {total} chapters already have checkpoint rows!",
            f"Run the integrity check:",
            f"```",
            f'python3 code/st_pipeline_mngr.py verify-book --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}"',
            f"```",
        ])


def update_checkpoint_row_cmd(args):
    """Appends a row to checkpoint table. Used by refine workflow."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if not cp_file.exists():
        log_message(f"FATAL: Checkpoint {cp_file} not found!")
        sys.exit(1)

    content, meta = read_checkpoint_meta(cp_file)
    meta["last_updated_at"] = now_iso
    write_checkpoint_meta(cp_file, content, meta)

    row = f"| `{now_iso}` | `{args.status_text}` | `{args.set_by}` | {args.details} |\n"
    with open(cp_file, "a", encoding="utf-8") as f:
        f.write(row)
    log_message(f"Checkpoint row added: {args.status_text}")


def truncate_sdf_chapter_cmd(args):
    """Removes all SDF content from a given chapter onwards for recovery."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    from_chapter = args.from_chapter

    sdf_subdir = SDF_OUT_DIR / f"{translation}_{model}_{executor}"
    sdf_file = sdf_subdir / f"{book_code}.md"

    if not sdf_file.exists():
        log_message(f"FATAL: SDF file {sdf_file} not found!")
        sys.exit(1)

    with open(sdf_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    kept_lines = []
    dropped = 0
    found = False
    for line in lines:
        if not found:
            ch_match = re.match(rf"^{re.escape(book_code)} (\d+):\d+:", line)
            if ch_match and int(ch_match.group(1)) >= from_chapter:
                found = True
                dropped += 1
                continue
            kept_lines.append(line)
        else:
            dropped += 1

    with open(sdf_file, "w", encoding="utf-8") as f:
        f.writelines(kept_lines)

    log_message(f"Truncated SDF: dropped {dropped} lines from chapter {from_chapter} onwards.")


def verify_book_cmd(args):
    """Post-completion integrity check."""
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()

    errors = []
    cp_chapter_set = set()
    sdf_chapters = set()

    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if not cp_file.exists():
        errors.append(f"MISSING CHECKPOINT: {cp_file.name}")
    else:
        content, _ = read_checkpoint_meta(cp_file)
        cp_chapters = re.findall(r"CHAPTER (\d+) COMPLETE", content)
        cp_chapter_set = set(int(c) for c in cp_chapters)

    sdf_subdir = SDF_OUT_DIR / f"{translation}_{model}_{executor}"
    sdf_file = sdf_subdir / f"{book_code}.md"
    if not sdf_file.exists():
        errors.append(f"MISSING SDF FILE: {sdf_file}")
    else:
        with open(sdf_file, "r", encoding="utf-8") as f:
            sdf_content = f.read()
        for m in re.finditer(rf"^{re.escape(book_code)} (\d+):\d+:", sdf_content, re.MULTILINE):
            sdf_chapters.add(int(m.group(1)))

    expected_chapters = set()
    vrefs = parse_vref()
    for ref in vrefs:
        if not ref:
            continue
        parts = ref.split(" ")
        if len(parts) >= 2 and parts[0] == book_code:
            expected_chapters.add(int(parts[1].split(":")[0]))

    total_expected = max(expected_chapters) if expected_chapters else 0

    if not errors:
        missing_in_cp = sdf_chapters - cp_chapter_set
        missing_in_sdf = cp_chapter_set - sdf_chapters
        missing_entirely = expected_chapters - sdf_chapters
        if missing_in_cp:
            errors.append(f"IN SDF BUT NOT CHECKPOINT: {sorted(missing_in_cp)}")
        if missing_in_sdf:
            errors.append(f"IN CHECKPOINT BUT NOT SDF: {sorted(missing_in_sdf)}")
        if missing_entirely:
            errors.append(f"MISSING FROM SDF: {sorted(missing_entirely)}")

    log_message(f"=== Verify Book: {book_code} ===")
    log_message(f"Expected: {total_expected} | Checkpoint: {len(cp_chapter_set)} | SDF: {len(sdf_chapters)}")

    if not errors:
        log_message("RESULT=PASS")
        # ── NEXT STEPS ──
        print_next_steps([
            f"Integrity check passed! Now finalize the book:",
            f"```",
            f'python3 code/st_pipeline_mngr.py complete-pass --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}" --total_chapters {total_expected}',
            f"```",
        ])
    else:
        for e in errors:
            log_message(f"ERROR: {e}")
        log_message("RESULT=FAIL")
        # Print remediation for missing chapters
        if expected_chapters and sdf_chapters:
            missing = sorted(expected_chapters - sdf_chapters)
            if missing:
                print_next_steps([
                    f"Fix the gaps by running get-chapter → write → save-chapter for:",
                    f"  Missing chapters: {missing}",
                    f"```",
                    f'python3 code/st_pipeline_mngr.py get-chapter --executor "{args.executor}" --model "{args.model}" --translation "{args.translation}" --book_code "{book_code}" --chapter {missing[0]}',
                    f"```",
                ])
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ST Pipeline Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p = subparsers.add_parser("status")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)

    # claim
    p = subparsers.add_parser("claim")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)
    p.add_argument("--corpus_version", required=True)
    p.add_argument("--pipeline_version", required=True)

    # get-chapter
    p = subparsers.add_parser("get-chapter")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)
    p.add_argument("--chapter", type=int, required=True)

    # save-chapter
    p = subparsers.add_parser("save-chapter")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)
    p.add_argument("--chapter", type=int, required=True)
    p.add_argument("--tokens_in", required=False)
    p.add_argument("--tokens_out", required=False)

    # complete-pass
    p = subparsers.add_parser("complete-pass")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)
    p.add_argument("--total_chapters", type=int, required=True)

    # bootstrap-log
    p = subparsers.add_parser("bootstrap-log")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)

    # next-task
    p = subparsers.add_parser("next-task")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)

    # log-interaction
    p = subparsers.add_parser("log-interaction")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--action", required=True)

    # cleanup-workspace
    p = subparsers.add_parser("cleanup-workspace")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)

    # get-chapter-count
    p = subparsers.add_parser("get-chapter-count")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)

    # verify-book
    p = subparsers.add_parser("verify-book")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)

    # update-checkpoint-row
    p = subparsers.add_parser("update-checkpoint-row")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)
    p.add_argument("--status_text", required=True)
    p.add_argument("--set_by", required=True)
    p.add_argument("--details", required=True)

    # truncate-sdf-chapter
    p = subparsers.add_parser("truncate-sdf-chapter")
    p.add_argument("--executor", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--translation", required=True)
    p.add_argument("--book_code", required=True)
    p.add_argument("--from_chapter", type=int, required=True)

    args = parser.parse_args()

    global CURRENT_LOG_FILE
    if hasattr(args, "executor") and hasattr(args, "model") and hasattr(args, "book_code") and hasattr(args, "translation"):
        executor = sanitize_name(args.executor)
        model = sanitize_name(args.model)
        translation = sanitize_name(args.translation)
        book_code = sanitize_name(args.book_code)
        
        PIPELINE_LOG_DIR.mkdir(parents=True, exist_ok=True)
        # Find the most recently created log for this book
        pattern = f"*_{executor}_{model}_{translation}_{book_code}.log"
        existing = sorted(list(PIPELINE_LOG_DIR.glob(pattern)))
        
        if existing and getattr(args, "command", "") != "claim":
            # Append to latest if continuing the book
            CURRENT_LOG_FILE = existing[-1]
        else:
            # Create a new log file if it's the first time or we are re-claiming
            now_str = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
            CURRENT_LOG_FILE = PIPELINE_LOG_DIR / f"{now_str}_{executor}_{model}_{translation}_{book_code}.log"

    commands = {
        "status": status_cmd,
        "claim": claim_cmd,
        "get-chapter": get_chapter_cmd,
        "save-chapter": save_chapter_cmd,
        "complete-pass": complete_pass_cmd,
        "next-task": next_task_cmd,
        "bootstrap-log": bootstrap_log_cmd,
        "log-interaction": log_interaction_cmd,
        "cleanup-workspace": cleanup_workspace_cmd,
        "get-chapter-count": get_chapter_count_cmd,
        "verify-book": verify_book_cmd,
        "update-checkpoint-row": update_checkpoint_row_cmd,
        "truncate-sdf-chapter": truncate_sdf_chapter_cmd,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)


if __name__ == "__main__":
    main()
