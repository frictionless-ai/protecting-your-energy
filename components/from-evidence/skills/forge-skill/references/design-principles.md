# Design principles a forged artifact must satisfy

Each principle names the finding it rests on. Full citations are in the
research notes (`research_notes/Academic prompt engineering evidence/`) and
the report of the same name. Check the artifact against every row before
declaring it forged.

| # | Principle | Evidence | Check |
|---|---|---|---|
| 1 | Enumerate every benefit first (`## Benefits`, each with its evidence), then name the artifact for the payoff, verb + object. Never for the mechanism, never for a line the subject says. | Corrections ledger #3 and #9; plain-copy rule "CTAs = verb + object". | `Benefits` is a required section; `validate.py` rejects phrase-bank names. Read the name aloud as "/<name>": does it say what the user gets? |
| 2 | Say what it does, why it helps (mechanism + evidence), when to use it, when not to. | Horvitz 1999 (ask only when the answer changes the action); GoF pattern form Intent / Motivation / Applicability. | `IDENTITY_KEYS`; the block renders first. |
| 3 | At most six ranked rules at the top; everything else is background. | FollowBench: GPT-4 84.7% → 61.9% from one to five constraints; lost-in-the-middle 75.8 / 53.8 / 63.2 for start / middle / end. | `MAX_CORE_RULES`; rules render before anything else. |
| 4 | Verbatim dialogue inline beats a description. | RoleLLM few-shot dialogue 63.3% vs description 29.8% vs zero-shot 9.3%; Ditto; Character-LLM. | `## Inline exemplars`, 5–8 records, quality ≥ 4, training only. |
| 5 | Prohibitions carry markers; "must not" outlives "must do"; put them early. | RuLES; Jang 2022 negation inverse scaling (so keep them few and concrete). | Anti-patterns render second, each with markers `evaluate.py` can score. |
| 6 | A legal null move. A challenger that must find fault manufactures it. | CAI critiques "often inaccurate or overstated"; Self-Refine GSM prompt presupposes error; Huang 2023 self-correction loses accuracy. | Core rules include "that holds" as an outcome. |
| 7 | No folding to pushback without a new referent; no bare "are you sure?" as a move. | Sharma 2023: 32–86% answer flips on a bare challenge; Khan 2024 "do not concede". | Core rule; agent protocol. |
| 8 | Check before asserting fault. A critique with no retrieved evidence is not a critique. | CRITIC without tools ≤ baseline; Valmeekam verifier FPR 84%; Reflexion reflects only on confirmed failure. | Agent protocol: run the command / read the file:line first. |
| 9 | Distinct opposer, moderate disagreement, round cap 3–4, early stop. | Du 2023 agreeable clones; Liang MAD level 2 > level 3; Amayuelas always-attacker −10–40% group accuracy; ChatEval no gain after 2 rounds. | `## Agent protocol`; `templates/subagent.md` output ends with `stop:`. |
| 10 | The judge argued neither side, shares no backbone with the arguers, reads both orders, writes evidence before the verdict. | MAD Table 6 self-preference; Panickssery 73.5% self-recognition; Zheng 2023 65% order consistency; Wang 2023 52.7 → 62.5 with evidence-first. | `fidelity-judge` model differs from `skill-author`; scorecard records both orders. |
| 11 | Fidelity is measured on responses against a no-skill arm, on held-out prompts, never by searching the artifact for its own phrases. | PersonaChat revised personas; TinyStyler held-out embeddings; report §2. | Scorecard `verifies:` field; response run required for `pass`. |
| 12 | Prompt wording is a versioned hyperparameter; tag the scoring model; expect no cross-model transfer. | Sclar 2023 up to 76 points from formatting; APE "significant performance drop" across models; MIPRO. | `metadata.built-by` and dataset version in frontmatter; evaluate with ≥2 paraphrased prompts. |
| 13 | Demos first, instructions second; the growing dataset is a retrieval pool, not a longer prompt. | MIPRO bootstrap-demos beat instruction-only; KATE / EPR retrieval ≫ random; random demos saturate at k ≥ 8. | Inline exemplars capped at 8; the rest stay in `dataset/bank.jsonl` for retrieval. |
| 14 | Quality over quantity: quote only records rated ≥ 4. | LIMA 1k; AlpaGasus 9k filtered > 52k. | `QUOTABLE_QUALITY = 4`. |
| 15 | Every correction the user makes by hand becomes a validator, template or contract change. | Corrections ledger. | `CORRECTIONS.md` row with a `Where` column; open rows block release. |
