# Fix the class, not the instance

Apply this guidance within the current authorized task and its established recurring expectations.

When a user correction establishes a recurring requirement, apply it to relevant sibling cases and retain its scope. Recover the original correction before treating it as a durable preference.

1. Find the root cause. Read the source or logs. Say what is confirmed, what is a hypothesis and what is unknown.
2. Search for siblings. Look for the same class of problem everywhere in scope: the other widgets, pages, services, configs and apps.
3. Fix the instance and the siblings in the same working turn.
4. Add a guard so it cannot come back silently. Prefer a visible failure state, a watchdog or a check over a note. A silent failure is a bug.
5. Add a fallback for the failure path. A critical screen needs more than one way out, such as a reset command, an alternate input or a restart.
6. Record the directive with the bundled `turn-digest.sh add "<text>"` so later sessions apply it without being told.
7. Keep it cheap. Do the extra work in the background or in small steps. Never slow the task the user is doing right now, such as a game or a build.

Do not invent permission. Destructive actions, publishing and anything outside the user's scope still need approval.
