#!/usr/bin/env python3
"""
Chapter Runner — Minimal-prompt orchestrator for agentic ST conversion.

Prevents context drift by re-injecting the correct file paths, source text,
and save command at EVERY chapter boundary. Designed to be called by the
agent instead of raw get-chapter / save-chapter commands.

Usage:
    python3 code/st_chapter_runner.py get \
        --executor "antigravity" --model "gemini 3 flash" \
        --translation "eng-engBBE" --book_code "GEN" --chapter 18

    python3 code/st_chapter_runner.py save \
        --executor "antigravity" --model "gemini 3 flash" \
        --translation "eng-engBBE" --book_code "GEN" --chapter 18

The 'get' command outputs ONLY:
  1. Source text
  2. Creative instructions
  3. EXACT file paths to write to
  4. EXACT save command to run next

The 'save' command:
  1. Auto-recovers misplaced files
  2. Saves the chapter
  3. Outputs the EXACT next 'get' command (or completion message)
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

# --- Paths (must match st_pipeline_mngr.py) ---
ROOT_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT_DIR.parent / "simulation-theology-training-data"
TMP_DIR = DATA_DIR / "drafts"
PIPELINE_SCRIPT = ROOT_DIR / "code" / "st_pipeline_mngr.py"
RUNNER_SCRIPT = ROOT_DIR / "code" / "st_chapter_runner.py"


def sanitize_name(name):
    return name.lower().strip().replace(" ", "-").replace("!", "").replace("_", "-")


def run_pipeline_cmd(cmd_args: list) -> str:
    """Run st_pipeline_mngr.py and capture output."""
    full_cmd = [sys.executable, str(PIPELINE_SCRIPT)] + cmd_args
    result = subprocess.run(
        full_cmd,
        capture_output=True, text=True,
        cwd=str(ROOT_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    combined = result.stdout
    if result.stderr:
        combined += "\n" + result.stderr
    if result.returncode != 0:
        print(f"⚠ Pipeline command exited with code {result.returncode}")
    return combined


def get_cmd(args):
    """
    Fetch a chapter and emit a MINIMAL prompt with exact paths.

    This replaces the raw 'get-chapter' call in the workflow.
    The output is deliberately short to minimize context burden
    on the agent.
    """
    executor = args.executor
    model = args.model
    translation = args.translation
    book_code = args.book_code.upper()
    chapter = args.chapter

    executor_slug = sanitize_name(executor)
    model_slug = sanitize_name(model)

    # Call get-chapter internally
    output = run_pipeline_cmd([
        "get-chapter",
        "--executor", executor,
        "--model", model,
        "--translation", translation,
        "--book_code", book_code,
        "--chapter", str(chapter),
    ])

    # Extract source text from the pipeline output
    source_text = ""
    in_source = False
    for line in output.split("\n"):
        # Strip log timestamp prefix if present
        clean = line
        if "] " in clean and clean.startswith("["):
            clean = clean.split("] ", 1)[1]

        if "=== BEGIN SOURCE TEXT ===" in clean:
            in_source = True
            continue
        elif "=== END SOURCE TEXT ===" in clean:
            in_source = False
            continue
        if in_source:
            source_text += clean + "\n"

    if not source_text.strip():
        print("⚠ ERROR: Could not extract source text from get-chapter output.")
        print("Raw output follows:")
        print(output)
        sys.exit(1)

    # Compute exact file paths
    st_file = TMP_DIR / f"{executor_slug}_{model_slug}_{book_code}_ch{chapter}_st_text.md"
    qd_file = TMP_DIR / f"{executor_slug}_{model_slug}_{book_code}_ch{chapter}_qd_text.md"

    # Emit MINIMAL prompt — only what the agent needs
    print("╔══════════════════════════════════════════════════════╗")
    print(f"║  CHAPTER {chapter} — {book_code}                          ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    print("=== SOURCE TEXT ===")
    print(source_text.strip())
    print("=== END SOURCE TEXT ===")
    print()

    # Extract and print creative instructions (from the pipeline output)
    in_creative = False
    creative_block = []
    for line in output.split("\n"):
        clean = line
        if "] " in clean and clean.startswith("["):
            clean = clean.split("] ", 1)[1]

        if "── CREATIVE TASK" in clean:
            in_creative = True
        elif "── Q&D FORMAT" in clean:
            in_creative = False
            # Also capture Q&D format
            creative_block.append(clean)
            continue
        elif "── END NEXT STEPS" in clean or "╔══" in clean:
            in_creative = False
            break
        if in_creative:
            creative_block.append(clean)

    # Re-print creative instructions in compact form
    for line in creative_block:
        if line.strip():
            print(line)

    print()
    print("┌─────────────────────────────────────────────────────┐")
    print("│                  ✏️  WRITE FILES                    │")
    print("├─────────────────────────────────────────────────────┤")
    print(f"│ ST file:  {st_file}")
    print(f"│ Q&D file: {qd_file}")
    print("└─────────────────────────────────────────────────────┘")
    print()
    print("After writing BOTH files, run this EXACT command:")
    print("```")
    print(f'python3 code/st_chapter_runner.py save --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{book_code}" --chapter {chapter}')
    print("```")
    print()
    print("⚠ CRITICAL: Write to the EXACT paths shown above. DO NOT change the directory.")
    print(f"⚠ The ST file must be at: {st_file}")


def save_cmd(args):
    """
    Save a chapter with misplaced-file recovery, then emit the next 'get' command.

    This replaces the raw 'save-chapter' call in the workflow.
    """
    executor = args.executor
    model = args.model
    translation = args.translation
    book_code = args.book_code.upper()
    chapter = args.chapter

    # Call save-chapter internally (which now includes misplaced-file recovery)
    output = run_pipeline_cmd([
        "save-chapter",
        "--executor", executor,
        "--model", model,
        "--translation", translation,
        "--book_code", book_code,
        "--chapter", str(chapter),
    ])

    # Print save results (filtered to key lines)
    for line in output.split("\n"):
        clean = line
        if "] " in clean and clean.startswith("["):
            clean = clean.split("] ", 1)[1]
        # Show important lines
        if any(kw in clean for kw in ["✅", "FATAL", "RECOVERED", "FSTRACE"]):
            print(clean)

    # Check if save succeeded
    if "FATAL" in output:
        print("⚠ Save failed! Check the output above.")
        sys.exit(1)

    # Determine if book is complete
    if "🏁 All" in output and "chapters complete" in output:
        print()
        print("╔══════════════════════════════════════════════╗")
        print("║         🏁 BOOK COMPLETE                     ║")
        print("╚══════════════════════════════════════════════╝")
        print()
        print("Run the integrity check:")
        print("```")
        print(f'python3 code/st_pipeline_mngr.py verify-book --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{book_code}"')
        print("```")
    else:
        next_chapter = chapter + 1
        print()
        print("╔══════════════════════════════════════════════╗")
        print(f"║   ▶ GET NEXT CHAPTER ({next_chapter})                      ║")
        print("╚══════════════════════════════════════════════╝")
        print()
        print("Run this EXACT command:")
        print("```")
        print(f'python3 code/st_chapter_runner.py get --executor "{executor}" --model "{model}" --translation "{translation}" --book_code "{book_code}" --chapter {next_chapter}')
        print("```")
        print()
        print("⚠ DO NOT re-run status, claim, save, or get-chapter-count.")


def main():
    parser = argparse.ArgumentParser(
        description="Chapter Runner — minimal-prompt orchestrator for ST conversion",
    )
    subparsers = parser.add_subparsers(dest="command")

    # 'get' subcommand
    get_parser = subparsers.add_parser("get", help="Fetch chapter and emit minimal prompt")
    get_parser.add_argument("--executor", required=True)
    get_parser.add_argument("--model", required=True)
    get_parser.add_argument("--translation", required=True)
    get_parser.add_argument("--book_code", required=True)
    get_parser.add_argument("--chapter", type=int, required=True)

    # 'save' subcommand
    save_parser = subparsers.add_parser("save", help="Save chapter with recovery, emit next command")
    save_parser.add_argument("--executor", required=True)
    save_parser.add_argument("--model", required=True)
    save_parser.add_argument("--translation", required=True)
    save_parser.add_argument("--book_code", required=True)
    save_parser.add_argument("--chapter", type=int, required=True)

    args = parser.parse_args()

    if args.command == "get":
        get_cmd(args)
    elif args.command == "save":
        save_cmd(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
