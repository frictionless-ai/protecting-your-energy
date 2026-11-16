# Evidence-derived skills and agents

This optional source component retains nine skills, five agent roles, templates
and the local build, evaluation and validation helpers. The original private
datasets, generated artifacts and historical runs remain outside the plugin.

Configure `FROM_EVIDENCE_DATASETS`, `FROM_EVIDENCE_BUILD` and
`FROM_EVIDENCE_GENERATED` for the authorized dataset directory, build plan and
generated output. Defaults use the current user's XDG data and state locations
under `from-evidence`. Templates and source validation still resolve from this
component. Source guides referring to `datasets/` or `build.json` describe these
configured locations in this integrated distribution.

The standalone component can be selected through the host's explicit local
plugin loading. Its prompt-based completion hooks are retained for optional
use and are absent from Protect Your Energy's root hook registration. Those
hooks require the host's model support and have their own invocation costs.

Run `python3 scripts/build.py --help` or
`python3 scripts/evaluate.py --help` from this component for supported inputs.
No dataset is bundled or inferred from a source example.

The source validator checks the distributed package by default. Add `--workspace`
to include the configured private dataset and build-plan checks.
