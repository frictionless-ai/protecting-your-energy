# GUI full-build click sequence

Load this when driving ValidatePage on a desktop.

1. Clone `mod-builds` if needed.
2. `./scripts/agents/create_template_kotor_install.sh ./tmp/kotor_template ./tmp/mod_downloads`
3. `./scripts/agents/ensure_linux_holopatcher.sh`
4. Launch with preload. Prefer `content/k1/full.md` for parity; TOML only when the task is specifically the TOML wizard path.
5. `ModSelectionPage` → `SelectAllButton` → confirm count.
6. Fetch Downloads; wait until progress stabilizes.
7. `ValidatePage` → Run Validation → expand `LogExpander`.
8. Record environment, install-order, and dry-run/VFS issues.
9. Install only if the task expects a real write.

Good: environment passes, order passes, dry-run empty or acceptable warnings.
Bad: missing HoloPatcher, blocking extract failures, Next blocked by critical errors.
