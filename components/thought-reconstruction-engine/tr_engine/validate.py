"""Stdlib validator for exactly schema/thought-object.schema.json (v1).

Hand-written for this one schema: required keys, additionalProperties: false,
enums, patterns, integer ranges. No jsonschema dependency.
"""
import re

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

TYPES = {"idea", "observation", "hypothesis", "belief", "question", "problem",
         "solution", "concept", "prediction", "discovery", "preference", "goal"}
STATUSES = {"active", "weak", "refuted", "abandoned"}
EVOLUTION_KINDS = {"originated", "refined", "contradicted", "context-dependent",
                   "restated", "abandoned"}
OUTLETS = {"essay", "y2-draft", "adamant", "public-operator", "none"}
SCORE_KEYS = {"coherence", "evidence", "originality", "usefulness",
              "feasibility", "significance", "maturity", "research_confidence"}

_TOP_KEYS = {"id", "type", "title", "reconstruction", "status", "cluster",
             "evidence", "evolution", "critique", "scores", "outlet"}
_REQUIRED = {"id", "type", "title", "reconstruction", "status", "evidence",
             "scores"}


def _check_obj_keys(errors, where, value, allowed, required):
    if not isinstance(value, dict):
        errors.append("%s: not an object" % where)
        return False
    for k in value:
        if k not in allowed:
            errors.append("%s: unexpected property %r" % (where, k))
    for k in required:
        if k not in value:
            errors.append("%s: missing required property %r" % (where, k))
    return True


def _check_str(errors, where, value, pattern=None, max_length=None, enum=None):
    if not isinstance(value, str):
        errors.append("%s: not a string" % where)
        return
    if pattern and not pattern.match(value):
        errors.append("%s: %r does not match pattern" % (where, value))
    if max_length is not None and len(value) > max_length:
        errors.append("%s: longer than %d chars" % (where, max_length))
    if enum is not None and value not in enum:
        errors.append("%s: %r not in enum" % (where, value))


def validate_object(obj):
    """Return a list of error strings; empty means valid."""
    errors = []
    if not _check_obj_keys(errors, "object", obj, _TOP_KEYS, _REQUIRED):
        return errors

    if "id" in obj:
        _check_str(errors, "id", obj["id"], pattern=SLUG_RE)
    if "type" in obj:
        _check_str(errors, "type", obj["type"], enum=TYPES)
    if "title" in obj:
        _check_str(errors, "title", obj["title"], max_length=140)
    if "reconstruction" in obj:
        _check_str(errors, "reconstruction", obj["reconstruction"])
    if "status" in obj:
        _check_str(errors, "status", obj["status"], enum=STATUSES)
    if "cluster" in obj:
        _check_str(errors, "cluster", obj["cluster"], pattern=SLUG_RE)

    ev = obj.get("evidence")
    if "evidence" in obj:
        if not isinstance(ev, list):
            errors.append("evidence: not an array")
        else:
            if len(ev) < 1:
                errors.append("evidence: needs at least 1 item")
            for i, item in enumerate(ev):
                where = "evidence[%d]" % i
                if _check_obj_keys(errors, where, item,
                                   {"source", "ref", "quote", "date"},
                                   {"source", "quote"}):
                    for k in ("source", "ref", "quote", "date"):
                        if k in item:
                            _check_str(errors, "%s.%s" % (where, k), item[k])

    if "evolution" in obj:
        evo = obj["evolution"]
        if not isinstance(evo, list):
            errors.append("evolution: not an array")
        else:
            for i, item in enumerate(evo):
                where = "evolution[%d]" % i
                if _check_obj_keys(errors, where, item,
                                   {"date", "kind", "note"}, {"date", "kind"}):
                    if "date" in item:
                        _check_str(errors, where + ".date", item["date"])
                    if "kind" in item:
                        _check_str(errors, where + ".kind", item["kind"],
                                   enum=EVOLUTION_KINDS)
                    if "note" in item:
                        _check_str(errors, where + ".note", item["note"])

    if "critique" in obj:
        crit = obj["critique"]
        if not isinstance(crit, list):
            errors.append("critique: not an array")
        else:
            for i, item in enumerate(crit):
                where = "critique[%d]" % i
                if _check_obj_keys(errors, where, item,
                                   {"date", "finding"}, {"date", "finding"}):
                    for k in ("date", "finding"):
                        if k in item:
                            _check_str(errors, "%s.%s" % (where, k), item[k])

    if "scores" in obj:
        scores = obj["scores"]
        if _check_obj_keys(errors, "scores", scores, SCORE_KEYS, SCORE_KEYS):
            for k, v in scores.items():
                if k not in SCORE_KEYS:
                    continue
                # bool is an int subclass; the schema means real integers
                if isinstance(v, bool) or not isinstance(v, int):
                    errors.append("scores.%s: not an integer" % k)
                elif not 0 <= v <= 100:
                    errors.append("scores.%s: %d out of range 0-100" % (k, v))

    if "outlet" in obj:
        outlet = obj["outlet"]
        if _check_obj_keys(errors, "outlet", outlet, {"suggested", "note"}, set()):
            if "suggested" in outlet:
                _check_str(errors, "outlet.suggested", outlet["suggested"],
                           enum=OUTLETS)
            if "note" in outlet:
                _check_str(errors, "outlet.note", outlet["note"])

    return errors
