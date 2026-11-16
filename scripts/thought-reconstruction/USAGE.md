# Thought reconstruction commands

The package resolves its implementation relative to its installed location.
Invoke the dispatcher from the resolved Protect Your Energy root.

```sh
python3 scripts/thought_reconstruction.py --help
python3 scripts/thought_reconstruction.py discover
python3 scripts/thought_reconstruction.py acquire --help
python3 scripts/thought_reconstruction.py inspect --help
python3 scripts/thought_reconstruction.py assemble --help
```

`discover` prepares bounded identity hints and a continuation. The agent reviews
original context, identifies the intended project, acquires complementary
details and writes the cohesive account. `assemble` verifies an authored claim
ledger and generates the design document with explicit gaps and scope decisions.

The detailed adapter guide is
[components/thought-reconstruction/scripts/USAGE.md](../../components/thought-reconstruction/scripts/USAGE.md).

Indexed commands use the bundled `thought-reconstruction-engine` component when
available. `THOUGHT_RECONSTRUCTION_LEGACY_ENTRY` selects an external engine's
`bin/thought-reconstruction` entrypoint. `THOUGHT_RECONSTRUCTION_CONFIG` retains
the engine's private configuration override. Existing library arguments pass
through unchanged.

Without that override, the bundled library uses an existing XDG configuration
at `protecting-your-energy/thought-reconstruction.json`. If it is absent and the
earlier private `~/brain-data/upar-dip/derived/thought-reconstruction/config.json`
exists, that file remains the configuration source. A fresh installation defaults
to the XDG location. Configuration contents stay outside the package.

`THOUGHT_RECONSTRUCTION_ARCHIVE` identifies the private archive root for automatic
discovery and output protection. Explicit `--root` sources remain available.
`THOUGHT_RECONSTRUCTION_OWNER_ID` supplies Discord owner attribution, and
`--owner-id` can override it. An unset owner identity leaves Discord authorship
unattributed while retaining review-required search candidates. Configure these
values privately for the installation.

Provider-backed and indexed routes retain their configuration and authorization
requirements. Private sources, indexes, models and credentials stay in configured
external storage. The acquisition adapter uses Python's standard library and
optionally invokes an installed Roust executable. Its receipts identify actual
nomination, fallback, omissions and continuation.
