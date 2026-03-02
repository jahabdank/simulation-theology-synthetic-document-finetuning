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
TMP_DIR = DATA_DIR / "tmp"


def log_message(msg):
    print(msg)


def sanitize_name(name):
    """
    Standardizes names for file paths and identifiers.
    """
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
    
    # Strip hypothetical language prefix for mapping check
    lookup_key = t[4:] if t.startswith("eng-") else t
    res = mapping.get(lookup_key, translation)
    
    # Ensure prefix if missing
    if "-" not in res:
        res = f"eng-{res}"

    # Verify exact casing by matching against the corpus directory
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


def status_cmd(args):
    """
    Scans checkpoints and ebible corpus to suggest the next action.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = args.translation
    resolved_translation = resolve_translation(translation)

    # Get available books for the translation
    trans_file = EBIBLE_CORPUS / f"{resolved_translation}.txt"
    if not trans_file.exists():
        log_message(f"Error: Translation file {trans_file} not found.")
        return

    vrefs = parse_vref()
    available_books = []
    for ref in vrefs:
        if not ref:
            continue
        book = ref.split(" ")[0]
        if book not in available_books:
            available_books.append(book)

    # Scan checkpoints
    checkpoints = list(SDF_CHECKPOINTS_DIR.glob(f"{executor}_{model}_{translation}_*.md"))
    
    abandoned = []
    completed = []
    in_progress = []
    
    now = datetime.datetime.now(datetime.timezone.utc)

    for cp in checkpoints:
        try:
            with open(cp, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
            if match:
                meta = yaml.safe_load(match.group(1))
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
    log_message(f"Completed books: {len(completed)}")
    log_message(f"In-progress (active) books: {len(in_progress)}")
    log_message(f"Abandoned books: {len(abandoned)}")
    
    if abandoned:
        log_message("\nRECOMMENDATION: Recover an abandoned book.")
        log_message(f"Book to recover: {abandoned[0]}")
    else:
        # Find first unclaimed book in canonical order
        unclaimed = [b for b in available_books if b not in completed and b not in in_progress and b not in abandoned]
        if unclaimed:
            log_message("\nRECOMMENDATION: Claim a new book.")
            log_message(f"Next unclaimed book: {unclaimed[0]}")
        else:
            log_message("\nRECOMMENDATION: No books left to process for this translation!")


def claim_cmd(args):
    """
    Claims a new book or recovers an abandoned one.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    
    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    agent_host = os.uname().nodename if hasattr(os, "uname") else "unknown"
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    
    starting_chapter = 1

    if cp_file.exists():
        # Recovery
        log_message(f"Recovering checkpoint {cp_file.name}...")
        with open(cp_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse YAML
        match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
        if match:
            meta = yaml.safe_load(match.group(1))
            meta["last_updated_at"] = now_iso
            meta["agent_host"] = agent_host
            
            # Find last completed chapter
            table_lines = [line for line in content.split("\n") if "|" in line]
            last_chapter = 0
            for line in table_lines:
                ch_match = re.search(r"CHAPTER (\d+) COMPLETE", line)
                if ch_match:
                    last_chapter = int(ch_match.group(1))
            
            starting_chapter = last_chapter + 1
            log_message(f"Last complete chapter was {last_chapter}. Starting from {starting_chapter}.")
            
            # Write back updated meta and recovery log
            new_yaml = yaml.dump(meta, sort_keys=False)
            new_content = content.replace(match.group(1), new_yaml.strip() + "\n")
            recovery_log = f"| `{now_iso}` | `RECOVERED` | `/convert` | Dropped partial chapter {starting_chapter}. Resuming from chapter {starting_chapter}. |\n"
            new_content += recovery_log
            
            with open(cp_file, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            # Truncate SDF and Q&D files
            # This is complex to do robustly with plain text, we will let the agent know
            log_message("WARNING: Make sure to drop any partial SDF or Q&D data for the starting chapter!")
    else:
        # New Claim
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
            "agent_host": agent_host
        }
        
        yaml_str = yaml.dump(meta, sort_keys=False)
        content = f"---\n{yaml_str}---\n\n# Checkpoint: {executor} - {model} - {translation} - {book_code}\n\n"
        content += "| Timestamp | Status | Set By | Details & Metrics |\n"
        content += "|-----------|--------|--------|-------------------|\n"
        content += f"| `{now_iso}` | `STARTED` | `/convert` | Claimed by agent on {agent_host} |\n"
        
        SDF_CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(cp_file, "w", encoding="utf-8") as f:
            f.write(content)
            
    log_message(f"Claim successful. You should start from Chapter {starting_chapter}.")


def get_chapter_cmd(args):
    """
    Extracts a specific chapter from the ebible corpus and initializes the workspace limits.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    resolved_translation = translation
    book_code = args.book_code.upper()
    chapter = args.chapter
    
    trans_file = EBIBLE_CORPUS / f"{resolved_translation}.txt"
    if not trans_file.exists():
        log_message(f"Error: Translation file {trans_file} not found.")
        return

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

    if chapter_text:
        text_out = "\n".join(chapter_text)
        
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        raw_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_raw.txt"
        st_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_st_text.md"
        qd_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_qd_text.md"
        
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write(text_out)
        with open(st_file, "w", encoding="utf-8") as f:
            f.write("")
        with open(qd_file, "w", encoding="utf-8") as f:
            f.write("")
            
        log_message("=== BEGIN SOURCE TEXT ===")
        log_message(text_out)
        log_message("=== END SOURCE TEXT ===")
        log_message("\n=== WORKSPACE INITIALIZED ===")
        log_message(f"Raw Text Saved: {raw_file}")
        log_message(f"Write ST Here: {st_file}")
        log_message(f"Write QD Here: {qd_file}")
    else:
        log_message(f"Chapter {chapter} not found in {book_code}.")


def save_chapter_cmd(args):
    """
    Saves the translated chapter and Q&D items, updates checkpoint.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    chapter = args.chapter
    
    st_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_st_text.md"
    qd_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_qd_text.md"
    raw_file = TMP_DIR / f"{executor}_{model}_{book_code}_ch{chapter}_raw.txt"
    
    if not st_file.exists():
        log_message(f"Error: ST file {st_file} not found. Did you write to the correct workspace path?")
        return
    
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    now_date = datetime.datetime.now().strftime("%Y%m%d")

    # SDF Output
    sdf_out_subdir = SDF_OUT_DIR / f"{translation}_{model}_{executor}"
    sdf_out_subdir.mkdir(parents=True, exist_ok=True)
    sdf_file = sdf_out_subdir / f"{book_code}.md"
    
    with open(st_file, "r", encoding="utf-8") as f:
        st_text = f.read()
        
    word_count = len(st_text.split())

    if not sdf_file.exists() or chapter == 1:
        # Create with YAML
        frontmatter = f"""---
source_religion: Christianity
source_tradition: Protestant
source_book_code: {book_code}
source_translation_file: {resolve_translation(translation)}.txt
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

    # Q&D Output
    qd_count = 0
    if qd_file.exists():
        qd_file_out = QD_OUT_DIR / f"{now_date}_{executor}_{model}_{translation}_{book_code}.md"
        with open(qd_file, "r", encoding="utf-8") as f:
            qd_text = f.read()
            if qd_text.strip():
                QD_OUT_DIR.mkdir(parents=True, exist_ok=True)
                qd_count = qd_text.count("### Q")
                with open(qd_file_out, "a", encoding="utf-8") as fout:
                    fout.write(qd_text + "\n\n")
                    
    # Update checkpoint
    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if not cp_file.exists():
        log_message(f"FATAL: Checkpoint file {cp_file} not found! You must run 'claim' before 'save-chapter'.")
        sys.exit(1)

    with open(cp_file, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
    if match:
        meta = yaml.safe_load(match.group(1))
        meta["last_updated_at"] = now_iso
        
        new_yaml = yaml.dump(meta, sort_keys=False)
        new_content = content.replace(match.group(1), new_yaml.strip() + "\n")
        
        tokens_in = args.tokens_in if args.tokens_in else "?"
        tokens_out = args.tokens_out if args.tokens_out else "?"
        
        log_entry = f"| `{now_iso}` | `CHAPTER {chapter} COMPLETE` | `/convert` | Wrote {word_count} words. Added {qd_count} Q&D items. Tokens: {tokens_in}/{tokens_out}. |\n"
        new_content += log_entry
        
        with open(cp_file, "w", encoding="utf-8") as f:
            f.write(new_content)
                
    # Cleanup workspace
    if st_file.exists():
        st_file.unlink()
    if qd_file.exists():
        qd_file.unlink()
    if raw_file.exists():
        raw_file.unlink()
                
    log_message(f"Chapter {chapter} saved and workspace cleaned successfully.")

def complete_pass_cmd(args):
    """
    Marks the first pass as complete in the checkpoint.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()
    total_chapters = args.total_chapters
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    
    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if cp_file.exists():
        with open(cp_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
        if match:
            meta = yaml.safe_load(match.group(1))
            meta["last_updated_at"] = now_iso
            meta["status"] = "COMPLETED"
            
            new_yaml = yaml.dump(meta, sort_keys=False)
            new_content = content.replace(match.group(1), new_yaml.strip() + "\n")
            
            new_content += f"| `{now_iso}` | `FIRST_PASS_COMPLETE` | `/convert` | Total chapters: {total_chapters}. |\n"
            new_content += f"| `{now_iso}` | `QD_CREATED` | `/convert` | Saved Q&D file with dilemmas. |\n"
            
            with open(cp_file, "w", encoding="utf-8") as f:
                f.write(new_content)
    log_message("Pass completed successfully.")

def check_status_for_translation(executor, model, translation):
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
    
    abandoned = []
    completed = []
    in_progress = []
    
    now = datetime.datetime.now(datetime.timezone.utc)

    for cp in checkpoints:
        try:
            with open(cp, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
            if match:
                meta = yaml.safe_load(match.group(1))
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
                log_message(f"=== Next Task Found ===")
                log_message(f"TRANSLATION={translation}")
                log_message(f"BOOK_CODE={book}")
                log_message(f"ACTION={action}")
                return
                
    log_message("=== Next Task Found ===")
    log_message("STATUS=COMPLETE")
    log_message("No more books or translations available in the corpus!")
    
def bootstrap_log_cmd(args):
    """
    Bootstraps the agent log directory and reads previous context.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    log_dir = AGENT_LOG_DIR / f"{executor}_{model}"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_files = sorted(list(log_dir.glob("*.md")))
    log_message(f"=== Agent Logging Bootstrap ===")
    log_message(f"Agent Name: {executor}")
    log_message(f"Found {len(log_files)} past session logs.")
    
    if log_files:
        log_message("Reading the most recent log file for context...")
        with open(log_files[-1], "r", encoding="utf-8") as f:
            log_message(f.read())
    else:
        log_message("This is a fresh session. No prior logs exist.")
        
def log_interaction_cmd(args):
    """
    Appends an interaction log to the daily agent log file.
    """
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
    """
    Removes lingering temporary workspace files for an executor/model.
    """
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
    
    log_message(f"Cleanup complete for {executor}/{model}.")


def get_chapter_count_cmd(args):
    """
    Returns the total number of chapters for a given book in a translation.
    This gives the agent a deterministic loop bound.
    """
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()

    trans_file = EBIBLE_CORPUS / f"{translation}.txt"
    if not trans_file.exists():
        log_message(f"Error: Translation file {trans_file} not found.")
        sys.exit(1)

    vrefs = parse_vref()
    chapters = set()
    for ref in vrefs:
        if not ref:
            continue
        parts = ref.split(" ")
        if len(parts) >= 2 and parts[0] == book_code:
            ch = parts[1].split(":")[0]
            chapters.add(int(ch))

    if not chapters:
        log_message(f"Error: No chapters found for {book_code} in {translation}.")
        sys.exit(1)

    total = max(chapters)
    log_message(f"TOTAL_CHAPTERS={total}")
    log_message(f"Book {book_code} in {translation} has {total} chapters.")


def verify_book_cmd(args):
    """
    Post-completion integrity check. Compares checkpoint chapter rows
    against actual SDF file content. Reports mismatches.
    """
    executor = sanitize_name(args.executor)
    model = sanitize_name(args.model)
    translation = resolve_translation(args.translation)
    book_code = args.book_code.upper()

    errors = []

    # 1. Check checkpoint exists
    cp_file = SDF_CHECKPOINTS_DIR / f"{executor}_{model}_{translation}_{book_code}.md"
    if not cp_file.exists():
        errors.append(f"MISSING CHECKPOINT: {cp_file.name}")
    else:
        with open(cp_file, "r", encoding="utf-8") as f:
            cp_content = f.read()
        # Count checkpoint chapter rows
        cp_chapters = re.findall(r"CHAPTER (\d+) COMPLETE", cp_content)
        cp_chapter_set = set(int(c) for c in cp_chapters)

    # 2. Check SDF file exists
    sdf_subdir = SDF_OUT_DIR / f"{translation}_{model}_{executor}"
    sdf_file = sdf_subdir / f"{book_code}.md"
    if not sdf_file.exists():
        errors.append(f"MISSING SDF FILE: {sdf_file}")
    else:
        with open(sdf_file, "r", encoding="utf-8") as f:
            sdf_content = f.read()
        # Find all unique chapter numbers in SDF (format: BOOK CH:VERSE)
        sdf_chapters = set()
        for m in re.finditer(rf"^{re.escape(book_code)} (\d+):\d+:", sdf_content, re.MULTILINE):
            sdf_chapters.add(int(m.group(1)))

    # 3. Get expected chapter count from vref
    vrefs = parse_vref()
    expected_chapters = set()
    for ref in vrefs:
        if not ref:
            continue
        parts = ref.split(" ")
        if len(parts) >= 2 and parts[0] == book_code:
            expected_chapters.add(int(parts[1].split(":")[0]))

    total_expected = max(expected_chapters) if expected_chapters else 0

    # 4. Cross-check
    if not errors:  # only if both files exist
        missing_in_cp = sdf_chapters - cp_chapter_set
        missing_in_sdf = cp_chapter_set - sdf_chapters
        missing_entirely = expected_chapters - sdf_chapters

        if missing_in_cp:
            errors.append(f"CHAPTERS IN SDF BUT NOT IN CHECKPOINT: {sorted(missing_in_cp)}")
        if missing_in_sdf:
            errors.append(f"CHAPTERS IN CHECKPOINT BUT NOT IN SDF: {sorted(missing_in_sdf)}")
        if missing_entirely:
            errors.append(f"CHAPTERS MISSING FROM SDF (vs vref): {sorted(missing_entirely)}")

    # Report
    log_message(f"=== Verify Book: {book_code} ===")
    log_message(f"Expected chapters: {total_expected}")
    if not errors:
        checkpoint_count = len(cp_chapter_set) if cp_file.exists() else 0
        sdf_count = len(sdf_chapters) if sdf_file.exists() else 0
        log_message(f"Checkpoint rows: {checkpoint_count}")
        log_message(f"SDF chapters: {sdf_count}")
        log_message("RESULT=PASS")
    else:
        for e in errors:
            log_message(f"ERROR: {e}")
        log_message("RESULT=FAIL")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="ST Pipeline Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    parser_status = subparsers.add_parser("status", help="Get pipeline status")
    parser_status.add_argument("--executor", required=True)
    parser_status.add_argument("--model", required=True)
    parser_status.add_argument("--translation", required=True)

    # claim
    parser_claim = subparsers.add_parser("claim", help="Claim or recover a book")
    parser_claim.add_argument("--executor", required=True)
    parser_claim.add_argument("--model", required=True)
    parser_claim.add_argument("--translation", required=True)
    parser_claim.add_argument("--book_code", required=True)
    parser_claim.add_argument("--corpus_version", required=True)
    parser_claim.add_argument("--pipeline_version", required=True, help="Git hash of the execution pipeline")
    
    # get-chapter
    parser_gc = subparsers.add_parser("get-chapter", help="Get text for a chapter")
    parser_gc.add_argument("--executor", required=True)
    parser_gc.add_argument("--model", required=True)
    parser_gc.add_argument("--translation", required=True)
    parser_gc.add_argument("--book_code", required=True)
    parser_gc.add_argument("--chapter", type=int, required=True)

    # save-chapter
    parser_sc = subparsers.add_parser("save-chapter", help="Save translated text from workspace")
    parser_sc.add_argument("--executor", required=True)
    parser_sc.add_argument("--model", required=True)
    parser_sc.add_argument("--translation", required=True)
    parser_sc.add_argument("--book_code", required=True)
    parser_sc.add_argument("--chapter", type=int, required=True)
    parser_sc.add_argument("--tokens_in", required=False)
    parser_sc.add_argument("--tokens_out", required=False)
    
    # complete-pass
    parser_cp = subparsers.add_parser("complete-pass", help="Mark pass as complete")
    parser_cp.add_argument("--executor", required=True)
    parser_cp.add_argument("--model", required=True)
    parser_cp.add_argument("--translation", required=True)
    parser_cp.add_argument("--book_code", required=True)
    parser_cp.add_argument("--total_chapters", type=int, required=True)

    # bootstrap-log
    parser_bl = subparsers.add_parser("bootstrap-log", help="Bootstrap agent logging")
    parser_bl.add_argument("--executor", required=True)
    parser_bl.add_argument("--model", required=True)
    
    # next-task
    parser_nt = subparsers.add_parser("next-task", help="Find the next best book and translation")
    parser_nt.add_argument("--executor", required=True)
    parser_nt.add_argument("--model", required=True)
    
    # log-interaction
    parser_li = subparsers.add_parser("log-interaction", help="Log an interaction")
    parser_li.add_argument("--executor", required=True)
    parser_li.add_argument("--model", required=True)
    parser_li.add_argument("--prompt", required=True)
    parser_li.add_argument("--task", required=True)
    parser_li.add_argument("--action", required=True)

    # cleanup-workspace
    parser_cw = subparsers.add_parser("cleanup-workspace", help="Cleanup lingering workspace files")
    parser_cw.add_argument("--executor", required=True)
    parser_cw.add_argument("--model", required=True)

    # get-chapter-count
    parser_gcc = subparsers.add_parser("get-chapter-count", help="Get the total number of chapters for a book")
    parser_gcc.add_argument("--translation", required=True)
    parser_gcc.add_argument("--book_code", required=True)

    # verify-book
    parser_vb = subparsers.add_parser("verify-book", help="Verify checkpoint and SDF integrity for a book")
    parser_vb.add_argument("--executor", required=True)
    parser_vb.add_argument("--model", required=True)
    parser_vb.add_argument("--translation", required=True)
    parser_vb.add_argument("--book_code", required=True)

    args = parser.parse_args()

    if args.command == "status":
        status_cmd(args)
    elif args.command == "claim":
        claim_cmd(args)
    elif args.command == "get-chapter":
        get_chapter_cmd(args)
    elif args.command == "save-chapter":
        save_chapter_cmd(args)
    elif args.command == "complete-pass":
        complete_pass_cmd(args)
    elif args.command == "next-task":
        next_task_cmd(args)
    elif args.command == "bootstrap-log":
        bootstrap_log_cmd(args)
    elif args.command == "log-interaction":
        log_interaction_cmd(args)
    elif args.command == "cleanup-workspace":
        cleanup_workspace_cmd(args)
    elif args.command == "get-chapter-count":
        get_chapter_count_cmd(args)
    elif args.command == "verify-book":
        verify_book_cmd(args)

if __name__ == "__main__":
    main()
