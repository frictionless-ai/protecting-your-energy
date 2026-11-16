# Evaluation release contract v1

Private original events and public-shaped evaluation cases are different records. The private mapping connects them; no original source paths, hashes of plaintext, account IDs, or timestamps enter release files. Every release case carries separate privacy and fidelity decisions by distinct reviewers, each bound to the digest of the non-review case content.

Each case has exactly these fields:

```json
{
  "case_id": "case-opaque-id",
  "group_id": "group-opaque-id",
  "domain": "ai_conversation",
  "split": "test",
  "input": {"messages": [{"role": "user", "content": "generalized request"}], "context": "facts available before the decision"},
  "rubric": {"required": ["observable behavior"], "forbidden": ["observable failure"], "outcome_status": "unknown"},
  "provenance_kind": "generalized_real_episode",
  "review": {"privacy": "pending", "fidelity": "pending", "reviewer": "reviewer-role", "reviewed_content_sha256": "digest of case excluding review"}
}
```

Domains: discord, ai_conversation. Splits: development, validation, test. Outcomes: unknown, user_confirmed, tool_verified, contradicted. Never upgrade an assistant claim to verified.

Review values: pending, approved, rejected. Both privacy and fidelity must be approved and their digest must match current content before export. Reviewer is a generic role, not a personal identifier. Agent review must be disclosed as agent review, not human certification.

`input` is the only evaluated-model payload. `rubric` and future corrections remain grader-only. Corpus extraction can inspect outcomes, but a prediction input cannot contain evidence from after its decision boundary. Freeze group assignment before induction. Every source conversation and connected duplicate/overlapping export shares one group; generalizations of a case inherit that group.

Local records mapping case/group IDs to source locators and event IDs live only in ignored private/. Every released case must have such evidence and a documented generalization decision. Changes to source records invalidate dependent cases until re-reviewed. Release documentation states exclusions and sample coverage rather than implying complete anonymization or population coverage.

Before a release build, the private mapping must use
`interaction-foundry/private-provenance/v1`: a complete lineage flag, private
source-artifact references, a decision-boundary ordinal, input-event ordinals
at or before that boundary, and grader-event ordinals strictly after it. The
two sets cannot overlap. This is a structural gate against future-information
leakage; independent review still checks whether the generalized wording is
faithful to the permitted input events.

Validation checks schema, review digest, split disjointness, exact-content duplication, identifier patterns and caller-supplied deny terms. These are screening controls: contextual privacy/fidelity review is still required. No generated reviewer approval is a legal guarantee of anonymity.
