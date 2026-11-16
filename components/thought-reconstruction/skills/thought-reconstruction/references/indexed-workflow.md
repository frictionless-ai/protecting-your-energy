---
name: thought-reconstruction
description: Reclaim an idea from earlier conversations and notes, recover its reasoning and intended behavior, and continue it in the owner's voice with traceable evidence. Use when asked to reclaim, recover, resume or finish a scattered thought.
---

# Thought Reconstruction

Recover what the person was trying to express. Preserve the evidence and changes
over time. Judge the artifact, never the person. Read this project's README and
the selected configuration before accessing sources.

## Reclaim an idea

An ordinary request such as "Reclaim my notes app idea" is enough. Infer the
specific idea and retrieve the missing context yourself. Current instructions
and corrections take precedence over historical patterns. Read
[the bundled reclamation workflow](../../../../thought-reconstruction-engine/docs/reclaim-workflow.md) for the retrieval and
writing procedure. It uses the current agent to reconstruct and continue the
idea; the CLI prepares evidence rather than claiming to infer a complete mind.

Use `thought-reconstruction reclaim TEXT --query FACET` to prepare a private
packet without rebuilding the library or making a provider call. Shared local
dense retrieval is the default primary route; the packet reports actual index
coverage and hydrates bounded original parents with hash/version checks. It
continues when the saved library is unavailable, and resolves truncated unit
parent metadata through the pinned generation before text hydration. The
saved library BM25 is a lexical supplement. Read `discovery_retrieval` and
`discovery_originals` first, expand all relevant parent locators and unfinished
exchanges, and repair retrieval failures before treating silence as absence.
Use helper status and the packet's dense scope to identify the published
generation's source families and dates. Investigate relevant sources outside
that scope separately, and freshly hydrate originals using the query's pinned
generation. Repeat `--query` for different parts of the idea. Explicit new inputs
use `--source PATH`; `--owner-source PATH` records an operator's authorship assertion for
otherwise unattributed notes. Inspect copied AI prose and quoted dialogue at
fragment level; note ownership is not original authorship. Semantic search yields leads that must
be resolved to their originals. Read the packet and the surrounding sources,
then produce the usable continuation. Delivering the packet alone is unfinished.

When asked to rediscover or when understanding is challenged, begin with the
original exchanges rather than loading a prior owner profile to frame them.
Trace the reasons, changed conditions and outcomes; keep interpretations that
challenge the current account. Recheck that account against new episodes during
the work, and revise it for an observed discrepancy. Begin building when the
evidence supports a useful increment. Keep investigating
relevant conversations during the build and incorporate newly supported design
requirements. For substantial work, a source investigator can run alongside
the builder. Preserve dated changes and the remaining investigation scope.

Lead with the recovered idea and move it forward. Preserve its motivation,
feel, behavior, constraints and meaningful changes. Ground the voice in the
owner's relevant writing and present self-description. Historical brainstorming
can express a desired experience before specifying an implementation. Keep
proposed technical mechanisms revisable while preserving that experience.

Use the owner's narrative as the main interpretive context. Treat peer reactions
as evidence about the interaction and possible communication constraints.
Preserve disagreements without inventing motives or claiming consensus. Protect
credibility through exact attribution, defensible claims and visible uncertainty.

Write confidently where the record supports the meaning. Make inferred bridges
and new suggestions distinguishable from recovered thinking. Ask only for a
missing decision that materially blocks the next action. Usually return the
draft and one next step, with evidence in the private artifact.

## Maintain the library

1. Run `thought-reconstruction verify` to check the current library. If the
   source files changed or no library exists, use `rebuild`. Source or output
   changes belong in the private configuration, not in application code.
2. Use `query TEXT` to locate candidates. Read their exact fragments and relevant
   context from the configured source. Unknown speakers and derived paraphrases
   are not the owner's verbatim evidence. Captured quotes are identified as such.
3. Reconstruct a specific thought, not a whole topic. Select exact fragment keys
   in the private reviews file. Retain uncertainty, genuine contradictions and
   later cost judgments. Do not infer abandonment merely from silence or age.
4. State the next action, acceptance conditions, open questions and a critique.
   Include eight dimensions only as explicit estimates. Zero research confidence
   means the claim has not been independently researched; zero originality is
   unassessed, not a judgment of the person's originality.
5. For implementation questions, use configured local repository research.
   Search results are code leads. Working behavior requires stronger evidence.
   Label missing evidence unknown; never automatically call it unimplemented.
6. Rebuild and verify. The canvas defaults to reviewed thoughts, retains the
   wider candidate collection and downloads the same private task brief as the CLI.

## Boundaries

Raw sources are read-only. Application files and output stay outside the archive.
The operational library is offline unless explicit `semantic.provider=claude`
configuration enables bounded hosted reconstruction. The user authorized and
prefers hosted processing on 2026-09-27. Keep project scope, per-request limits,
tool-disabled isolated calls, private receipts and exact local evidence checks.
Hosted output remains a candidate until evidence-reviewed. The legacy
CLI's `--hosted-llm` explicitly sends selected material to a hosted provider and
requires authorization for that transmission. Do not invoke it under a local-only
expectation. No auto-posting, sending, background collection or global hooks.

Retain previous runs. Never silently replace evidence or use a generated sample
when real data is missing. A schema pass does not prove useful reconstruction;
inspect actual output against the user's intended use and report coverage limits.

## Implementation reference

Follow the minimal-code approach and thin-adapter structure of
DietrichGebert/ponytail. See `docs/ponytail-reference.md` for the pinned comparison.
Reuse the current Python engine and native HTML controls; avoid parallel engines,
duplicate output formatters and host-specific copies of this workflow.
