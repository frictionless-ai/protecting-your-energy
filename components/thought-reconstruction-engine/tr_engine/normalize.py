"""Normalize heterogeneous sources into one fragment record shape.

Fragment record: {"source": str, "ref": str, "quote": str, "date": "YYYY-MM-DD" or ""}.
Quotes stay verbatim (evidence-first): parsers select text, they never rewrite it.
"""
import json
import os
import re

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _date_of(text):
    m = DATE_RE.search(text or "")
    return m.group(1) if m else ""


def parse_thought_stream(path, label):
    """y2/THOUGHT-STREAM.md: '### Title' headers followed by '- key: value'
    bullet lines; the fragment text is the '- quote:' line, dated by '- ts:'."""
    frags = []
    title = None
    ts = ""
    msg_id = ""
    line_no = 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if line.startswith("### "):
                title = line[4:].strip()
                ts = ""
                msg_id = ""
                line_no = i
            elif line.startswith("- ts:"):
                ts = _date_of(line)
            elif line.startswith("- id:"):
                msg_id = line[5:].strip()
            elif line.startswith("- quote:") and title is not None:
                quote = line[len("- quote:"):].strip()
                if quote.startswith('"') and quote.endswith('"') and len(quote) > 1:
                    quote = quote[1:-1]
                if quote:
                    ref = msg_id if msg_id and msg_id != "session" else "L%d" % line_no
                    frags.append({"source": label, "ref": ref, "quote": quote, "date": ts})
    return frags


def parse_adamant(path, label):
    """y2/adamant.json: slug catalog {updated, count, entries:[{slug, section,
    adamant, principle, ids, ledger}]}. The 'adamant' field is the fragment
    text; entries carry no per-thought date (the file-level 'updated' stamp is
    a catalog date, not a thought date, so date stays empty)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    frags = []
    for e in data.get("entries", []):
        quote = (e.get("adamant") or "").strip()
        if not quote:
            continue
        frags.append({
            "source": label,
            "ref": e.get("slug", ""),
            "quote": quote,
            "date": "",
        })
    return frags


def parse_jsonl(path, label):
    """docs/essays/_sources/*.jsonl: one JSON object per line, fields vary.
    Text lives in 'content' (fall back to 'text'/'quote'); timestamp in
    'sent_at' (fall back to 'timestamp'/'date'); id in 'id'."""
    frags = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue  # skip unparseable lines, don't fail the source
            if not isinstance(row, dict):
                continue
            quote = None
            for key in ("content", "text", "quote"):
                v = row.get(key)
                if isinstance(v, str) and v.strip():
                    quote = v
                    break
            if quote is None:
                continue
            date = ""
            for key in ("sent_at", "timestamp", "date"):
                v = row.get(key)
                if isinstance(v, str):
                    date = _date_of(v)
                    if date:
                        break
            ref = str(row.get("id") or "L%d" % i)
            frags.append({"source": label, "ref": ref, "quote": quote, "date": date})
    return frags


# DM exports carry both sides of a conversation, but thought objects are
# reconstructed from the archive owner's messages only; the other side is
# context, not evidence. Explicit owner aliases identify export headers.
from .identity import OWNER_ALIASES as SELF_AUTHORS

DM_HEADER_RE = re.compile(r"^### (.+?) — (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(?:\s+·.*)?\s*$")


def looks_like_dm_markdown(path):
    """Sniff the first 200 lines for at least two '### Author — timestamp'
    headers so curated DM exports don't fall through to the paragraph parser."""
    hits = 0
    try:
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 200:
                    break
                if DM_HEADER_RE.match(line.rstrip("\n")):
                    hits += 1
                    if hits >= 2:
                        return True
    except (OSError, UnicodeDecodeError):
        return False
    return False


def parse_dm_turns(path):
    """Every '### Author — timestamp' turn of a curated DM export, in file order:
    {"author", "ref", "date", "body", "self"}. Both sides are kept so the other
    side can serve as context; only self turns may ever become evidence."""
    turns = []
    author = None
    ref = ""
    date = ""
    buf = []

    def flush():
        if author is not None:
            turns.append({"author": author, "ref": ref, "date": date,
                          "body": "\n".join(buf).strip(),
                          "self": author.strip().casefold() in SELF_AUTHORS})

    with open(path, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]
    framed_day = False
    for i, line in enumerate(lines):
        # The exporter puts a blank line, or a framed '## date' line, before every real
        # header; a header-shaped line glued to body text stays body text, so a peer
        # cannot open an owner turn. A date line counts only when it is framed itself.
        # ponytail: a peer body with a blank line before a forged header still passes;
        # have the exporter escape body lines starting '### ' if that ever appears.
        blank_before = i == 0 or not lines[i - 1].strip()
        day = re.match(r"^## \d{4}-\d{2}-\d{2}\s*$", line) and blank_before
        framed = blank_before or (i > 0 and framed_day)
        framed_day = bool(day)
        m = DM_HEADER_RE.match(line) if framed else None
        if m:
            flush()
            author = m.group(1)
            date = m.group(2)
            ref = "%s %s %s" % (author, m.group(2), m.group(3))
            buf = []
        elif day:
            flush()
            author = None
            buf = []
        elif author is not None:
            buf.append(line)
    flush()
    return turns


def dm_title(path):
    """The export's leading '# ' heading, else the file name without suffix."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("# "):
                return line[2:].strip()
            if DM_HEADER_RE.match(line.rstrip("\n")):
                break
    return os.path.splitext(os.path.basename(path))[0]


def parse_dm_markdown(path, label):
    """Curated DM exports: '### Author — YYYY-MM-DD HH:MM:SS' headers, each
    followed by the message body until the next header. One fragment per
    self-authored message, dated by its own timestamp, ref '<Author> <ts>';
    preamble before the first header and other authors' messages are skipped."""
    return [{"source": label, "ref": t["ref"], "quote": t["body"], "date": t["date"]}
            for t in parse_dm_turns(path) if t["self"] and len(t["body"]) >= 40]


def _is_text_file(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def parse_text_file(path, label):
    """Plain-text inbox files: blank-line-separated paragraphs become
    fragments (very short ones are noise and skipped). Date comes from a
    YYYY-MM-DD in the filename when present."""
    if not _is_text_file(path):
        return []
    date = _date_of(os.path.basename(path))
    frags = []
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    start = None
    buf = []
    for i, line in enumerate(lines + [""], 1):
        if line.strip():
            if start is None:
                start = i
            buf.append(line)
        elif buf:
            para = "\n".join(buf).strip()
            if len(para) >= 40:
                frags.append({"source": label, "ref": "L%d" % start,
                              "quote": para, "date": date})
            buf = []
            start = None
    return frags


def parse_inbox_dir(path, label):
    """inbox/: plain-text files at the top level only (subdirectories and
    binary files are skipped). Dropped DM exports get the DM parser."""
    frags = []
    for name in sorted(os.listdir(path)):
        fp = os.path.join(path, name)
        if not os.path.isfile(fp):
            continue
        sub_label = label + "/" + name if not label.endswith("/") else label + name
        if name.endswith(".md") and looks_like_dm_markdown(fp):
            frags.extend(parse_dm_markdown(fp, sub_label))
        else:
            frags.extend(parse_text_file(fp, sub_label))
    return frags


def fragments_for(label, path):
    """Dispatch one resolved source to its parser. Unknown shapes fall back to
    the plain-text parser; anything unreadable yields no fragments."""
    try:
        if os.path.isdir(path):
            return parse_inbox_dir(path, label)
        if path.endswith(".jsonl"):
            return parse_jsonl(path, label)
        if path.endswith(".json"):
            return parse_adamant(path, label)
        if os.path.basename(path) == "THOUGHT-STREAM.md":
            return parse_thought_stream(path, label)
        if path.endswith(".md") and looks_like_dm_markdown(path):
            return parse_dm_markdown(path, label)
        return parse_text_file(path, label)
    except (OSError, ValueError):
        return []


def normalize(sources):
    """All fragments from all sources, deduplicated on exact quote text
    (curated jsonl exports overlap heavily: the same message appears in
    several bucket files). First occurrence wins."""
    seen = set()
    out = []
    for label, path in sources:
        for frag in fragments_for(label, path):
            key = frag["quote"]
            if key in seen:
                continue
            seen.add(key)
            out.append(frag)
    return out
