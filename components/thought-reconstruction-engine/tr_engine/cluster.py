"""Group extracted candidates that carry the same underlying thought.

Greedy single-pass clustering on normalized-token Jaccard overlap of
title + quote. Stdlib only, deterministic. LLM mode adds a refinement
pass that merges clusters token overlap cannot see (the same thought
restated in different words months apart).
"""
import re
import sys

from . import llm

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common words that would create false overlap between unrelated fragments.
_STOPWORDS = frozenset("""
a about after all also an and any are as at be because been but by can could
did do does for from get got had has have he her him his how i if in into is
it its just like me my no not of on or our out she so some than that the their
them then there these they this to too up us was we were what when where which
who why will with would you your
""".split())


def tokens(text):
    return frozenset(t for t in _TOKEN_RE.findall(text.lower())
                     if t not in _STOPWORDS and len(t) > 1)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def slugify(text, fallback="thought"):
    words = _TOKEN_RE.findall(text.lower())[:6]
    slug = "-".join(words)
    return slug or fallback


def cluster(records, threshold=0.35):
    """Assign a 'cluster' slug to every record (in place, returned).

    Each record joins the first existing cluster whose accumulated token set
    overlaps its own tokens at >= threshold Jaccard, else starts a new one.
    Cluster slug comes from the title of the cluster's first member.
    """
    clusters = []  # list of {"tokens": set, "members": [record, ...]}
    for rec in records:
        toks = tokens(rec.get("title", "") + " " + rec.get("quote", ""))
        best = None
        best_score = threshold
        for c in clusters:
            score = jaccard(toks, c["tokens"])
            if score >= best_score:
                best = c
                best_score = score
        if best is None:
            clusters.append({"tokens": set(toks), "members": [rec]})
        else:
            best["tokens"] |= toks
            best["members"].append(rec)

    _assign_slugs(clusters)
    return records


def _assign_slugs(clusters):
    used = set()
    for i, c in enumerate(clusters):
        slug = slugify(c["members"][0].get("title", ""), fallback="thought-%d" % i)
        base = slug
        n = 2
        while slug in used:
            slug = "%s-%d" % (base, n)
            n += 1
        used.add(slug)
        for rec in c["members"]:
            rec["cluster"] = slug


def refine_llm(records):
    """Merge clusters that carry the same underlying thought restated in
    different words. One CLI call over the cluster representatives (first
    member's type + title); on any failure the heuristic clusters stand.

    Groups the same recurring thought, not the same topic: fragments that
    merely share a product area stay separate objects."""
    order = []
    reps = {}
    for rec in records:
        slug = rec["cluster"]
        if slug not in reps:
            reps[slug] = rec
            order.append(slug)
    prompt = (
        "Below are numbered thought fragments (type | title). Reply with JSON "
        "only: an array of arrays, each inner array the indices of fragments "
        "that carry the SAME underlying thought — the same specific idea, "
        "question, proposal or claim recurring or evolving over time. Do NOT "
        "group fragments that are merely about the same product, tool or "
        "topic area. Omit singletons. If nothing groups, reply [].\n\n"
    )
    for i, slug in enumerate(order):
        rec = reps[slug]
        prompt += "%d. %s | %s\n" % (i, rec.get("type", "?"),
                                     (rec.get("title") or "")[:140])
    try:
        groups = llm.ask_json(prompt)
    except llm.LLMError as e:
        print("cluster: LLM refine failed (%s); keeping token clusters" % e,
              file=sys.stderr)
        return records
    if not isinstance(groups, list):
        return records
    merged = {}  # old slug -> canonical slug (first index in its group)
    for g in groups:
        if not (isinstance(g, list) and len(g) > 1):
            continue
        idxs = [i for i in g if isinstance(i, int) and 0 <= i < len(order)]
        if len(idxs) < 2:
            continue
        canon = order[min(idxs)]
        for i in idxs:
            merged[order[i]] = canon
    n = 0
    for rec in records:
        canon = merged.get(rec["cluster"])
        if canon and canon != rec["cluster"]:
            rec["cluster"] = canon
            n += 1
    if n:
        print("cluster: LLM refine merged %d record(s) across %d group(s)"
              % (n, len({v for v in merged.values()})), file=sys.stderr)
    return records
