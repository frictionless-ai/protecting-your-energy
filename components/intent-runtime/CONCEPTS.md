# Concepts

Shared domain vocabulary for this project — entities, named processes, and status concepts with project-specific meaning. Seeded with core domain vocabulary, then accretes as ce-compound and ce-compound-refresh process learnings; direct edits are fine. Glossary only, not a spec or catch-all.

## Eval runners

### Hosted runner
The opt-in host-CLI A/B path for session-pattern fixtures. Default is inspector smoke: one fixture, no host process. A host binary on PATH is not permission to run.

### Inspector
The deterministic, no-model grader that compares a naive reading of a session message to the compiled contract. It is what the hosted runner still runs when live CLI is off, so a smoke job can succeed without invoking a host.

### Live host A/B
The hosted-runner path that actually invokes the host CLI (two run arms plus a blinded grader per case). It is a separate command from the offline suite. Unittest and CI smoke must not take this path.

### Offline suite
The no-model unittest discover for evaluation fixtures. Green here is not a live pass. If this suite hangs, look for an accidental live host spawn before profiling Python.

### Self-handhold
The runtime owns connect, follow-up, iterate, and check. The user does not drive that loop. A complaint that they had to is a missed-inference signal, not tone to strip.

### Distill-intent
The step that turns a solution specification into a pure statement of
intent: problem, outcome, goals, result qualities, and essential
success constraints. Methodology, architecture, and process do not
survive. The compiler and the specialist chassis apply it when the
incoming text is a how-to. Self-improve distills a miss or a strategy
note the same way, then recompiles — the repair is not the new goal.

### Compile-spec dialect
The one compiled shape a forked executor sees: Markdown section headers as the chassis, XML only around recovered or untrusted user data and negation lines, and Pythonic `if` / `elif` only for mutually exclusive paths. It is the compile-spec template, not a third heading set and not a lesson in prompt-ese.
