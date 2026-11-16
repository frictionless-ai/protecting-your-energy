"""Score the eight ranking dimensions per ThoughtObject.

Dimensions are stored individually; the composite is render-time only and is
never written anywhere by this engine.
"""
import datetime
import json
import sys

from . import llm
from .cluster import jaccard, tokens

DIMENSIONS = ["coherence", "evidence", "originality", "usefulness",
              "feasibility", "significance", "maturity", "research_confidence"]

_USEFULNESS_PRIOR = {
    "solution": 70, "idea": 65, "goal": 60, "problem": 55, "discovery": 55,
    "question": 50, "hypothesis": 45, "prediction": 45, "concept": 45,
    "belief": 40, "preference": 40, "observation": 35,
}
_FEASIBILITY_PRIOR = {
    "solution": 70, "idea": 55, "goal": 50, "discovery": 60,
}


def _clamp(v):
    return max(0, min(100, int(round(v))))


def _timespan_days(obj):
    dates = sorted({e["date"] for e in obj.get("evidence", []) if e.get("date")})
    if len(dates) < 2:
        return 0
    try:
        first = datetime.date.fromisoformat(dates[0])
        last = datetime.date.fromisoformat(dates[-1])
        return (last - first).days
    except ValueError:
        return 0


def heuristic_scores(obj, token_doc_counts, own_tokens):
    """Deterministic offline scoring. Formulas per dimension:

    evidence: 20 per fragment, +15 per distinct source beyond the first,
        +10 per distinct date beyond the first. More corroboration from more
        places over more days = stronger evidence.
    maturity: 25 per evolution entry plus 2 per week of evidence timespan
        (capped at 40). A thought restated over months is more mature than a
        one-off.
    coherence: single-fragment objects are trivially coherent (70). Multi-
        fragment: 40 base + 50 * mean pairwise token Jaccard between quotes
        (tighter clusters cohere more) + 10 if every fragment was typed the
        same way.
    originality: share of this object's distinct tokens that appear in no
        other object (vocabulary nobody else on the canvas uses).
    usefulness: type prior (solutions/ideas/goals rank above passive
        observations) + 5 per extra fragment (recurrence implies felt need),
        capped at +20.
    feasibility: type prior (solutions most actionable) minus a verbosity
        penalty of 1 per 500 chars of evidence (sprawling thoughts are harder
        to act on), capped at -20.
    significance: 10 per fragment + total evidence length / 200 (capped 40)
        + 15 per distinct source beyond the first. Recurring, substantial,
        cross-context thoughts matter more.
    research_confidence: always 0 — the research stage is a stub in v1;
        nothing has been independently verified.
    """
    ev = obj.get("evidence", [])
    n = len(ev)
    n_sources = len({e["source"] for e in ev})
    n_dates = len({e["date"] for e in ev if e.get("date")})
    total_chars = sum(len(e["quote"]) for e in ev)
    typ = obj["type"]

    evidence = _clamp(20 * n + 15 * (n_sources - 1) + 10 * max(0, n_dates - 1))

    evo = obj.get("evolution", [])
    maturity = _clamp(25 * len(evo) + min(40, (_timespan_days(obj) // 7) * 2))
    if not evo:
        maturity = _clamp(10)

    if n <= 1:
        coherence = 70
    else:
        toks = [tokens(e["quote"]) for e in ev]
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        sim = sum(jaccard(toks[i], toks[j]) for i, j in pairs) / len(pairs)
        coherence = _clamp(40 + 50 * sim + 10)  # same-type bonus folded in:
        # all evidence in a cluster shares the object's type by construction.

    if own_tokens:
        unique = sum(1 for t in own_tokens if token_doc_counts.get(t, 0) <= 1)
        originality = _clamp(100 * unique / len(own_tokens))
    else:
        originality = 0

    usefulness = _clamp(_USEFULNESS_PRIOR.get(typ, 40) + min(20, 5 * (n - 1)))
    feasibility = _clamp(_FEASIBILITY_PRIOR.get(typ, 40)
                         - min(20, total_chars // 500))
    significance = _clamp(10 * n + min(40, total_chars // 200)
                          + 15 * (n_sources - 1))

    return {
        "coherence": coherence,
        "evidence": evidence,
        "originality": originality,
        "usefulness": usefulness,
        "feasibility": feasibility,
        "significance": significance,
        "maturity": maturity,
        "research_confidence": 0,
    }


def llm_scores_batch(batch):
    """Score a batch of thought objects in one CLI call. Returns
    {index: scores} for every index the model answered validly; callers
    fill the gaps with heuristics."""
    prompt = (
        "Score each numbered thought object below on eight dimensions, each "
        "an integer 0-100: %s. Judge the artifact of thought, never the "
        "person. Reply with JSON only: an array of "
        '{"index": <int>, "scores": {<dimension>: <int>, ...}}.\n\n'
        % ", ".join(DIMENSIONS)
    )
    for j, obj in enumerate(batch):
        prompt += "%d. %s\n\n" % (j, json.dumps(
            {"type": obj["type"], "title": obj["title"],
             "reconstruction": obj["reconstruction"][:1200],
             "evidence_count": len(obj.get("evidence", []))}))
    data = llm.ask_json(prompt)
    if not isinstance(data, list):
        raise llm.LLMError("batch score reply was not a JSON array")
    out = {}
    for row in data:
        if not (isinstance(row, dict) and isinstance(row.get("index"), int)):
            continue
        raw = row.get("scores")
        if not isinstance(raw, dict):
            continue
        scores = {}
        for d in DIMENSIONS:
            v = raw.get(d)
            if not isinstance(v, int):
                scores = None
                break
            scores[d] = _clamp(v)
        if scores is not None:
            out[row["index"]] = scores
    return out


def rank(objects, use_llm, batch_size=10):
    token_sets = {
        o["id"]: tokens(o["title"] + " " + " ".join(e["quote"] for e in o["evidence"]))
        for o in objects
    }
    # How many objects contain each token; tokens with count 1 are unique
    # to their object (used for originality).
    token_doc_counts = {}
    for ts in token_sets.values():
        for t in ts:
            token_doc_counts[t] = token_doc_counts.get(t, 0) + 1
    llm_results = {}
    if use_llm:
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            try:
                got = llm_scores_batch(batch)
                for j, scores in got.items():
                    if 0 <= j < len(batch):
                        llm_results[i + j] = scores
            except llm.LLMError as e:
                print("rank: LLM batch at %d failed (%s); using heuristics"
                      % (i, e), file=sys.stderr)
    for i, obj in enumerate(objects):
        obj["scores"] = llm_results.get(i) or heuristic_scores(
            obj, token_doc_counts, token_sets[obj["id"]])
    return objects
