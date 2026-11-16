# Constraint channels

Every constraint found in the message is classified into a channel; each
channel has an owner. Never strip a constraint wholesale — route it.
Misrouting severity is asymmetric: dropping task semantics or authority is
severity-1; over-forwarding a cosmetic preference is a nit.

| Channel | Owner | Examples |
|---|---|---|
| Task semantics | **executor must receive** | "don't use third-party modules", "i need SPECIFICALLY an 8-bit encoding", "don't use BinaryReader" |
| Authority / boundaries | **executor must receive** | "don't make any changes" (read-only), "don't run the tests until done", "you have permission — just do it, don't ask me every five minutes" (autonomy policy) |
| Output contract | executor prompt and/or native generation controls | "return JSON", "one sentence", "just the one-liner command", "do not summarize or generalize" |
| Reasoning / effort | provider-native parameter when available | urgency/depth cues → effort / thinking level; "be quicker about it" → lower effort, not a prompt clause |
| Cosmetic presentation | primary agent may own | emoji policy, greeting style, rendering niceties the executor need not know |

## Rules

- Brevity requests are legitimate executor instructions on current models —
  do not hide them from the executor. Prefer the native verbosity control
  when the target exposes one; otherwise render a content-priority short-form
  instruction: state what a short answer must *preserve* (conclusion,
  supporting evidence, material caveats, next action) and what to omit
  (secondary detail, repetition), not just a length cap.
- Classify by function, not phrasing: "use your best judgement" is an
  authority grant (keep, forward); "quickly" is an effort cue (map to a
  knob); "no essay" is output contract (render/knob).
- **Persistence is turn-scoped by default.** A constraint outlives the turn
  only on explicit persistence language: "from now on", "always",
  "stop doing X", "for the rest of this session". A persisted constraint is
  re-classified into its channel on each turn it applies to. A one-turn
  contrary request ("explain in detail this time") overrides a persisted
  rule for exactly that turn.
