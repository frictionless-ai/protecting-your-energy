---
name: md-rewrite-guards
description: Compresses markdown documentation by deleting slop, with a script that verifies every change before it is written. Use when asked to tighten, deslop, shorten, or clean up markdown docs, or to remove AI-sounding filler from a README or a plan. The guard script decides what is applied; it refuses rewrites that insert words, reorder content, alter code blocks or tables, delete too much, or run against a file that changed underneath. Not for code comments, not for prose outside markdown, and not for making text evade AI detection.
---

# Markdown rewrite guards

You propose deletions. The script decides what is written.

You never edit the target file. You write a candidate to a sidecar path and hand both paths to the guard. It checks the candidate and performs the write itself, or refuses and leaves the file untouched.

## The loop, per file

Run these in order for each file. Do not pause between files — see "Run the batch without stopping".

**1. Score it.**

```
python3 <skill-directory>/scripts/guard.py --allow-root <authorized-document-root> --score-only --original <path>
```

Line 1 of stdout carries the verdict. `CLEAN` means the file is already fine: record it and move to the next file. Anything else means proceed to step 2. The command also writes a receipt recording the file's hash; you do not read the receipt.

**2. Write a candidate.**

Copy the file's text, remove what should go, and write the result to `<path>.candidate`. Nothing else. Two operations are permitted:

- **Delete a span of prose.** Whole sentences, clauses, redundant qualifiers, restated summaries.
- **Split one sentence into two.** You may add the terminal punctuation and the capital letter this requires.

Everything else is a violation the guard will catch, so there is no benefit to attempting it:

- Do not add a word that was not already there.
- Do not reorder anything — not sentences, not sections, not code blocks.
- Do not touch a fenced code block, table, YAML frontmatter, HTML comment, or heading. Their contents are frozen.
- Do not rephrase. If a sentence is bad and you cannot fix it by deleting, leave it.

**3. Apply it.**

```
python3 <skill-directory>/scripts/guard.py --allow-root <authorized-document-root> --original <path> --candidate <path>.candidate
```

Line 1 carries the verdict. Route on that word — see `references/verdicts.md` for the full table. The guard writes the file when it accepts, and backs it up first. It deletes the candidate either way.

## What to do with each verdict

- `ACCEPTED` — the file was rewritten. Record the reduction.
- `CLEAN` — nothing needed doing.
- `REJECTED` — record the check that failed and the value. Do not retry with a different candidate unless the failure was the compression floor and you left something obvious uncut. Never retry more than once per file.
- `STALE` — the file changed after scoring. Re-run from step 1.
- `UNSUPPORTED` — the file holds something the scanner will not parse, or is out of scope. Skip it.

## When the guard does not answer

If the command produces no status word — the script is missing, not executable, or it crashed — the verdict for that file is `unresolved`. Record it with the path and move on.

Do not read the file and judge it yourself. An assessment of whether a document "looks fine" is not a verdict, and reporting one as though the guard had spoken is the exact failure this tool exists to remove. Reporting nothing is better.

## Run the batch without stopping

Process every file in one pass and report at the end. Continue authorized files without unnecessary questions. If a file requires a material decision, retain its unresolved status and continue other authorized files. Host approval behavior depends on the current host.

If something genuinely needs a decision, finish the run, record the file as `unresolved`, and raise it in the summary.

## Report

One line per file, then a total:

```
docs/setup.md          ACCEPTED   -14%
docs/api.md            CLEAN
README.md              REJECTED   compression_ceiling achieved=0.61 maximum=0.35
notes/scratch.md       UNSUPPORTED  blockquote container at line 12
CHANGELOG.md           unresolved   guard produced no verdict

5 files: 1 accepted, 1 clean, 1 rejected, 1 unsupported, 1 unresolved
Backups: /tmp/md-rewrite-guards/run-20260901-0142/
```

Name the backup directory. It is the only undo.

## Scope

This skill edits markdown prose files named by the configured allowlist. It does not touch code comments, agent state (`.remember/`, `.mission/`, `.autoclaw/`, `.cursor/`), or anything under a content-addressed archive. The guard enforces this independently; the allowlist is not advisory.

The goal is documentation that reads as though a person wrote it tersely. It is not to make text evade AI-detection tools — detectors are unreliable in both directions, and model output may carry a provenance watermark regardless.
