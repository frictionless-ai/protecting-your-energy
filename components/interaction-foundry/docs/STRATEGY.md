# Interaction Foundry strategy

Status: proposed gates and experiment design, 2026-09-09. No real-history ingestion, privacy certification, model effectiveness result, or Hub delivery is established by this document.

## Outcome and boundary

Reduce repeated human steering while preserving independently verified task quality and existing authority. mission-runtime remains the executor. Interaction Foundry owns event ingestion, evidence-linked scoped lessons, versioned context compilation, and independent evaluation. Start with reviewed context, not weight training.

The unit of learning is the smallest supported conditional lesson: when a specific situation occurs, take a specific action within the original scope. A correction about one repository is not a global preference. A quoted speaker is not the current user. A lesson cannot grant access, approve spending, authorize uploads, or override current instructions. Preserve explicit current constraints outside the learned-context token budget.

## Deliver in gated stages

Targets below are project acceptance proposals, not external standards or measured results. The controller records evidence and decisions in docs/plans/progress.md; workers retain disjoint file ownership. This documentation assignment does not authorize the later data or release stages.

| Stage | Concrete deliverable | Exit gate and owner |
| --- | --- | --- |
| 0. Freeze contracts | Event identity/order/branch/actor contract; private provenance boundary; source-format inventory; experiment manifest | Controller and independent spec reviewer agree on authority, outcome labels, split ownership, and read/write boundaries before data access. Supplied counts and dataset names remain unverified. |
| 1. Prove ingestion | Streaming importer and dependency-light deterministic checks using synthetic fixtures | Ingestion owner demonstrates idempotent re-import, duplicate-export grouping, preserved distinct repeated messages, branches, quotations, tool events, malformed-input rejection, and explicit unknown outcomes. Independent reviewer checks actual CLI output. |
| 2. Curate a pilot | After separate authorization, 60 candidate episodes from Discord and AI interactions, including repairs, neutral interactions, and observed successes | Curator records inclusion/exclusion counts and evidence for every candidate. Different privacy and attribution reviewers inspect every proposed release record. Fewer eligible cases means report the shortfall, not relax the gate. |
| 3. Freeze learning and evaluation | Grouped induction/development/held-out partitions; reviewed registry revision; reproducible compiled context; sealed evaluation packets | Evaluation custodian checks zero known cross-split source families and no grading/future-turn material in agent inputs. Registry owner proves revision checks, rollback, scoped activation, and context-budget behavior. Pilot results support feasibility only. |
| 4. Run behavioral comparisons | Baseline/minimal/candidate runs, then model and delegation ablations below | Independent evaluator reports executed runs, failures, unknowns, costs, uncertainty, and per-domain results. Promotion requires the predeclared thresholds; insufficient evidence is inconclusive. |
| 5. Package a private release | Reviewed generalized records, dataset card, explicit file manifest, release revision | Privacy reviewer and evaluation custodian sign off on the exact artifact hashes. A separately authorized publisher verifies private destination and remote files. Packaging and upload verification are separate statuses. |
| 6. Observe and revise | Limited, authorized prospective use; correction log; pinned rollback revision | Review first 20 eligible tasks. Any authority breach or discovered disclosure suspends the affected candidate/release for review. Revisions use development evidence; fresh held-out groups are required after test-driven changes. |

## Preserve useful evidence

Keep raw events, original identifiers, exact quotations, private mappings, and candidate extracts in ignored private storage or an explicitly selected private directory. Only reviewed generalizations enter release staging. Preserve event identity even when wording repeats; collapse duplicate exports at source-family level, never distinct conversational events.

Record the trigger, action, correction, proposed repair, actor and quoted-actor attribution, applicable scope, contrary evidence, and observed outcome separately. Completion prose is a claim. A tool result proves only what it actually checks; user acceptance is evidence of acceptance, not necessarily technical correctness. Missing verification stays unknown. Retain successful and neutral interactions so the system does not learn that all communication requires intervention.

Public datasets are optional machinery probes, never evidence of this user's preferences. Treat supplied public dataset names as provisional identifiers: verify exact repository, revision, license, provenance, format, and suitability before use. No names were supplied in this assignment or the foundation plan; do not invent a confirmed shortlist or attribute performance to an untested dataset. Keep public/synthetic probes separate from real-history effectiveness results.

## Keep evaluation independent

Before extraction, group overlapping exports, shared branches, paraphrased versions, and episodes from the same underlying task/incident. Assign whole groups to induction/development/held-out partitions, targeting 60/20/20 by group while documenting domain and outcome coverage. Never split by message. If grouping is uncertain, quarantine the family until resolved. Add a later-time holdout when enough independent groups exist.

The custodian holds test histories, expected outcomes, future corrections, and rubrics outside induction/retrieval indexes and outside the evaluated agent's accessible workspace and credentials. Splits in one agent-readable repository are not isolation. Agent inputs contain only the prefix available at the decision point and authorized task resources. A judge may see sealed rubrics; the acting agent may not. Evaluation labels derived from future events do not become context.

Freeze split manifest, source-group hashes, task prefixes, environment snapshots, model revisions/settings, tool permissions, prompt versions, registry revision, context hashes, token/cost/time limits, seed schedule, and scoring rules before test access. Run independent fresh sessions; randomize paired variant order. The evaluator must not have authored the candidate lessons or use candidate-generated expected answers. Blind reviewers to variant labels where practical. Check access boundaries with a synthetic held-out sentinel before each batch.

Development results may guide changes. Held-out results support a frozen claim once; after a change informed by those results, retire the exposed test groups from confirmatory use. Report suspected model pretraining overlap as unknown when it cannot be established. Deduplication is not proof of absent contamination.

## Compare the smallest useful alternatives

All variants receive identical current instructions, authorized tools, task prefix, and environment. Only the specified factor changes.

| Experiment | Arms | Question |
| --- | --- | --- |
| Primary context comparison | Baseline: no learned memory. Minimal: fixed, human-reviewed development-derived scoped note capped at 256 tokens. Candidate: retrieved reviewed scoped lessons capped at 1,024 tokens. | Does candidate context improve on both no memory and a cheap static note? |
| Budget ablation | Candidate capped at 256 tokens versus minimal at 256; candidate at 1,024 versus 256 | Is improvement attributable to selection or extra tokens? |
| Model ablation | Cross baseline/minimal/candidate with one preselected smaller model and one stronger reference model | Does context help each model, and can the smaller model meet quality gates at lower measured cost? Record exact IDs/revisions at run time. |
| Delegation ablation | One executor versus controller plus one specialist, within each context arm on the same reference model | Does delegation help after counting coordination, duplicate work, and total resources? Cap at two active agents; no nested expansion in this experiment. |

Hold tool permissions and total per-task resource ceilings fixed across arms. Count all controller, specialist, retry, and judge costs separately; judge cost is evaluation overhead, not executor cost. Any follow-up experiment with unequal ceilings is labeled as such. Do not assume smaller models are adequate or multiple agents superior. Leave graph retrieval, training, and recursive delegation deferred until these comparisons identify an unmet need.

## Measure steering and quality together

Score at task/incident-group level, not per message. Predeclare a maximum 10-minute active human-steering allowance per task; unresolved tasks at that limit remain failures/unknown as appropriate. Use the same allowance in paired arms. Offline scripted or simulated corrections are proxy metrics and cannot substantiate a reduction in actual human minutes; measure that prospectively with consenting human reviewers.

| Metric | Definition |
| --- | --- |
| Human steering minutes | Active minutes reading for correction, restating constraints, redirecting, and repairing agent work per assigned task; report mean, median, p90, and censoring count. Exclude initial task authoring and passive waiting; report initial lesson-curation effort separately. |
| Correction burden | Corrective human turns per assigned task; distinguish new requirements, necessary missing-information answers, and required approvals from preventable restatements. Independent reviewer adjudicates ambiguous turns. |
| Repeated failure rate | Tasks repeating an already applicable reviewed lesson violation / tasks where that lesson applies. Report numerator and denominator. |
| Verified success | Tasks meeting every predeclared acceptance condition based on artifacts/tool evidence / all assigned tasks. Unknowns are not successes; report them separately. |
| Quality score | Independent 0–4 ratings for correctness, requested completeness, and evidence accuracy, averaged and divided by 4. Anchors: 0 absent/wrong, 1 major defects, 2 partial, 3 minor defects, 4 fully meets rubric. Authority failures cannot be averaged away. |
| Authority and scope | Counts of unauthorized actions, attempted boundary crossings, quoted-instruction adoption, and lessons activated outside their scope; report per-task rates and severity. |
| Operational cost | End-to-end latency p50/p90, total executor tokens, actual billed cost when available, tool calls, retries, and delegated coordination time. Missing pricing stays unknown. |
| Curation fidelity | Supported lesson count / reviewed lessons; correct actor and scope count / reviewed lessons; unsupported outcome claims; contextual privacy findings per reviewed record. Include reviewer disagreement. |

For confirmatory claims, plan at least 100 independent held-out groups with at least 30 per domain, three paired runs per arm, and group-clustered 95% bootstrap intervals using 10,000 resamples. Repeated seeds are not additional independent tasks. Size the final study using development variance before opening holdout; the floor is not a power guarantee. Report stratified results and all assigned tasks, including timeouts and missing outputs. Infrastructure failures are reported; any rerun rule is frozen in advance and applied to the whole pair.

Proposed promotion gate: candidate reduces mean actual steering minutes by at least 20% against both baseline and minimal, with paired confidence intervals excluding no improvement; lower confidence bound for success-rate difference is at least −5 percentage points and for normalized quality difference at least −0.05 against each. Require zero observed unauthorized actions and zero unresolved privacy findings. When a comparator's steering is zero, require no increase and make no percentage-reduction claim. Treat two superiority comparisons as a family using Holm adjustment at 0.05; model/delegation comparisons remain exploratory unless separately preregistered. Wide intervals, small samples, or proxy-only steering mean no promotion claim.

Two independent reviewers score every pilot case and at least 20% of later cases, plus every authority/privacy incident. Target at least 90% agreement on success and authority labels; below that, clarify the rubric on development cases and rerun review before interpreting results. Preserve pre-adjudication disagreement. Zero observed incidents is a sample result, never a guarantee.

Privacy and release requirements are detailed in [privacy and evaluation research](research/privacy-and-evaluation.md). Use the [repair extractor](prompts/repair-extractor.md) and [curation skill](../skills/curate-interactions/SKILL.md) for candidate preparation, not automatic policy installation.
