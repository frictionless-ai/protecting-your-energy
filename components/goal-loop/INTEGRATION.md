# Optional check-backed goal loop

This source component includes its goal CLI, stop hooks, skill, agent, commands,
templates and general guides. It requires Node.js 18 or later and the shell used
by a configured verification command. The source MIT license is retained.

Run `node scripts/goalctl.mjs --help` from this component. The help path prints
usage without creating goal state. Active goals remain project-local under
`.cursor/goal/`. Creating or changing a goal requires the applicable request.

Select the component through explicit local plugin loading for compatible hosts.
Its stop hook runs the verification commands in the active goal contract. Root
Protect Your Energy hooks leave this loop unregistered. Review the commands and
their authority before enabling the component in a project.

The website, example application, original test suite and release/install
machinery remain in the source project. Source guides may refer to those
upstream artifacts. This integration has checked JavaScript syntax and the help
entry point. It has not created or run a project goal.
