# Verdicts

The guard reports one verdict per file. The verdict is the **first word on line 1 of stdout**. Exit status reports whether the guard ran, not what it decided.

## The status words

| Word | Meaning | File on disk afterwards |
|---|---|---|
| `CLEAN` | Scored at or below the tell threshold. No rewrite was attempted. | Unchanged |
| `PROCEED` | Scored above the threshold. Phase 1 only — write a candidate and call the guard again. | Unchanged |
| `ACCEPTED` | Every check passed. | Replaced, backup written — unless `applied=false` |
| `REJECTED` | A check failed. Line 1 names the check and the measured value. | Unchanged |
| `STALE` | The original changed after it was scored. | Unchanged |
| `UNSUPPORTED` | The scanner refuses the file, or the path is out of scope. | Unchanged |

`PROCEED` is a phase-1 signal rather than one of the five per-file verdicts. Treat anything other than `CLEAN` from `--score-only` as "write a candidate."

A further verdict, `unresolved`, is never emitted by the script. The **skill** records it when the guard produced no status word — see "When the guard does not answer."

## Exit status

- `0` — the guard ran and reached a verdict. **Any** word above, including a rejection. A rejection is a successful run.
- non-zero — the guard did not reach a verdict: usage error, unhandled failure, or a backup that could not be written or verified.

Exit status is not the verdict channel. Exit `1` is also what an unhandled exception produces, so treating it as "rejected" would conflate a working refusal with a crash. Route on the word.

## Rejections

Line 1 carries the check that failed and the value that failed it.

```
REJECTED  compression_floor achieved=0.04 required=0.10
REJECTED  compression_ceiling achieved=0.63 maximum=0.35
REJECTED  delete_only inserted_token="seamlessly"
REJECTED  region_mismatch first_boundary_index=3
REJECTED  missing_candidate
REJECTED  missing_receipt
REJECTED  unusable_receipt
REJECTED  receipt_mismatch
```

**`region_mismatch` covers two different conditions**, and the index means the same thing in both:

- the frozen-region sequences diverged at that index — an altered, deleted, or added block;
- prose crossed a frozen boundary at that index — content was relocated past a block while the regions themselves stayed equal.

It is a boundary index, not "the region that changed." Reading it the second way makes the relocation message false.

## Refusals

```
UNSUPPORTED  blockquote line=12
UNSUPPORTED  unterminated_fence line=41
UNSUPPORTED  utf8_decode line=0
UNSUPPORTED  missing_target
UNSUPPORTED  not_allowlisted
UNSUPPORTED  no_allowlist
UNSUPPORTED  not_a_file
```

The reason is the scanner's own word, passed through unrenamed.

**Known limitation:** a CRLF document containing a fenced code block is refused as `unterminated_fence`, because the closing-fence pattern anchors at end-of-line. CRLF headings, tables, and lists scan normally. Refusing is the safe direction, so this is left as-is — but a well-formed CRLF file can be rejected.

## When the guard does not answer

If no status word comes back — the script is missing, not executable, it crashed, or a backup failed — the verdict for that file is `unresolved`.

Record it and move to the next file. Do not inspect the file by reading it and form a judgment; that is the failure this tool exists to remove. A prose assessment of whether a document "looks fine" is not a verdict, and presenting one as if it were is worse than reporting nothing.

Report `unresolved` in the run summary with the path attempted.

## Bounds

The compression floor and ceiling are configuration, not constants. **Both ship unset.**

- Floor: **not calibrated.**
- Ceiling: **not calibrated.**

While either is unset the guard runs in dry-run: it reaches a verdict and writes nothing, appending `applied=false` to an `ACCEPTED` line. Pass both explicitly to enable writes.

The `0.10` / `0.35` pair appearing in the test suite is a test-local value chosen to make fixtures discriminate. It is not a calibrated default and must not be adopted as one. Calibration means measuring achieved reduction across real documents and setting the floor below the useful range and the ceiling above it — the ceiling exists because an unbounded guard set accepts aggressive deletions and rejects conservative ones, which is the failure mode this tool was redesigned to prevent.
