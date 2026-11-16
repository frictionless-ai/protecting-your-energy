# Protect Your Energy

Recover what someone means and carry that meaning into the model doing the work.

The project brings together four pieces.

| Piece | Purpose | Entry point |
| --- | --- | --- |
| Thought reconstruction | Recover ideas, reasons, constraints and corrections from conversations and documents, with original-source evidence | [Skill](skills/thought-reconstruction/SKILL.md) |
| Intent runtime | Turn the recovered outcome into an execution contract and follow through on authorized work | [Skill](skills/intent-runtime/SKILL.md) |
| Prompt uplift | Prepare a self-contained prompt when a target executor needs context carried across a handoff | [Skill](skills/prompt-uplift/SKILL.md) |
| Prompt-submit hook | Supply context-recovery and meaning-preservation guidance before the assistant responds | [Hook](components/semantic-expression/hooks/intent_coach.py) |

`intent-runtime` remains the component and skill name. Its documentation calls
its operation an **intent compiler**.

## How they work together

Start with the current conversation, named material and the user's corrections.
Use thought reconstruction when missing history could change the work. Intent
runtime organizes the recovered request into an execution contract. Prompt
uplift makes that contract self-contained when another executor needs it.
Preserve the user's methods, constraints, uncertainty, scope and requested format
throughout the process.

The submit hook injects guidance into the assistant's context. Its implementation
uses Python's standard library and makes no model calls. The host retains the
original user message. Any interpretation or prompt compilation happens in the
assistant's turn. A separate model-powered preprocessing turn would require
additional implementation and host integration.

## Use

For Claude Code, add the marketplace and install the plugin.

```text
/plugin marketplace add frictionless-ai/protecting-your-energy
/plugin install protecting-your-energy@frictionless-ai
```

Invoke the umbrella skill or select a core skill directly.

```text
/protecting-your-energy:protect-your-energy
/protecting-your-energy:thought-reconstruction
/protecting-your-energy:intent-runtime
/protecting-your-energy:prompt-uplift
```

Claude documents marketplace installation and namespaced skill invocation in its
[plugin guide](https://code.claude.com/docs/en/discover-plugins).

Hosts that use dollar-prefixed skill invocation can use `$protect-your-energy`,
`$thought-reconstruction`, `$intent-runtime` and `$prompt-uplift`.

The repository includes Claude and Codex plugin manifests. Hook discovery,
activation and trust depend on the host. Each root hook configuration registers
one `UserPromptSubmit` command. Reconcile an existing direct registration of
`intent_coach.py` when enabling the plugin so the event runs once.

Prompt uplift also has an optional candidate-marker hook under its component.
Its [setup guide](components/prompt-uplift/README.md) describes deliberate activation.

## Reconstruction commands

```sh
python3 scripts/thought_reconstruction.py --help
python3 scripts/thought_reconstruction.py acquire --help
python3 scripts/thought_reconstruction.py inspect --help
python3 scripts/thought_reconstruction.py reclaim --help
```

The acquisition adapter supports source discovery, contextual inspection and
curated assembly. The indexed engine supports existing library workflows,
including reclaim, rebuild, verify, query and task. The dispatcher keeps both
interfaces available. [Command guide](scripts/thought-reconstruction/USAGE.md)

Source archives, identity settings, provider credentials, generated indexes and
working output belong in private external locations. Local acquisition uses
Python's standard library. Roust is optional. Indexed retrieval and explicitly
configured hosted processing have additional dependencies described in their
guides. [Components and configuration](COMPONENTS.md)
