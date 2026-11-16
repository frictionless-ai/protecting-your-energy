---
name: mission-brief
description: >
  Legacy elicitation front-half for an explicit mission. Use when the
  user asks to "start a mission" or "/mission-brief" and the ask is too
  thin to write a mission contract from. Recovers outcome, boundary,
  situation, and criteria via answer cards with silence-defaults.
  Ordinary underspecified tasks belong to prompt-runtime, not this
  skill.
disable-model-invocation: true
metadata:
  version: "0.6.0"
---

# Mission Brief

Convert an underspecified ask into something buildable by talking, not by
interrogating. A user who writes "make it better" is not withholding a spec.
They are holding a situation they have not had to put into words yet, and
the fastest way to get it is to be easy to correct rather than expensive to
answer.

Nothing in this skill blocks independent inspection. Start the reading
that is already clear, run the brief alongside it, and let silence keep
that work running. When the mission is a create, the new artifact waits
on intake: recover first, then remaining cards.

## When to run a brief

Run one when two or more of the four decision inputs are missing and cannot
be recovered from the repository, the prior conversation, `docs/`, or the
ledgers. When the mission is a create, read
`${CLAUDE_PLUGIN_ROOT}/skills/prompt-runtime/references/intake.md`
before the first card: recover every already-known answer at full
fidelity, auto-answer branches the user has not redirected, and walk
only what is still open.
These four are the inputs that change what gets built; everything else can
be defaulted and logged.

| Input | The question it answers | Missing when |
|---|---|---|
| Outcome | What is true when this is done? | Only a mechanism or a mood is named ("faster", "cleaner", "use Redis") |
| Boundary | What must not change? | No scope edge, no compatibility or budget limit, no "don't touch X" |
| Situation | What is happening now, and what was already tried? | No failure text, no current behavior, no prior attempt |
| Criteria | How to choose when options tie? | Two defensible builds exist and nothing in the message prefers one |

One missing input is a provisional assumption: register it and continue.
Three missing inputs is not a licence for three times the questions — the
ceiling below still holds.

Message length does not decide this. A long ramble often carries all four
inputs, and a six-word message sometimes carries them too. Judge the inputs,
not the word count.

## The ceiling

At most three remaining answer cards after recovery, once per mission,
one card per turn so dependent branches resolve in order. Past that,
default the rest, register them as assumptions, and build. A user who is
already tired of explaining will not be rescued by a fourth question, and
the mission's own question gate governs anything that genuinely blocks
later. Thoroughness follows the size of the create: a named micro-create
gets zero cards; a multi-surface create may use the full three.

## Open by staking a reading

Lead with the interpretation, not with a question. A stated reading gives
the user something to push against, which is cheaper for them than composing
an explanation from nothing — and a wrong reading is corrected in one line.

State it, hedge it honestly, name the one thing that would change it:

> Reading this as: the install breaks on a clean Fedora box and you want it
> to stop needing manual steps. Fairly confident. What I cannot tell from
> here is whether the Ubuntu path has to keep working unchanged.

Then the next remaining card — one decision, with the recommended
answer marked. Then the inspection already in motion. A brief that
opens with "could you clarify?" has spent the user's attention and
returned nothing. Do not send a card whose answer is already in the
conversation, `docs/`, or the ledgers.

## Answer cards

Every question ships as an answer card: pre-filled options drawn from real
evidence, a marked default, and the hands-off option. The user answers by
picking, not by writing.

Read `references/answer-cards.md` before composing the first card — it
carries the card format, where autofilled options come from, the hands-off
contract, and worked examples.

Use the platform's structured question tool when one is available so the
options are clickable; fall back to a lettered list in chat when it is not.
Either way the card keeps its shape.

## Hands-off mode

Every card carries an option that ends the questions: *decide for me — no
more questions this mission*. Selecting it records a decision, sets
`Autonomy: hands-off` in the contract, and suppresses answer cards for the
remainder of the mission. Preference questions stop; the mission's question
gate still surfaces the rare item that carries real authority or
irreversibility, because a user waiving questions about scope has not waived
authority over their own credentials or their production data.

Treat an explicit "just figure it out", "do whatever", "you decide", or
"build as much as you can" in the original message as hands-off already
selected. Do not ask a user who pre-authorized autonomy to confirm it —
state the reading, register the assumptions, and build.

## How to talk

The register matters as much as the questions. Read
`references/elicitation.md` before the first brief — it carries the
conversational moves that measurably draw out detail, the ones that
measurably end a thread, and the evidence behind each.

The four that carry most of the effect:

- **Disclose your own attempt before asking for theirs.** "I looked at the
  installer and the service unit; the unit assumes a config dir that the
  package never creates" earns more than any question does.
- **Name what you cannot tell from here.** Specific uncertainty invites a
  specific answer; "please clarify" invites nothing.
- **Offer a named choice instead of an open question.** "Flaky tests first
  or missing coverage first?" outperforms "what would you like me to focus
  on?" by a wide margin.
- **Ask them to describe, not to decide.** When someone is stuck, "walk me
  through what it does now" produces detail that "what do you want?" does
  not.

## Handing off

A brief is not a mission. When the inputs are recovered — by answer, by
default, or by hands-off — write them into the contract at
`.mission/mission.md` and continue under the mission skill: outcome and
criteria become the outcome model, boundary becomes scope and drift
boundaries, situation becomes the starting evidence in the ledgers. Answered
cards land in `.mission/decisions.md`; defaulted cards land in
`.mission/assumptions.md` with the option that fired and the impact if it is
wrong.

If a mission is already running, a brief for a vague mid-mission directive
follows the amendment protocol: the directive lands in the queue verbatim
first, and the card resolves how to act on it, not whether to.

## Boundaries

- A specified ask does not get a brief. When outcome and boundary are both
  present, run the mission and let the readback carry the interpretation.
- A brief never delays independent inspection. The new artifact of a
  create waits on remaining load-bearing branches being settled or
  defaulted.
- A card is not a permission request. "Which of these two?" is a card;
  "shall I proceed?" is a disguised permission request and does not belong
  in one.
- Questions about the user rather than the work stay out. The brief recovers
  what to build, not who they are.
