---
name: anonymous-mod-fixtures
description: >
  Use this skill when adding or editing tests, fixtures, comments, policy
  exceptions, or sample guides so published mod titles stay out of this
  repo. Use even if the user only says "add a test for that installer
  option" or "hard-code an exception." Do not use for live install logs
  or for editing upstream mod-builds guides.
license: BSL-1.1
metadata:
  author: ModSync
  version: "1.1"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Anonymous fixtures

`AGENTS.md` § Never name a real mod in this repo.

## In this repository

Do not put a published title, author-branded pack name, archive file name, host slug, or option label that only that pack uses into:

- tests and assert messages
- `ModComponent.Name`
- C# comments or XML docs
- `[[exceptions]]` / policy that hard-codes one titled pack

Use stand-ins: `Texture Pack A`, `example-mod.zip`, `Option 2: Extra Scene`, `N_Example01.tga`.

## Allowed outside this tree

Live install logs, operator reports, checkpoint subjects, and `mod-builds/content/k{1,2}/full.md`.

## When editing old tests

If you touch a test that still uses a real title, anonymize it in the same change.

## Interpretation

New behavior is a **pattern** in `guide-interpretation.defaults.toml`. Not `if (component.Name == "…")`.

## Gotchas

- Unique option labels are titles. "I recommend the Additional Scene option" in a test must become a made-up sibling pair.
- Host slugs and archive basenames count. `example-mod.zip` only.
