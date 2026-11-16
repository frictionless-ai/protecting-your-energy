"""Extract candidate thought objects from fragments.

Candidate record: fragment fields + {"type": <ontology type>, "title": str}.
"""
import json
import re
import sys

from . import llm

TYPES = ["idea", "observation", "hypothesis", "belief", "question", "problem",
         "solution", "concept", "prediction", "discovery", "preference", "goal"]

# Heuristic typing: ordered (first match wins), all matched case-insensitively
# against the fragment text. Deliberately simple so the pipeline runs offline.
_RULES = [
    ("question", [r"\?\s*$", r"^\s*(why|how come|is there a reason|what does|what is)\b"]),
    ("prediction", [r"\bi predict\b", r"\bwill (probably |likely )?(happen|end up|become)\b",
                    r"\bgoing to (be|become|end)\b"]),
    ("hypothesis", [r"\bmy (guess|theory|hypothesis)\b", r"\bprobably because\b",
                    r"\bmaybe because\b", r"\bi suspect\b"]),
    ("belief", [r"\bi (think|believe|feel like)\b", r"\bimo\b", r"\bin my opinion\b",
                r"\bi'?m convinced\b"]),
    ("idea", [r"\bwhat if\b", r"\bidea\b", r"\bwe could\b", r"\bcould (make|build|do|use)\b",
              r"\bimagine if\b"]),
    ("discovery", [r"\bturns out\b", r"\bi (learned|discovered|found out)\b",
                   r"\btil\b", r"\brealized that\b"]),
    ("observation", [r"\bi noticed\b", r"\bi'?ve (seen|noticed)\b", r"\bseems like\b",
                     r"\bi realized\b", r"\bapparently\b"]),
    ("problem", [r"\bproblem\b", r"\bthe issue\b", r"\bbroken\b", r"\bannoying\b",
                 r"\bdoesn'?t work\b", r"\bpain point\b"]),
    ("solution", [r"\bsolution\b", r"\bfix(ed|es)? (it|this|that|by)\b", r"\bworkaround\b",
                  r"\bthe way to solve\b"]),
    ("goal", [r"\bgoal\b", r"\bi want to\b", r"\btrying to\b", r"\baiming (to|for)\b"]),
    ("preference", [r"\bi prefer\b", r"\bi'?d rather\b", r"\bi (like|love|hate)\b"]),
    ("concept", [r"\bmental model\b", r"\bconcept\b", r"\babstraction\b",
                 r"\bthink of it as\b"]),
]
_COMPILED = [(t, [re.compile(p, re.IGNORECASE) for p in pats]) for t, pats in _RULES]


def heuristic_type(text):
    """Keyword/pattern typing with 'observation' as the neutral default."""
    for typ, pats in _COMPILED:
        for p in pats:
            if p.search(text):
                return typ
    return "observation"


def make_title(text, limit=140):
    """First sentence of the fragment, whitespace-collapsed, hard-capped."""
    flat = " ".join(text.split())
    m = re.search(r"[.!?]\s", flat)
    title = flat[:m.end()].strip() if m else flat
    if len(title) > limit:
        title = title[:limit - 1].rstrip() + "…"
    return title or "untitled"


def extract_heuristic(fragments):
    out = []
    for frag in fragments:
        rec = dict(frag)
        rec["type"] = heuristic_type(frag["quote"])
        rec["title"] = make_title(frag["quote"])
        out.append(rec)
    return out


def extract_llm(fragments, batch_size=20):
    """LLM typing/titling in batches; any failed batch falls back to the
    heuristic so a flaky CLI never kills the run."""
    out = []
    for i in range(0, len(fragments), batch_size):
        batch = fragments[i:i + batch_size]
        prompt = (
            "You classify personal thought fragments. For each numbered fragment "
            "below, reply with a JSON array of objects "
            '{"index": <int>, "type": <one of %s>, "title": "<one line, <=120 chars>"}. '
            "Reply with JSON only.\n\n" % json.dumps(TYPES)
        )
        for j, frag in enumerate(batch):
            prompt += "%d. %s\n\n" % (j, frag["quote"][:1500])
        try:
            rows = llm.ask_json(prompt)
            by_index = {}
            for row in rows:
                if isinstance(row, dict) and isinstance(row.get("index"), int):
                    by_index[row["index"]] = row
            for j, frag in enumerate(batch):
                rec = dict(frag)
                row = by_index.get(j, {})
                typ = row.get("type")
                rec["type"] = typ if typ in TYPES else heuristic_type(frag["quote"])
                title = row.get("title")
                rec["title"] = (title.strip()[:140] if isinstance(title, str) and title.strip()
                                else make_title(frag["quote"]))
                out.append(rec)
        except llm.LLMError as e:
            print("extract: LLM batch failed (%s); using heuristic" % e,
                  file=sys.stderr)
            out.extend(extract_heuristic(batch))
    return out


def extract(fragments, use_llm, batch_size=20):
    if use_llm:
        return extract_llm(fragments, batch_size=batch_size)
    return extract_heuristic(fragments)
