# Implementation notes — deviations from SKILLS.md Rev. 2

Everything not listed here is implemented as designed.

## Deviations

1. **Hook subagent detection is heuristic (§4 recursion guard).** The design
   calls for "top-level session detection". Hook payload field names for
   subagent sessions vary across Claude Code versions, so the script checks a
   permissive list (`agent_type`, `agent_name`, `parent_session_id`,
   `subagent`, `is_subagent`, `parent_tool_use_id`) plus two belt-and-braces
   guards: a `suppress-<session>` state file the skill/wrapper can create
   while uplift runs, and a marker-echo check (never re-mark text already
   containing `PROMPT_UPLIFT_CANDIDATE`). Adjust the field list to your
   harness version if needed; false positives here fail toward silence,
   which is the safe direction.

2. **Deterministic pre-screen lives inside the hook, not a separate
   `scripts/prescreen` (§3.2/§4).** The design sketched the mechanical
   pass-through checks as a skill-side script; since the hook must make the
   same checks anyway (to avoid marking protected turns), the single hook
   script is the one deterministic pre-screen. The skill re-applies the
   same classes judgmentally (routing.md) for turns that arrive without the
   hook.

3. **Opt-out persistence is session-scoped via flag file.** "Stop rewriting
   my prompts" is detected by a small deterministic phrase pattern in the
   hook and recorded as an *empty* flag file keyed by session id (no prompt
   text on disk). Cross-session ("from now on") persistence is left to the
   agent's memory system, as the design assigns durable preferences to the
   application layer; the hook cannot durably know a user across sessions.

4. **The prompt-engineer renderer ships as an optional agent definition,
   not `context: fork` in a skill (§3.4).** Claude Code's forked-context
   skill execution and custom-agent formats are both in flux; a standalone
   `agents/prompt-engineer.md` (installable into `.claude/agents/`) is the
   portable choice. The skill's inline fast path (portable-base template)
   is the default and is sufficient when the subagent is not installed —
   this slightly widens D3's "trivial contract" fast path by making it the
   fallback for all contracts in unconfigured installs.

5. **Trigger-calibration and invariant evals require manual model runs.**
   The scripts validate, split, and report on the corpora but do not call
   models — the design's run-loop (skill-creator §evaluation) assumes a
   `claude` CLI + credentials this repo should not embed. Methodology is
   fully documented in `evals/README.md`; `split_corpus.py` is the runnable
   part.

6. **Corpus texts are paraphrases, not dataset rows.** Per the privacy
   constraint, every case in `evals/trigger-corpus/corpus.json` and
   `evals/invariants/invariant-cases.json` is a paraphrased/genericized
   shape of messages observed in the mined dataset (usernames, hosts, paths,
   project names removed or replaced). This trades a little ecological
   validity for zero verbatim leakage.

7. **Adapter registry content is frozen at design-time knowledge (§7).**
   Entries reflect the guidance verified during the design review (Fable 5 /
   Opus 5 / Sonnet 5 prompting guides, GPT-5.6 latest-model guide, Gemini 3
   prompting guides, DeepSeek docs). The registry is data, not behavior:
   re-verify entries against current vendor docs when a snapshot changes,
   per the re-run-evals rule in adapters.md.

## Deferred

- **A/B harness automation** (arm runners, LLM-judge prompts): methodology
  documented in `evals/README.md`; automation deferred until a target
  harness/CLI is fixed.
- **Copilot `userPromptTransformed` variant of the interceptor** (§4 noted
  it as a portability target): only the Claude Code `UserPromptSubmit` hook
  is shipped.
- **Session-state suppress-file writer**: the skill instructs the agent not
  to re-enter uplift, but no wrapper currently creates
  `suppress-<session>`; it exists as a hook-side hook for harnesses that
  want a hard guarantee.

## Subagent-dispatch eval (this change)

- **Heuristic compiler is a test double, not the live skill.**
  `evals/harness/` follows SKILLS.md Rev. 2 enough to assert routing,
  isolation, and gold-token coverage without a model. A live Fable-5 run
  can still diverge; `run_trace.py` is the fixture for comparing them.
- **`make` is no longer a blanket protected shell command.** `make it better`
  is English; `make test` is still silenced. The same lookahead lives in
  the hook and the compiler.
- **Reddit pairs are paraphrased.** Live reddit.com JSON/HTML 403s;
  Firecrawl + Tavily found permalinks, then Arctic Shift supplied
  post/comment bodies. OP/comment text is not stored verbatim. See
  `evals/reddit-pairs/SOURCES.md`. Text-prompt subs rarely post true
  one-liners; the short-lazy set mixes the “make it better” phrase list
  with the Midjourney cross-stitch one-liner and the TikTok generate-N
  shape.
- **Fork uplifts always record both subagent calls** in the tracer, even
  when `is_trivial` is true, so isolation can be asserted on every gold
  pair. The live skill may still inline-render trivial contracts (D3).
- **`target_model` is optional and never inferred.** An empty argument
  skips `adapters.md`, omits `target_model` / effort / verbosity from
  hints, and does not mention other model families. Explicit snapshots
  still get adapter notes. This overrides Rev. 2's "infer from runtime
  context" line.
