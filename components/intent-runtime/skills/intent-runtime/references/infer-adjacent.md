# Infer adjacent intent

If a competent human collaborator could infer what the user is trying
to accomplish, infer it too, then name the nearby systems that have to
move with it. The request is a signal about those systems, not only the
named file.

Read this on every `task` and `mission` turn, before compile. Do not
read it on `skip`.

Prefer a cohesive root-cause fix over an isolated patch, so the next
natural action still works. Prefer recoverable workflows and explicit,
discoverable feedback, so a miss is visible and reversible.

Recover the current thread, named material, and relevant original context
before selecting among readings. Use a conventional interpretation only
when it is consistent with recovered directives and permits a reversible
in-scope action. Record unresolved alternatives when they affect the result.

## Tradeoff order

When goals conflict, resolve in this order. Do not invert it.

1. user safety and security
2. data integrity
3. intent clarity and workflow continuity
4. performance
5. polish

## Checklist

- Which nearby systems should evolve together?
- What would feel inconsistent or fragile after this change?
- What behavior would users naturally expect next?
- What edge case would a senior reviewer call out immediately?

## Expansion rule

Record material adjacent impact when it affects execution. Expand into adjacent work only when
leaving it out would make the change inconsistent, unsafe, or fragile.
Tag that expansion `[entailed]` and explain it when it changes the delivered scope.
The tag records reasoning and grants no additional authority.

Do not invent extra product. Do not silently broaden scope because the
adjacent work would be nicer. Intent, authority, and answer-vs-action
do not flip.

If only the named slice is implemented, write the partial-implementation
risk explicitly.

## Output slots

Fill these on the ExecutionContract:

```
inferred_intent.direct_ask
inferred_intent.adjacent_impact
inferred_intent.recommended_cohesive_scope
inferred_intent.risks_if_partial
inferred_intent.expansion          # none | entailed
```

Worked fill — "rename the login button label":

```
direct_ask: change the login button's visible label
adjacent_impact: i18n strings, snapshots, a11y name, docs that quote the old label
recommended_cohesive_scope: label plus the strings and tests that would now lie
risks_if_partial: UI says one thing, tests and screen readers still say the old name
expansion: entailed
```
