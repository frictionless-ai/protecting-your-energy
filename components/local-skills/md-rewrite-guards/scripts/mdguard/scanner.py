"""Line-oriented markdown scanner splitting a document into frozen regions and prose (KTD3, KTD9)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- Refusal set (KTD9) -----------------------------------------------------

TILDE_FENCE_RE = re.compile(r"^ {0,3}~{3,}")
BLOCKQUOTE_RE = re.compile(r"^ {0,3}>")
SETEXT_RE = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
INDENTED_CODE_RE = re.compile(r"^(?: {4,}|\t)\S")

# --- Frozen constructs (R6) -------------------------------------------------
#
# Known limitation: these patterns anchor at end-of-line, so a CRLF document
# containing a fence is refused as ``unterminated_fence`` rather than scanned.
# Refusing is the safe direction; mislabeling code as prose is not.

FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,})(?P<info>[^`]*)$")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,})[ \t]*$")
HTML_COMMENT_OPEN_RE = re.compile(r"^ {0,3}<!--")
HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t].*)?$")
LIST_ITEM_RE = re.compile(r"^(?P<marker>[ \t]*(?:[-*+]|\d{1,9}[.)]))(?:[ \t]+|$)")
LINK_REF_RE = re.compile(r"^ {0,3}\[[^\]\n]+\]:[ \t]*\S+")
_BADGE_ATOM = r"(?:\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\))"
BADGE_RE = re.compile(rf"^[ \t]*{_BADGE_ATOM}(?:[ \t]+{_BADGE_ATOM})*[ \t]*$")
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")
DELIMITER_CELL_RE = re.compile(r"^:?-+:?$")

FROZEN_KINDS = (
    "frontmatter",
    "fence",
    "table",
    "html_comment",
    "heading",
    "list_marker",
    "link_ref",
    "badge",
)
#: Regions that own whole lines. ``list_marker`` is the one sub-line kind: its
#: line is also a prose line, because the item's text is prose (KTD9 note).
BLOCK_KINDS = tuple(k for k in FROZEN_KINDS if k != "list_marker")


class UnsupportedConstruct(Exception):
    """A construct the scanner refuses to scan partially (KTD9)."""

    def __init__(self, reason: str, line: int) -> None:
        super().__init__(f"{reason} at line {line}")
        self.reason = reason
        self.line = line


@dataclass(frozen=True)
class Region:
    """One frozen region: its kind, its exact source text, and its line span."""

    kind: str
    text: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ScanResult:
    """Frozen regions in document order, the prose line indices, and the source lines."""

    regions: tuple[Region, ...]
    prose_lines: tuple[int, ...]
    lines: tuple[str, ...]


def split_lines(text: str) -> tuple[str, ...]:
    """Split on newlines only, dropping the empty tail a trailing newline produces."""
    if text == "":
        return ()
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts.pop()
    return tuple(parts)


def split_cells(line: str) -> list[str]:
    """Split a pipe-table row into stripped cells, ignoring leading and trailing pipes."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [cell.strip() for cell in UNESCAPED_PIPE_RE.split(body)]


def is_delimiter_row(line: str, cell_count: int) -> bool:
    """Report whether ``line`` is a table delimiter row with exactly ``cell_count`` cells."""
    if "|" not in line and cell_count != 1:
        return False
    if "-" not in line:
        return False
    cells = split_cells(line)
    if len(cells) != cell_count:
        return False
    return all(DELIMITER_CELL_RE.match(cell) for cell in cells)


def scan(text: str) -> ScanResult:
    """Scan a markdown document, raising ``UnsupportedConstruct`` rather than scanning partially."""
    lines = split_lines(text)
    regions: list[Region] = []
    prose: list[int] = []
    total = len(lines)
    in_list = False
    prev_blank = True
    prev_paragraph = False
    index = 0

    while index < total:
        line = lines[index]

        if not line.strip():
            prose.append(index)
            prev_blank = True
            prev_paragraph = False
            index += 1
            continue

        # A blank line followed by unindented non-list content ends the list.
        if prev_blank and not line[:1].isspace() and not LIST_ITEM_RE.match(line):
            in_list = False

        # Frontmatter is recognized only when line 1 is exactly '---' (KTD3).
        if index == 0 and line == "---":
            end = _find_line(lines, 1, lambda candidate: candidate.rstrip() == "---")
            if end is None:
                raise UnsupportedConstruct("unterminated_frontmatter", 0)
            regions.append(Region("frontmatter", _slice(lines, 0, end), 0, end))
            index, prev_blank, prev_paragraph, in_list = end + 1, False, False, False
            continue

        opener = FENCE_OPEN_RE.match(line)
        if opener:
            run = len(opener.group("fence"))
            end = None
            for probe in range(index + 1, total):
                closer = FENCE_CLOSE_RE.match(lines[probe])
                if closer and len(closer.group("fence")) >= run:
                    end = probe
                    break
            if end is None:
                raise UnsupportedConstruct("unterminated_fence", index)
            regions.append(Region("fence", _slice(lines, index, end), index, end))
            index, prev_blank, prev_paragraph, in_list = end + 1, False, False, False
            continue

        if TILDE_FENCE_RE.match(line):
            raise UnsupportedConstruct("tilde_fence", index)
        if BLOCKQUOTE_RE.match(line):
            raise UnsupportedConstruct("blockquote", index)

        if HTML_COMMENT_OPEN_RE.match(line):
            end = _find_line(lines, index, lambda candidate: "-->" in candidate)
            if end is None:
                raise UnsupportedConstruct("unterminated_html_comment", index)
            regions.append(Region("html_comment", _slice(lines, index, end), index, end))
            index, prev_blank, prev_paragraph, in_list = end + 1, False, False, False
            continue

        if "|" in line:
            cells = split_cells(line)
            if index + 1 < total and is_delimiter_row(lines[index + 1], len(cells)):
                end = index + 1
                probe = index + 2
                while probe < total and lines[probe].strip() and "|" in lines[probe]:
                    end = probe
                    probe += 1
                regions.append(Region("table", _slice(lines, index, end), index, end))
                index, prev_blank, prev_paragraph, in_list = end + 1, False, False, False
                continue

        if HEADING_RE.match(line):
            regions.append(Region("heading", line, index, index))
            index, prev_blank, prev_paragraph, in_list = index + 1, False, False, False
            continue

        if LINK_REF_RE.match(line):
            regions.append(Region("link_ref", line, index, index))
            index, prev_blank, prev_paragraph, in_list = index + 1, False, False, False
            continue

        if BADGE_RE.match(line):
            regions.append(Region("badge", line, index, index))
            index, prev_blank, prev_paragraph, in_list = index + 1, False, False, False
            continue

        item = LIST_ITEM_RE.match(line)
        if item:
            regions.append(Region("list_marker", item.group(0), index, index))
            prose.append(index)
            index, prev_blank, prev_paragraph, in_list = index + 1, False, False, True
            continue

        if prev_paragraph and SETEXT_RE.match(line):
            raise UnsupportedConstruct("setext_heading", index)

        if prev_blank and not in_list and INDENTED_CODE_RE.match(line):
            raise UnsupportedConstruct("indented_code_block", index)

        prose.append(index)
        index, prev_blank, prev_paragraph = index + 1, False, True

    return ScanResult(tuple(regions), tuple(prose), lines)


def scan_bytes(data: bytes) -> ScanResult:
    """Decode UTF-8 then scan; a decode failure is an unsupported construct (KTD9)."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedConstruct("utf8_decode", 0) from exc
    return scan(text)


def _slice(lines: tuple[str, ...], start: int, end: int) -> str:
    return "\n".join(lines[start : end + 1])


def _find_line(lines: tuple[str, ...], start: int, predicate) -> int | None:
    for index in range(start, len(lines)):
        if predicate(lines[index]):
            return index
    return None
