---
name: sponsorware
description: Put a codebase behind a paid sponsor or subscriber wall and keep a docs-only public repo. Use when asked to make source sponsors-only, subscribers-only, members-only or paid-access; to split a repo into public docs plus private source; to wire GitHub Sponsors tier access; to relicense from open source to source-available; or to verify source is unrecoverable before making a repo public.
---

# Sponsorware

Move source behind a sponsor wall, keep a public face for docs and issues, and
prove the source is unrecoverable before anything is published.

## Staged release sequence

For a new project that is private today, release in stages. Treat each stage as
an independently reviewable product boundary; do not jump directly from local
work to a public repository.

1. **Private foundation.** Keep the source repository private. Build the
   smallest useful slice, document its scope, and validate privacy, licensing,
   dependency, and rollback assumptions. No public mirror is created.
2. **Private dogfood.** Exercise the slice against representative workloads
   and record outcome evidence, friction, and known gaps. Keep raw traces,
   credentials, unpublished research, and third-party data private.
3. **Sponsor preview.** If sponsorship is the chosen access model, attach the
   private source repository to a monthly GitHub Sponsors tier. Publish only
   the access terms and a sanitized capability description. Sponsors receive
   access to the reviewed revision, not an implicit promise of production
   readiness.
4. **Public documentation.** When the product boundary is stable, create a
   fresh docs-only repository with independent history. Run the pre-publish
   gate before the first push. It may describe the product and collect issues,
   but it must not contain recoverable source, source-bearing tags, or patches.
5. **Brand and portfolio distribution.** Turn the reviewed release into a
   small sequence of channel-specific artifacts: a canonical GitHub story,
   an owned-site case study, a Medium article or publication submission, a
   developer-community post such as DEV, and a short sponsor/update note when
   appropriate. Each artifact must link back to the canonical project and use
   the same version, evidence, and claim boundaries. Prefer APIs or approved
   platform workflows where available; Medium supports publication posting for
   authorized editors, while community sites may require a draft or manual
   submission. Never spray the same text across channels.
6. **Public core or general release.** Only after an explicit owner decision,
   license/dependency review, sponsor communication, and a fresh pre-publish
   gate should any source or generally usable package become public. Record the
   exact version boundary and what remains sponsor-only.

Use the release model the owner requested. Preserve any explicit publication, push, access, and license-change authorization already given. Ask only when a required action exceeds that authorization. Keep a short release ledger containing stage,
revision, allowed audience, artifacts, evidence, and rollback path.

### Distribution pipeline

For each reviewed stage, run this pipeline:

```text
release evidence
  -> one canonical announcement and portfolio narrative
  -> channel adaptations (GitHub, owned site, Medium, DEV/newsletter)
  -> claim/privacy/license review
  -> owner approval
  -> publish or submit
  -> record URL, revision, audience, and response
```

The pipeline prepares drafts and submission payloads automatically, but
publication is an explicit owner action. Do not expose sponsor-only details,
private traces, unreleased source, or identifiable third-party material while
marketing a stage. A channel with no reliable publishing path remains a
prepared draft; do not add a brittle browser scraper just to claim automation.

Measure portfolio value by qualified readers, useful feedback, contributors,
sponsors, and concrete reuse. Do not optimize for impressions alone. Preserve
the same staged release ledger across code, documentation, sponsor access, and
marketing so every public claim can be traced to a reviewed revision.

## The rule that decides everything

**Deleting `src/` in a new commit protects nothing.** Git keeps every earlier
version. `git log -p` recovers all of it the second the repo is public.

A placeholder like `src/SPONSORS-ONLY.md` is a signpost, not a lock. If it lands
in a repo whose history still holds the source, you have hung a sign on an
unlocked door.

Six ways source leaks out of a repo you made "docs-only":

| Vector | Why it leaks |
|---|---|
| Commit history | `git log -p` on any source-bearing commit |
| Tags | A tag pins a whole source tree, even off `main` |
| GitHub Releases | Auto-generated `.tar.gz` / `.zip` of the tagged tree |
| Merged PR diffs | Full patches stay readable on a public repo |
| Stale remote branches | Never deleted after merge |
| Forks | A fork made while public survives the repo going private |

## Pick the shape

| Shape | What it is | Pick it when |
|---|---|---|
| **Two-repo split** | Private source repo + separate public docs repo, fresh history | Default. Nothing to purge, no force-push, no leak risk |
| **History purge** | `git filter-repo` the source out, force-push, republish | Only if the public repo URL must be preserved and stars/issues matter |
| **Open-core** | Public core, private premium modules | The core has standalone value and you want contributors |

Prefer the two-repo split. A fresh public repo has no history to leak, so the
gate below passes trivially instead of relying on a rewrite being complete.

## Two-repo split

1. **Keep the existing repo private.** It stays the source of truth. Do not
   rewrite it, do not republish it.
2. **Create a new public repo** for docs. Fresh `git init` — never clone or
   fork the source repo, or you inherit its history.
3. **Copy only** docs, README, images, the docs license, issue templates.
   Copy files, not git objects.
4. **Carry no tags.** A tag pointing at a source-bearing commit re-publishes
   the source.
5. **Run the gate** (below) against the public repo before the first push.
6. **Wire sponsor access** on the private repo (below).
7. Point the public README at the sponsor tier, and take issues on the public repo.

## Pre-publish gate

Run the gate against any repo about to go public. It fails loudly if source is
recoverable:

```
<skill-directory>/publish-gate.sh <repo-path> [--canary=STRING] <pathspec>...
```

Describe source by **file type**, not by directory, so a deliberate placeholder
like `src/SPONSORS-ONLY.md` does not trip the gate:

```
publish-gate.sh ./myproject-docs --canary=kJmpRel32Size '*.cpp' '*.hpp' '*.inc'
```

Pick a canary that only ever existed in private source — an internal constant or
a member name, never something the docs also mention.

It checks, across every ref and not just `HEAD`:

- no tracked files match the source pathspecs
- no commit in `--all` ever *added* a file matching them
- no tag or remote branch points at a tree containing it
- no GitHub Release exists (source tarballs)
- an optional canary string appears in no blob in the object store

Never make a repo public on a green working tree alone. The gate reads history.

## Licensing

**You cannot revoke a license you already granted.** Anyone who received the
code under MIT/GPL/AGPL keeps those rights forever, including redistribution.
Going private removes future access, not past grants.

What you *can* do, if you hold copyright on all of it:

- Relicense **future versions**. State the boundary plainly: "0.1.0 was AGPL-3.0;
  0.2.0 and later are source-available under X."
- Check every dependency first. Permissive deps (MIT, BSD, Apache) can be
  combined into a source-available release if you keep their notices. Copyleft dependency obligations depend on how the code is combined and distributed. Verify the applicable license and release facts.
- Check every contributor. More than one author means you need their permission
  or a CLA. Verify with `git log --format='%an <%ae>' | sort -u`.

Common source-available licenses:

| License | Shape |
|---|---|
| **FSL-1.1** | Non-compete, converts to MIT/Apache after 2 years. Best default for sponsorware |
| **BUSL-1.1** | Parameterized; non-production use allowed, converts after up to 4 years |
| **PolyForm** (Noncommercial, Shield, Strict) | Pick one prewritten restriction |
| Custom EULA | Full control, no ecosystem recognition, needs a lawyer |

None of these are open source. Do not call them open source.

Docs in the public repo get their own license (CC-BY-4.0 is normal). Do not
leave a copyleft `LICENSE` sitting in a docs-only repo — it is incoherent and
arguably licenses the docs to everyone.

## GitHub Sponsors wiring

GitHub has native sponsors-only repositories. Attach a private repo to a tier
and GitHub adds and removes sponsors as collaborators automatically.

- Enable Sponsors, then add the private repo to a tier in the tier editor.
- **Monthly tiers only.** One-time tiers cannot grant repo access.
- Sponsors get read access. They can clone and leak; the wall is social and
  legal, not technical.
- Add a `.github/FUNDING.yml` to the public repo so the Sponsor button shows.

Alternatives when GitHub Sponsors does not fit: Polar, Patreon plus a
license-key server, or a private package registry with per-subscriber tokens.
A registry is the only one that ships builds without shipping source.

## Say it plainly in the README

State three things, or you will field the same issue forever: what is public,
what sponsorship buys, and which version changed license. Do not imply the
project is still open source if it is not.

## Verification scope

The bundled gate is a historical local helper. Its pass result covers its completed checks and selected pathspecs. Independently resolve command errors, missing tools, remote artifacts, forks and external copies before relying on a release decision. Verify current platform and license details from authoritative sources when executing a release.
