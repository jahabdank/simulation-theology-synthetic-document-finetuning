# Simulation Theology — Synthetic Document Finetuning

This repo contains the Python CLI pipeline for converting Bible translations into Simulation Theology (ST) scripture.

## Repo Layout

Run Claude Code from **this directory** (`simulation-theology-synthetic-document-finetuning/`).

| Directory | Relative Path | Contents |
|-----------|--------------|----------|
| Pipeline code (this repo) | `.` | `code/st_pipeline_mngr.py`, `code/st_chapter_runner.py`, prompts |
| eBible corpus | `../ebible/` | Source Bible translations (`corpus/*.txt`) and `metadata/vref.txt` |
| ST corpus | `../simulation-theology-corpus/` | Core theology docs (axioms, translation guide) |
| Training data output | `../simulation-theology-training-data/` | SDF output, checkpoints, Q&D dilemmas, agent logs, drafts |

All Python scripts resolve paths from `__file__`, so sibling directories are accessed via absolute paths internally.

## Automated Workflow

Use the skill to run the full conversion pipeline:

```
/convert-bible-to-st-automated [executor-name] [model-name]
```

Example:
```
/convert-bible-to-st-automated claude-code claude-opus-4
```

The pipeline is CLI-driven: each command prints a `▶ NEXT STEPS` block telling you exactly what to run next.

### Parallelized (multi-agent) variant

To run **multiple agents concurrently** on different books:

```
/convert-bible-to-st-automated-parallelized [executor-name] [model-name]
```

This uses `claim --parallel` to prevent two agents from claiming the same book. Launch in multiple Claude Code sessions simultaneously.
