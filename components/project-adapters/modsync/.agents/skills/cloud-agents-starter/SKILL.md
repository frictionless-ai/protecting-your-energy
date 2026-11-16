---
name: cloud-agents-starter
description: >
  Use this skill when bootstrapping a headless Cloud VM for ModSync:
  .NET 9 build, non-LongRunning tests, NuGet.org-only restore, inotify
  gotchas, or routing telemetry-auth vs Core/GUI. Use even if the user
  says "run the usual tests" on a display-less box. Do not use for the
  desktop wizard or a real full-build install.
license: BSL-1.1
compatibility: Designed for Cursor Cloud / headless Linux. Requires .NET 9 SDK. No X11.
metadata:
  author: ModSync
  version: "1.2"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Cloud / headless bootstrap

## Checklist

- [ ] `dotnet --info` is 9.0.x
- [ ] `git submodule update --init --recursive` before first build
- [ ] `NuGet.config` is nuget.org only (no GitHub Packages auth)
- [ ] Tests: `./scripts/agents/run_headless_tests.sh` (exclude `LongRunning`)
- [ ] Do not launch the Avalonia desktop app

Load [references/build-and-test.md](references/build-and-test.md) for commands and filters.
Load [references/security-and-env.md](references/security-and-env.md) when touching telemetry, settings, or URL/archive code.

## Routing

- Core / tests / docs → this skill + headless `dotnet`
- GUI / wizard / full-build desktop → `local-desktop-gui-testing` (needs X11)
- `telemetry-auth/` → that directory's own docs
- CLI guide install → `cli-full-md-install`

## Gotchas

- `CrossPlatformFileWatcherTests` fail without inotify in cloud FS — expected.
- Some Avalonia xUnit tests fail headlessly — pre-existing.
- `DISPLAY=:1` is for a real desktop VM, not for this skill's default path.
- Do not create a second test project. Everything lives in `src/ModSync.Tests`.
- Tests >2 minutes need the `LongRunning` suffix.

## Update

Edit `.agents/skills/cloud-agents-starter/`. Mirror hard rules to `.cursorrules` when they apply to every task.
