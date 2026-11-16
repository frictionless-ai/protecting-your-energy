---
name: local-desktop-gui-testing
description: >
  Use this skill when launching or driving the Avalonia install wizard on
  a real desktop (preload args, helper scripts, visible pages, native
  pickers). Use even if the user says "click through the wizard" or
  "see the Validate page." Do not use for display-less Cloud VMs, Core
  parser work, or headless Avalonia smoke (run_headless_tests.sh).
license: BSL-1.1
compatibility: Requires X11 DISPLAY, .NET 9, and scripts/agents/launch_gui_desktop.sh.
metadata:
  author: ModSync
  version: "1.1"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Local desktop GUI testing

## Checklist

- [ ] `./mod-builds` exists if the task needs a real guide
- [ ] `./scripts/agents/create_template_kotor_install.sh`
- [ ] Linux: `./scripts/agents/ensure_linux_holopatcher.sh`
- [ ] Launch with preload args, not file pickers
- [ ] Drive wizard pages in documented order

Load [references/wizard-controls.md](references/wizard-controls.md) when you need page order or control names.

## Default launch

```bash
./scripts/agents/launch_gui_desktop.sh \
  --instruction-file ./mod-builds/content/k1/full.md \
  --kotor-dir ./tmp/kotor_template \
  --mod-dir ./tmp/mod_downloads
```

Prefer `content/k{1,2}/full.md` over `KOTOR*_Full.toml` when the task is guide parity.

Preload flags: `--instructionFile`, `--kotorPath`, `--modDirectory`.

Headless smoke (not this skill):

```bash
./scripts/agents/run_headless_tests.sh --filter "FullyQualifiedName~Headless|FullyQualifiedName~GuiSmoke"
```

## Gotchas

- Cloud / no X11: do not run the desktop app. Use headless tests.
- If validation says HoloPatcher is missing, run `ensure_linux_holopatcher.sh` before automating pickers.
- `ZIndex` is not valid in AvaloniaUI.
- Do not hardcode fonts/colors on XAML controls.

## After new GUI facts

Update `docs/local_desktop_agent_runbook.md`, this skill, `.cursorrules` if always-on, and launch configs if the launch flow changed.
