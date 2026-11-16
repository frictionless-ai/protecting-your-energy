# Prompt engineering rules for generated skills

Rules the template follows and the reviewer checks. Each has a reason;
without the reason the rule gets cargo-culted.

## Description

- Third person. It is injected into a system prompt; "I can help" reads as
  the assistant talking about itself.
- Name what it does and when. Quote three to five trigger phrases a user
  would type. Skills under-trigger; a pushy description is the fix.
- No trigger information in the body. The body is not in context until the
  description has already fired.

## Body

- Imperative, verb first. "Ask for the run." Not "You should ask for the
  run." The reader is executing, not being advised.
- One idea per sentence. A skill is read under load, mid-task.
- Bullets over paragraphs for lists; paragraphs only to explain a why.
- Under 3,000 words. Exemplars live in `reference.md`.
- Explain why a rule exists when the rule is surprising. "Ask them to fetch
  the data so they own the result" survives edge cases; a bare "ask them to
  fetch the data" does not.

## Evidence grounding

- Every phrase in the bank is verbatim from a training record and carries a
  count. A phrase with no count is an invention.
- Every anti-pattern names tell-tale phrases. "Do not be rude" is not
  testable; "never: 'you always', 'you never'" is.
- Held-out records are never quoted. The evaluator checks for leaks.
- Motivations are written so a judge can ask "would this person answer
  this?" and decide.

## Structure

- Moves by phase (opening, escalation, repair, exit) so the skill composes
  one turn at a time instead of dumping everything at once.
- A quality bar the skill can run on its own output.
- Links one level deep. `SKILL.md` to `reference.md`; never a chain.

## Evolution

- Name the gate (`offload-indirect`) and the log owner (`evolution`) so the
  skill improves through the user's existing mechanism, not a new one.
- Say where new examples go (the dataset, via `/evolve`) so nobody edits
  the generated file by hand.

## Things to strike on review

- Buzzwords: seamless, robust, powerful, unified, holistic, leverage,
  cutting-edge.
- Comma-separated noun piles in place of a sentence.
- Any date or timestamp inside the generated file.
- A phrase that appears in the bank but in no record.
