# Reclaim an idea

Start with an idea, rough phrase, pasted note or selected file. The agent gathers
the earlier thinking, writes the idea so it can be used, and carries out the next
reversible action when the request calls for work. The user should not need to
choose retrieval methods, prepare keywords or retell the archive.

Examples:

> Reclaim my notes app idea.

> Reclaim this workflow and carry it forward.

> $reclaim the interface idea I discussed earlier

The short skill is an adapter to the canonical Thought Reconstruction workflow.
The command prepares evidence for the agent. It does not itself write a finished
reconstruction or prove exhaustive recovery.

## Recover the context

Resolve the installed checkout and read the selected private configuration.
Read its optional `reclamation.owner_context` when relevant. That is a revisable
guide with source locators, not a fixed identity or evidence for every idea.
Do not load personal context for unrelated work.

Turn the request into a few search facets: the motivating problem, desired
experience, behavior, design, constraints, earlier objections and later
corrections. Use the owner's actual terminology, aliases and examples once
found. Search complementary parts as well as paraphrases. Two pieces may belong
to the same idea while sharing no words. A shared project name alone does not
establish that they belong together.

Prepare a bounded local packet:

```sh
thought-reconstruction reclaim 'notes app' \
  --query 'semantic relationships between notes' \
  --query 'write from my own reasoning'
```

Additional inputs can be passed with `--source PATH`. Use `--owner-source PATH`
only when the user or source context establishes authorship of otherwise
unattributed notes. That assertion is recorded. A path selected for reading is
not itself proof of authorship. Inspect pasted dialogue and assistant prose at
fragment level before asserting authorship. A note maintained or adopted by the
owner can contain another author's text. Retain that useful prior work with its
attribution and actual adoption evidence. Do not reclassify assistant or peer
messages by passing an owner flag.

The packet starts with the shared local dense transformer route in
the bundled plugin's `scripts/archive_access.py`. It uses the private
Protect Your Energy configuration by default, records the actual generation and
indexed coverage, and hydrates bounded original parents with source hash and
message-version checks. No `--semantic-index` argument is needed. A missing or
unreadable saved library does not block shared archive discovery. The configured
library and explicit inputs remain a separately labelled lexical supplement.
Use `--archive-access-config PATH` for a different shared private configuration
and `--year YYYY` for an available year. Read the actual selected generation's
reported scope before assuming which source families or dates are available.
The active configuration may still select an older, partial Discord generation
while a refreshed archive builds. Planned sources are not indexed coverage;
publication and successful retrieval checks establish what that generation can
provide. Notes, AI history and earlier years require their own coverage checks.

Read `discovery_retrieval`, `discovery_originals` and the discovery lead parent
locators before using library interpretations. Truncated query metadata is
expanded through `parents --unit-id HASH --generation NAME` to recover the
complete original parent list from the pinned generation. Actual text hydration
is bounded at six lead units, 32 distinct parents and 45 seconds. Unread parents
remain listed for resumption. Expand clipped or unfinished
exchanges and additional unit parents through the same helper's `hydrate`
command. Dense failure is reported without silently substituting lexical search.
An explicitly supplied legacy `--semantic-index` is used only when the shared
route is not configured, and is labelled unhydrated legacy vector discovery.

The initial packet also covers the configured library and explicit inputs. Read its
coverage, rejected inputs and drift information before trusting it. It ranks
leads; it does not certify that every selected fragment belongs to the idea.
Existing model reconstructions are previous interpretations, never substitutes
for the original statements.

Make a default bounded coverage probe across the available Discord, Notes and
AI-history sources for the specific idea, even when the initial packet seems
coherent. Record absent, unreadable and unindexed source types. A narrow library
cannot reveal all the pieces it never held. Use the existing local archive
retrieval CLI or the optional local semantic index. Follow the returned
locators into the original records. Semantic windows may contain several
speakers or clipped passages. Index role filters and similarity scores do not
establish the author, endorsement, importance or full meaning of a statement.
Respect the index's existing sealed-store guards. Do not open request-only
material for a general reclamation request.

For the owner's local archive, use the shared route first:

```sh
python3 "$PYE_PLUGIN_ROOT/scripts/archive_access.py" query \
  --query 'the intended experience and reason, expressed in different words'
```

Its `auto` route is actual local transformer retrieval. Use explicitly labelled
`--mode lexical` or `--mode paths` for complementary exact lookups. Source
metadata matching through `catalog` is not semantic message retrieval. Follow
the reported original path, message ID, hash and version through `hydrate`.
Source scope or runtime faults require repair; no hit is not archive absence.

An optional SSD-only configuration can read verified replica files while retaining
historical source paths and hashes in receipts. Honor its configured source
restrictions. Derived inputs remain supplements, and moving bytes does not
establish original authorship.

An optional installation-specific retrieval backend can provide complementary
read-only lexical lookups. Configure its location explicitly, bound its scope,
and verify returned leads against original records.

Read entire relevant exchanges: expand beyond a clipped window until the
referent, reply, correction and outcome are clear. Deduplicate export snapshots
by platform, conversation and message ID. Preserve disagreements between
versions. Keep dated recurrence; repeated exports are not repeated evidence.
Keep all owner turns that complete a thought, including short replies. Before
joining pieces, record one sentence explaining their shared purpose, mechanism
or revision relationship. Separate valid citations do not establish that two
pieces belong to one idea.

Alternate reading with further search. New names, examples, missing constraints
and unresolved references determine the next query. Start a usable draft or
implementation once enough supported requirements exist. During substantial
building, keep a source investigator working alongside the builder. New
evidence can refine the design while the artifact is taking shape.

Use up to three retrieval rounds as an initial working budget, then continue
bounded probes for questions and requirements revealed by implementation.
Record new findings as dated design changes and apply them to the draft or
code. Two passes without a new relevant piece can close that particular query;
they do not close investigation of the whole design. Report outstanding source
coverage with each completed increment. These are practical budgets, not
research-backed proofs of completeness.

## Write the continuation

Use a private evidence ledger while drafting. For each substantive statement,
record the relevant source/message IDs, dates and speaker, and whether it is
expressed by the owner, your reconstruction, prior AI work or a new proposal.
Keep these mechanics out of the main prose unless they change the user's
decision. Date corrections and make their effect on the current interpretation
explicit. The current user correction overrides the old reading; do not delete
the old record.

Preserve why and how a decision was made, plus the conditions under which it
still applies. A proposed file format or tool can be an initial representation
of the idea. Determine which desired behavior survives a mechanism change.
Bring uncertainty and operating detail into view at the stage where they
affect an action. Retain supplied information rather than asking for it again.

First recover why the idea matters and how it should feel and behave. Then
recover the mechanism, rejected options, boundaries and next useful action.
Treat casual Discord brainstorming as possible experiential specifications:
"this should feel like…" can be the most important requirement. Determine
whether a later technical suggestion was endorsed, changed or only explored.
Silence, a reply to a different topic and continued conversation are not assent.

Ground a draft in relevant owner-authored examples from a similar setting.
Select examples for the current task and audience. A useful situation-specific
guide can change as the sources reveal new priorities; retain episodes that
challenge it rather than filtering them out to force consistency.
Preserve directness, technical depth and legitimate disagreement when those
serve the idea. Do not imitate a distressed passage as a universal personality.
Avoid generic imitation, invented autobiographical claims, asserted hidden
motives and commitments that the owner never made. First-person drafts are
drafts in the owner's voice, with new reasoning marked where it matters.

The owner's account receives the main attention. Peer context explains how a
conversation unfolded and where expectations conflicted. It cannot establish
the owner's intent or automatically invalidate it. An unsupported claim remains
unsupported whichever speaker made it. Preserve credibility by making the
strongest account the evidence can sustain and correcting weak claims before
they become part of the continuation.

Research only the unresolved mechanisms whose answer affects the next action.
Use primary papers, official implementations and documentation. Explain why a
method fits this problem and what its evaluation did not establish. Prefer
reusing available retrieval before adding a graph, training a persona model or
rebuilding the archive. Never submit private fragments as web-search queries.

For a complex idea, use a separate critic to check missing constraints, mixed
attribution, incorrect mergers, temporal contradictions and unsupported bridges.
The critic should see the evidence, not only the draft. Resolve disagreements
against the sources. Agreement among agents is not independent verification.

Deliver the usable artifact first: a coherent idea or draft, the next concrete
action, and only the open decisions that matter. Put full provenance and
coverage in its private companion. Do not make the user approve every fragment
or read a scoring dashboard before receiving the draft. Carry out authorized
reversible work when it is requested; writing a task description alone may not
complete an implementation request.

## Improve from real use

Keep each packet and reconstruction outside the raw archive with private
permissions. Retain the retrieval queries, selected sources, source hashes,
excluded or unresolved leads, revisions and material owner corrections. Do not
silently make an unreviewed reconstruction authoritative in the library.
Keep the current unfinished action and verifiable source or code bookmarks
with the idea so resuming it does not restart the same explanation. If tooling
blocks implementation, provide a concrete sketch or flow to develop the idea
while continuing the authorized work; record what still prevents completion.

The useful measures are recovered requirements, incorrect additions, changes
preserved, exact citation integrity, amount of owner rewriting, number of
clarification turns and time until a useful draft. Fluency and object counts
alone cannot measure thought recovery.

Evaluate future automatic merging on independently labelled real ideas across
different sources and dates, including same-topic decoys and later corrections.
Keep a held-out set separate from tuning examples. Compare this workflow with
the previous substring search and one-pass summary. Do not claim accuracy or
completeness percentages until those comparisons have been performed.

The next engine improvement is verified assembly of complementary pieces
across batches. An iCloud connector and large graph are later decisions driven
by demonstrated retrieval failures. The current command can read explicitly
selected supported exports; it does not synchronize iCloud or accept every
binary format.
