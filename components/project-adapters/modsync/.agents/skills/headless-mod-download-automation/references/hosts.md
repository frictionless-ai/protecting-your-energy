# Host routing

Load this when choosing how to fetch one URL.

| Host | Default |
|---|---|
| deadlystream.com | Browser click on the real download control. Failures are usually stale attachment ids or missing session — not a blanket bot-wall. |
| nexusmods.com | Headed Slow download; honor the countdown. No API key. |
| mega.nz | Browser only (client-side decrypt). |
| github.com | `curl -L` |
| misc | One-off; verify type after |

Integrity: `file`, `unzip -t` or `7z t`, non-trivial size. A tiny HTML error page with an archive extension is the classic silent miss.

Subagents: `mod-download-agent` (batch), `mod-link-triage-agent` (one URL → fixable / mirror / needs-access-step / unobtainable).
