"""Merged prose-and-region token stream and the delete-only subsequence check (KTD2, KTD4, KTD5)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .scanner import Region, ScanResult, scan

#: Curly quotes and the dash family fold to ASCII before tokenizing, so a
#: rewrite that only re-punctuates is accepted. This is the intended slack in R2.
FOLD_MAP = {
    0x2018: "'",
    0x2019: "'",
    0x201A: "'",
    0x201B: "'",
    0x2032: "'",
    0x201C: '"',
    0x201D: '"',
    0x201E: '"',
    0x201F: '"',
    0x2010: "-",
    0x2011: "-",
    0x2012: "-",
    0x2013: "-",
    0x2014: "-",
    0x2015: "-",
    0x2212: "-",
}

#: An explicit character class, not a whitespace split. Stopwords and short
#: tokens are kept: delete-only needs every token.
TOKEN_RE = re.compile(r"\w+(?:['-]\w+)*")


@dataclass(frozen=True)
class CheckResult:
    """Outcome of the delete-only check, with the first offending token or region index."""

    ok: bool
    reason: str | None
    detail: str | None


@dataclass(frozen=True)
class MergedStream:
    """One merged document stream: region tokens, and the prose segments between them."""

    regions: tuple[tuple[str, str], ...]
    segments: tuple[tuple[str, ...], ...]

    @property
    def tokens(self) -> tuple[str, ...]:
        """Every prose token in document order."""
        return tuple(token for segment in self.segments for token in segment)


def normalize(text: str) -> str:
    """Apply NFKC and fold curly quotes and dashes to ASCII."""
    return unicodedata.normalize("NFKC", text).translate(FOLD_MAP)


def tokenize(text: str) -> tuple[str, ...]:
    """Split normalized text into casefolded tokens with edge apostrophes stripped."""
    found = []
    for match in TOKEN_RE.finditer(normalize(text)):
        token = match.group(0).strip("'")
        if token:
            found.append(token.casefold())
    return tuple(found)


def merge(result: ScanResult) -> MergedStream:
    """Build the merged stream: one opaque token per frozen region, prose tokens between."""
    block_starts: dict[int, Region] = {}
    markers: dict[int, Region] = {}
    for region in result.regions:
        if region.kind == "list_marker":
            markers[region.start_line] = region
        else:
            block_starts[region.start_line] = region

    prose_set = set(result.prose_lines)
    regions: list[tuple[str, str]] = []
    segments: list[list[str]] = [[]]
    index = 0
    total = len(result.lines)

    while index < total:
        block = block_starts.get(index)
        if block is not None:
            regions.append((block.kind, block.text))
            segments.append([])
            index = block.end_line + 1
            continue
        if index in prose_set:
            line = result.lines[index]
            marker = markers.get(index)
            if marker is not None:
                regions.append((marker.kind, marker.text))
                segments.append([])
                # The marker prefix is frozen; only the item's text is prose.
                line = line[len(marker.text) :]
            segments[-1].extend(tokenize(line))
        index += 1

    return MergedStream(tuple(regions), tuple(tuple(segment) for segment in segments))


def prose_tokens(result: ScanResult) -> tuple[str, ...]:
    """Every prose token of an already-scanned document, frozen regions excluded (KTD5)."""
    return merge(result).tokens


def prose_word_count(text: str) -> int:
    """Count prose words, excluding frozen regions from the denominator (KTD5)."""
    return len(prose_tokens(scan(text)))


def check_delete_only(original: str, candidate: str) -> CheckResult:
    """Decide whether ``candidate`` is reachable from ``original`` by prose deletion alone.

    Two rules over one merged stream (KTD2). First, the frozen-region sequences
    must be *equal*, not merely a subsequence (KTD4): deleting or altering a
    block is a violation. Second, each prose segment between two regions must be
    a subsequence of the original's segment at the same position, which is R2's
    "in the same order relative to the surrounding frozen structures". A token
    that moved across a frozen boundary is reported as ``region_mismatch``
    naming that boundary; a token that moved within its own segment, or that
    never appears in the original, is an ``inserted_token`` -- under delete-only
    semantics a token that was skipped and then reappears has been inserted.

    Raises ``UnsupportedConstruct`` when either side refuses to scan; the caller
    routes that to the ``UNSUPPORTED`` verdict.
    """
    left = merge(scan(original))
    right = merge(scan(candidate))

    for index in range(max(len(left.regions), len(right.regions))):
        if index >= len(left.regions) or index >= len(right.regions):
            return CheckResult(False, "region_mismatch", str(index))
        if left.regions[index] != right.regions[index]:
            return CheckResult(False, "region_mismatch", str(index))

    for position, (source, target) in enumerate(zip(left.segments, right.segments)):
        cursor = 0
        for token in target:
            while cursor < len(source) and source[cursor] != token:
                cursor += 1
            if cursor == len(source):
                return _classify(left.segments, token, position)
            cursor += 1

    return CheckResult(True, None, None)


def _classify(segments: tuple[tuple[str, ...], ...], token: str, position: int) -> CheckResult:
    """Name the failure: a boundary crossing is structural, anything else is an insertion."""
    if token in segments[position]:
        return CheckResult(False, "inserted_token", token)
    origins = [index for index, segment in enumerate(segments) if token in segment]
    if not origins:
        return CheckResult(False, "inserted_token", token)
    origin = min(origins, key=lambda index: (abs(index - position), index))
    boundary = position - 1 if origin < position else position
    return CheckResult(False, "region_mismatch", str(boundary))
