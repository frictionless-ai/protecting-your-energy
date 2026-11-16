---
name: headless-mod-download-automation
description: >
  Use this skill when acquiring every archive for a mod-builds list with
  no GUI and no human clicks (DeadlyStream, Nexus Slow download, MEGA,
  FlareSolverr POST /v1). Use even if the user says "get the rest of the
  zips" or "unattended download." Never solve CAPTCHAs. Do not use for
  wizard Fetch Downloads or for installing a tree that already has archives.
license: BSL-1.1
compatibility: Requires network, a real browser or agent-browser CLI, optional FlareSolverr at localhost:8191.
metadata:
  author: ModSync
  version: "1.1"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Headless archive acquisition

Read `docs/knowledgebase/mod-download-playbook.md` before improvising a host flow.

Dispatch `mod-download-agent` for the batch loop. Dispatch `mod-link-triage-agent` for one failing URL.

## Checklist

- [ ] `./mod-builds` present; Core builds
- [ ] FlareSolverr: `POST http://localhost:8191/v1` (not `GET /`)
- [ ] Per host: playbook, not curl-on-Nexus
- [ ] `file` / `unzip -t` / `7z t` + size floor before trust
- [ ] CAPTCHA → stop that item as blocked-pending-user-action

Load [references/hosts.md](references/hosts.md) when routing a URL.

## Procedure

1. Confirm staging vs already-present archives. Do not redownload good files.
2. Route each missing archive by host (see references/hosts.md).
3. Verify type and size. HTML saved as `.rar` is a failure.
4. For a stubborn link, triage that one URL; do not stall the batch.
5. Fold new host facts into the playbook the same day.

Parity installs after archives exist: `cli-full-md-install` (fail-closed, not `--best-effort`).

## Gotchas

- No `NEXUS_API_KEY` here. Headless `agent-browser` on Nexus can hit a real Turnstile; headed persistent profile is the documented path.
- Never click Turnstile / reCAPTCHA / hCaptcha.
- WARP shared exit IP can TCP-timeout a host; `warp-cli tunnel host add <domain>` before assuming a bot-wall.
- `GET /` on FlareSolverr 404s and is not a health check.
- No new `.sh` files for the download loop — inline commands stay auditable. Skill-local scripts are for skill validation only.
