---
name: re-observe
description: Use this skill when asked what a binary does when it runs, to trace, replay, hook or instrument a target, a firmware image or a device, or when static evidence cannot answer a behavioural question. Routes between PANDA, avatar², Renode, Frida and real-hardware traces.
license: MIT
metadata:
  author: re-entry
  version: "0.1"
---

# re-observe

Execution evidence answers questions decompilation cannot: what value actually arrived, which branch actually ran, what the device actually returned. It is also the evidence most easily mistaken for proof. Label its substrate every time.

## Before running anything

- Static first. If `analyze_function` or a data-flow trace in REA answers the question, stop there. Running code costs more and proves less than it looks.
- The target must be declared: which binary, which build, which inputs, which lifecycle. Do not broaden it mid-run. REA's `prepare_bounded_process_capture` prompt is the template for a declared experiment; use it even when REA is not the executor.
- Authorization covers the target you were given. It does not extend to a sibling binary you found while looking.

## Pick the substrate

| Question | Engine | Substrate label |
|---|---|---|
| Whole-system behaviour, taint, replay a recording deterministically | PANDA | `emulator` |
| A userland process you can attach to, hook calls, read live memory | Frida | `live-process` |
| Embedded firmware with known peripherals | Renode | `model` |
| Firmware whose peripherals Renode does not model | avatar² handing unmodelled regions to the real board | `mixed` |
| Timing, analog behaviour, undocumented registers | Real-hardware trace | `hardware` |

Check `reentry doctor --json` for what is installed and whether the precondition holds: Renode needs a platform description, PANDA needs a recording or a bootable image, Frida needs a process you may attach to.

## Record

Every observation carries: substrate, engine and version, target hash, inputs, and the exact command or script. A PANDA replay is reproducible from the recording; a Frida session is not reproducible from anything but the script and the same binary state. Say which.

Behaviour observed on a model is a claim about the model. Behaviour observed on hardware is a claim about that board. Neither is a claim about the source.

## Feed back

Observed values become constraints for `re-match` (a function that reads the same device register in two builds) and `re-verify` (a concrete input where original and recovered must agree). Hand them over as records, not prose.

## Refuse

- Running a target that was not declared.
- Reporting model behaviour as hardware behaviour, or either as static fact.
- Describing static analysis as if it observed execution.
- Treating a successful hook or call as recovered source. Original code running is not source parity.

## Report

Per observation: substrate, engine and version, target, input, what was seen, what it constrains. Then what could not be observed and why. Rules in full: `../reverse-anything/references/rules.md`.
