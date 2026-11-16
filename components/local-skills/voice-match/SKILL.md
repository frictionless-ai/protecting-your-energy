---
name: voice-match
description: Edit existing prose for clarity and, when requested, an evidenced author voice. Keep personal writing samples and voice profiles in configured private locations.
---

# Voice match

Recover the author, audience, purpose, allowed edits and source-backed meaning. Apply [jurisdiction](jurisdiction.md) and [transform guards](forbidden-transforms.md).

Use ordinary clarity editing when no author profile is available. For voice matching, recover authorized examples from the current task or a configured private profile. `PYE_VOICE_PROFILE_DIR` can point to that private directory. Its optional `voice-spec.md`, `registers.md` and `voice-bank.md` remain outside the distributable plugin.

1. Inspect the text and its contract. Preserve source facts, uncertainty, disagreements and consequential detail.
2. Run the optional read-only diagnostic helper, `python3 <skill-root>/scripts/score.py --json FILE`. Supply `--profile PATH` for explicitly configured JSON style budgets.
3. Review failing spans against the actual request and authentic examples. Numerical budgets are editing aids.
4. Rewrite only the spans requiring change. Preserve code, tables, frontmatter and machine-consumed contracts unless the user authorizes their modification.
5. Compare meaning and evidence, then rerun the selected diagnostic. Explain any material limit in the result.

The helper reports `UNPROFILED` when no JSON style profile was supplied. A budget pass cannot establish authentic authorship. The [example configuration](profile.example.json) provides empty fields to fill with evidenced preferences.

For an optional authenticated Idiolect service, follow [the integration reference](references/idiolect-mcp.md) and current source-upload permissions. Local profile access does not authorize sending it to an external service.

Code-comment work follows its requested scope. Remove comments that merely restate code when appropriate. Preserve explanations that help a later reader understand a consequential decision.

When the user requests new prose, use write-as-me. Apply a repository-history workflow only when that separate action is authorized. Editing a document does not itself authorize rewriting Git history.
