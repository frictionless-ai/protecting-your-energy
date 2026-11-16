# Protect Your Energy

Keep the energy to explain an idea, develop it and get it done.

This project grew out of repeatedly having to explain the same thing to an AI,
recover context it could have found, connect the dots, request follow-ups and
remind it to check its work. Each correction takes effort away from the thing
you wanted to do. Sometimes the explanation gets longer while the result gets
further from what you meant.

Protect Your Energy brings together the skills and tools for reducing that
burden. The agent should investigate what you mean, use what you have already
explained, carry forward your corrections and keep working on the result you
asked for. It should leave room for the creative decisions and involvement you
enjoy.

## What it should help with

- Recover an idea spread across conversations, notes and project material.
- Combine your words into a coherent account while preserving your meaning,
  examples, uncertainty and voice.
- Recognize when an example illustrates a larger request and recover that
  request from its context.
- Find terminology that helps you explain or investigate an idea.
- Ask a concrete question when it helps you develop an idea, while continuing
  independent work.
- Follow through on investigation, implementation, iteration and checking.
- Continue useful independent work while an operation runs or an answer is pending.
- Resume interrupted work with its goals, corrections and unfinished steps intact.
- Notice recurring obstacles and improve the workflow that keeps producing them.
- Check whether the result actually addresses what you asked for.

## Thought reconstruction

Thought reconstruction recovers the thought behind scattered explanations. It
starts with your words and follows the relevant conversations, examples and
corrections. When you ask for a project account, it produces a cohesive Markdown
document with source references and the details already expressed about the idea.
It can discover project candidates from available context and derive a
descriptive name from the recovered account.

Your original explanations determine the substance. AI responses can complete a
reference or preserve an idea you explicitly adopted. Additional design work
belongs where you ask for it. A request to reconstruct an idea should preserve
what you meant without making you correct a newly invented architecture.

The local tooling supports candidate discovery, Roust-assisted retrieval,
contextual source inspection and evidence-linked document generation. The
active agent interprets the source material and reviews the account. Read its
skill and command guide for the supported formats, bounds and continuation
behavior. [Thought reconstruction](skills/thought-reconstruction/SKILL.md) ·
[Command guide](scripts/thought-reconstruction/USAGE.md)

## Keeping work moving

Install with Claude Code's GitHub marketplace command.

```text
/plugin install protecting-your-energy --marketplace frictionless-ai/protecting-your-energy
```

The included skills cover context recovery, clear expression, useful next
actions, recurring friction, sustained momentum and evaluation. They work
together through the main entry point.

```text
$protect-your-energy <what you are trying to do>
```

The main skill selects the relevant procedure from the request and available
context. Host support determines implicit selection and hook execution.
Background work needs an actual running execution mechanism. Progress reports
should reflect what has run, what has been checked and what remains.

The project also includes helpers for retaining task state, preparing
continuations and coordinating authorized background work. The component
documentation describes their individual setup and dependencies.
[Main skill](skills/protecting-your-energy/SKILL.md) ·
[Workflow orchestration](skills/workflow-orchestration/SKILL.md) ·
[Momentum](skills/sustain-momentum/SKILL.md) ·
[Evaluation](skills/self-evaluation/SKILL.md)

## Working with personal context

Source conversations and private working state stay in your configured local
locations. The plugin contains reusable procedures and tooling. Source access,
external providers and host hooks need configuration appropriate to your
environment.

Preserving energy includes keeping your choices, corrections and ability to
pause. The agent should recover information already available and ask when an
unresolved answer materially changes the work. The result should remain easy
to correct.

## Development

The intended behavior comes from the problems described above. Each capability
needs evaluation against real tasks, including cases where the agent has
misunderstood the scope or overlooked a correction. Source correspondence,
working integrations and a result the user finds representative each require
their own evidence.

The component inventory records the bundled skills, agents, commands and hook
adapters, alongside configuration and external dependencies.
[Included components](COMPONENTS.md)

Some retained workflows have their own project-scoped hooks or host setup.
Their source and instructions are included with the component. The main workflow
can consult those instructions directly and use the tools available in the active
host. Component-specific execution requirements are described in the inventory.
