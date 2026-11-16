"""Merge each cluster into one ThoughtObject conforming to the schema.

Raw fragments stay attached verbatim in evidence[]; the reconstruction is the
revisable interpretation layered on top. Scores are zeroed here and filled by
the rank stage.
"""
import sys
from collections import Counter, OrderedDict

from . import llm

ZERO_SCORES = OrderedDict([
    ("coherence", 0), ("evidence", 0), ("originality", 0), ("usefulness", 0),
    ("feasibility", 0), ("significance", 0), ("maturity", 0),
    ("research_confidence", 0),
])


def _sorted_members(members):
    # Dated fragments first, oldest first; undated keep input order.
    return sorted(members, key=lambda r: (r.get("date") == "", r.get("date", "")))


def _evidence(members):
    out = []
    for m in members:
        ev = {"source": m["source"], "quote": m["quote"]}
        if m.get("ref"):
            ev["ref"] = m["ref"]
        if m.get("date"):
            ev["date"] = m["date"]
        out.append(ev)
    return out


def _evolution(members):
    """Only when the cluster spans multiple distinct dates: the earliest date
    is where the thought originated; each later date is a restatement."""
    dates = sorted({m["date"] for m in members if m.get("date")})
    if len(dates) < 2:
        return None
    entries = [{"date": dates[0], "kind": "originated",
                "note": "first recorded fragment"}]
    for d in dates[1:]:
        entries.append({"date": d, "kind": "restated",
                        "note": "fragment recorded again on this date"})
    return entries


def _deterministic_synthesis(typ, members):
    """--no-llm reconstruction: a plain header plus the distinct fragments in
    date order. Deterministic concatenation, no paraphrase."""
    seen = set()
    quotes = []
    for m in members:
        q = m["quote"]
        if q not in seen:
            seen.add(q)
            quotes.append(q)
    header = "%s reconstructed from %d fragment%s:" % (
        typ.capitalize(), len(members), "" if len(members) == 1 else "s")
    return header + "\n\n" + "\n\n---\n\n".join(quotes)


def _llm_synthesis_batch(items, batch_size=5):
    """Synthesize several clusters per CLI call. items: [(typ, title,
    members)]; returns {index: synthesis} for every index the model answered.
    A failed batch just leaves its indices out (deterministic fallback)."""
    out = {}
    for start in range(0, len(items), batch_size):
        chunk = items[start:start + batch_size]
        prompt = (
            "For each numbered recurring thought below, write a short "
            "revisable synthesis (2-5 sentences, first person preserved "
            "where the fragments use it). Do not average away "
            "contradictions; name them. Reply with JSON only: an array of "
            '{"index": <int>, "synthesis": "<prose>"}.\n\n'
        )
        for j, (typ, title, members) in enumerate(chunk):
            prompt += "%d. %s: %s\nFragments:\n" % (j, typ, title[:140])
            for m in members[:8]:
                prompt += "- [%s] %s\n" % (m.get("date") or "undated",
                                           m["quote"][:600])
            prompt += "\n"
        try:
            rows = llm.ask_json(prompt)
        except llm.LLMError as e:
            print("reconstruct: LLM batch at %d failed (%s); using "
                  "deterministic" % (start, e), file=sys.stderr)
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if (isinstance(row, dict) and isinstance(row.get("index"), int)
                    and isinstance(row.get("synthesis"), str)
                    and row["synthesis"].strip()
                    and 0 <= row["index"] < len(chunk)):
                out[start + row["index"]] = row["synthesis"].strip()
    return out


def reconstruct(records, use_llm):
    """One ThoughtObject per cluster slug. id == cluster slug (1:1 in v1)."""
    by_cluster = OrderedDict()
    for rec in records:
        by_cluster.setdefault(rec["cluster"], []).append(rec)

    prepared = []
    for slug, members in by_cluster.items():
        members = _sorted_members(members)
        typ = Counter(m["type"] for m in members).most_common(1)[0][0]
        title = members[0].get("title", "untitled")[:140]
        prepared.append((slug, typ, title, members))

    # A singleton cluster has nothing to synthesize — the fragment is the
    # reconstruction; LLM synthesis fires only for real merges, batched.
    syntheses = {}
    if use_llm:
        multi = [(i, p) for i, p in enumerate(prepared) if len(p[3]) > 1]
        got = _llm_synthesis_batch([(typ, title, members)
                                    for _, (_, typ, title, members) in multi])
        for j, (i, _) in enumerate(multi):
            if j in got:
                syntheses[i] = got[j]

    objects = []
    for i, (slug, typ, title, members) in enumerate(prepared):
        synthesis = syntheses.get(i) or _deterministic_synthesis(typ, members)

        obj = OrderedDict([
            ("id", slug),
            ("type", typ),
            ("title", title),
            ("reconstruction", synthesis),
            ("status", "active"),
            ("cluster", slug),
            ("evidence", _evidence(members)),
        ])
        evolution = _evolution(members)
        if evolution:
            obj["evolution"] = evolution
        obj["scores"] = dict(ZERO_SCORES)
        obj["outlet"] = {"suggested": "none", "note": ""}
        objects.append(obj)
    return objects
