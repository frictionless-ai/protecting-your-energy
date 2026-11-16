"""Local retrieval: multi-field BM25 fused with reciprocal rank fusion.

Stdlib only, deterministic. Documents are {doc_id: {field: text}}. Queries
are a document's own owner-text terms, so every matched term is one the
querying document's owner wrote; a match only in another document's context
text is reported as a context match. Serves related links and, later, merge
candidate blocking.
"""
import collections
import math
import re

from . import cluster

FIELDS = ('owner', 'context', 'keys')
K1, B = 1.2, 0.75
RRF_K = 60
# A term in more than this share of documents is too common to index.
DF_CAP_SHARE = 0.10
# Absolute floors so small corpora (synthetic checks, benchmarks) still index.
DF_CAP_MIN = 20
RARE_DF = 3

# Coined forms in the source text: inner capitals (ModSync) or letter-digit mixes (v2api).
_COINED_RE = re.compile(r'\b(?:[A-Za-z]*[a-z][A-Z][A-Za-z0-9]*|(?=[A-Za-z]*\d)(?=\d*[A-Za-z])[A-Za-z0-9]{3,})\b')


def coined(text):
    return frozenset(t for w in _COINED_RE.findall(text) for t in cluster.tokens(w))


class Index:
    """Inverted per-field BM25 indexes over one corpus.

    ponytail: one in-memory inverted index; fine for tens of thousands of
    documents. Shard by source or year when postings for capped terms no
    longer fit in memory or a full related pass exceeds about a minute.
    """

    def __init__(self, docs):
        self.ids = sorted(docs)
        n = len(self.ids)
        self.cap = max(DF_CAP_MIN, int(n * DF_CAP_SHARE))
        self.terms = {}  # doc id -> owner terms (the query side)
        bags = {f: {} for f in FIELDS}
        for doc_id in self.ids:
            doc = docs[doc_id]
            owner = doc.get('owner', '')
            self.terms[doc_id] = cluster.tokens(owner)
            bags['owner'][doc_id] = _counts(owner)
            bags['context'][doc_id] = _counts(doc.get('context', ''))
        owner_df = _df(bags['owner'])
        for doc_id in self.ids:
            # Keys: coined forms plus owner terms rare across the corpus.
            keep = coined(docs[doc_id].get('owner', '')) | {t for t in self.terms[doc_id] if owner_df[t] <= RARE_DF}
            bags['keys'][doc_id] = collections.Counter({t: c for t, c in bags['owner'][doc_id].items() if t in keep})
        self.fields = {f: _Field(bags[f], n, self.cap) for f in FIELDS}
        # KTD3 gate: a link needs a shared term at or above the median idf of
        # shareable terms (in two or more documents, any field). idf falls as
        # df rises, so that is df at or below the median df. One corpus-wide
        # threshold, because a context match pairs one document's owner text
        # with another's context. "At or above", not "above": on Zipfian text
        # the median can be df 2, where "above" would admit no shared term.
        df = _df({d: set(bags['owner'][d]) | set(bags['context'][d]) for d in self.ids})
        shareable = sorted(c for c in df.values() if c > 1)
        self.median_df = shareable[len(shareable) // 2] if shareable else 0
        self.strong = {t for t, c in df.items() if 1 < c <= min(self.median_df, self.cap)}

    def search(self, doc_id, exclude=()):
        """Fused ranking for doc_id's owner terms: [(id, score, {field: terms})].

        A result needs at least one shared term in self.strong (KTD3), so
        shared common words alone never link. Terms are ordered rarest first.
        """
        query = self.terms[doc_id]
        skip = set(exclude) | {doc_id}
        # Only documents sharing a strong term can link, so rank just those.
        cands = {d for t in query & self.strong for f in ('owner', 'context')
                 for d in self.fields[f].postings.get(t, ())} - skip
        fused, matched = collections.defaultdict(float), collections.defaultdict(dict)
        for name, field in self.fields.items():
            for rank, (other, shared) in enumerate(field.rank(query, cands), 1):
                fused[other] += 1 / (RRF_K + rank)
                strong = sorted((t for t in shared if t in self.strong), key=lambda t: (-field.idf[t], t))
                if strong:
                    matched[other][name] = strong
        return sorted(((o, fused[o], matched[o]) for o in matched), key=lambda x: (-x[1], x[0]))


class _Field:
    def __init__(self, bags, n, cap):
        df = _df(bags)
        self.postings = collections.defaultdict(dict)
        self.length = {d: sum(b.values()) for d, b in bags.items()}
        self.avg = (sum(self.length.values()) / n) if n else 0
        for doc_id, bag in bags.items():
            for t, c in bag.items():
                if df[t] <= cap:
                    self.postings[t][doc_id] = c
        self.idf = {t: math.log(1 + (n - len(p) + .5) / (len(p) + .5)) for t, p in self.postings.items()}

    def rank(self, query, cands):
        """BM25 ranking of cands for query terms: [(id, shared terms)], best first."""
        scored = []
        for doc_id in cands:
            score, shared = 0.0, []
            for t in sorted(query):
                tf = self.postings.get(t, {}).get(doc_id)
                if tf:
                    norm = tf + K1 * (1 - B + B * self.length[doc_id] / (self.avg or 1))
                    score += self.idf[t] * tf * (K1 + 1) / norm
                    shared.append(t)
            if shared:
                scored.append((-score, doc_id, shared))
        return [(d, shared) for _, d, shared in sorted(scored)]


def _counts(text):
    keep = cluster.tokens(text)
    return collections.Counter(t for t in re.findall(r'[a-z0-9]+', text.lower()) if t in keep)


def _df(bags):
    df = collections.Counter()
    for bag in bags.values():
        df.update(set(bag))
    return df
