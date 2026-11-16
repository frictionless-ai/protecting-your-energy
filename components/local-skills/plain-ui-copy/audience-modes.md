# Audience modes

Pick one mode per file. When the audience is ambiguous, infer it from the path.

## Mode A — UI

User-visible strings in a running product: labels, buttons, placeholders,
toasts, empty states, onboarding, tooltips, landing pages, marketing.

Rules: verb-first, at most one adjective per sentence and prefer zero, friend
test (2 adjectives per paragraph or fewer), slop audit.

Paths that usually mean Mode A:

```
**/site/**, **/locales/**, **/i18n/**, **/*.{tsx,jsx,vue,svelte,html,mdx}
```

Extra checks before commit:

1. Run the slop audit on every `title`, `label`, `placeholder`, `description`,
   `emptyState`, and `cta` prop.
2. Headings in JSX/MDX are imperative or a benefit, never a feature codename.
3. Any subhead you add is 15 words or fewer and is not a feature dump.
4. Read the diff aloud. If it sounds like a product brochure, rewrite it.

## Mode B — public docs

README sections, public documentation, anything a reader outside the team
lands on.

Rules: precise and technical, no marketing adjectives. Lead with what the
reader can do.

## Mode C — internal docs

Contributor docs, internal notes, runbooks.

Rules: terse bullets. Keep file names and function names intact.

## Do not

- Make UI copy sound like a README, or a README sound like UI copy.
- Swap synonyms for variety. Use the same term for the same concept across files.
- Change code logic, imports, or component structure, unless a string prop rename requires it.
- Invent features that are not in the codebase.
