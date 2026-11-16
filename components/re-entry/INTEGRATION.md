# Optional re-entry component

This MIT component preserves the original six reverse-engineering skills, their host stubs, reference procedures, command adapter, Python CLI source, and general design documentation. Skills stay component-specific. The parent plugin has no automatic root route or MCP activation for them.

The original plugin descriptor automatically registered an `npx rea-agents@latest mcp` server. This bundled descriptor omits that registration. REA is an external dependency. Configure an intentionally selected installed version through the host's normal MCP settings when authorized. Tool availability and schemas must be inspected in the active host.

Run the bundled CLI help without installation by setting `PYTHONPATH=components/re-entry/src` and running `python3 -m reentry.cli --help` from the parent plugin directory. Python 3.11 or newer is required. Its own Python runtime uses the standard library. Building a wheel needs Hatchling. REA, Ghidra, objdiff and other catalogued engines are separate products and remain external.

`REENTRY_POOL` overrides the private pool file. Otherwise the pool configuration uses `${XDG_CONFIG_HOME:-~/.config}/reentry/pool.toml`. Shared workers remain unimplemented and refuse work. No private pool file, credentials, target binaries, analysis projects, model artifacts, or generated state is included.

`docs/status.md` preserves the original source's design-stage status. Code presence and the local help checks performed during packaging establish entrypoint availability. They establish no recovered-C parity, full-image proof, functioning distributed worker, or engine integration. The documented `reentry setup` command has no implementation in this source snapshot.

Source copyright and LICENSE remain intact. Optional host stubs and Cursor rules apply only when deliberately selected for an appropriate reverse-engineering project.
