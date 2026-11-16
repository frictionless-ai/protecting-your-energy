"""Local identifier screening, not guaranteed anonymization or review approval."""

from dataclasses import dataclass
import ipaddress
import re
import unicodedata
from collections.abc import Iterable


def normalize_text(text: str) -> str:
    """NFKC plus removal of format controls; offsets refer to this normalized text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return "".join(c for c in unicodedata.normalize("NFKC", text)
                   if unicodedata.category(c) != "Cf")


@dataclass(frozen=True)
class Finding:
    kind: str
    start: int
    end: int


_PATTERNS = {
    # Local-part bounded to 64 chars (RFC 5321 3.4.1) and each domain label
    # to 63 chars with at most 8 labels (RFC 1035 2.3.4) so an unrelated
    # "@" or "." run far later in unstructured text cannot be greedily
    # absorbed into one pathologically long match.
    "email": r"[\w.!#$%&'*+/=?^`{|}~-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}",
    "url": r"\b[a-z][a-z0-9+.-]*://[^\s<>]+|\bwww\.[^\s<>]+|\b(?:[\w-]+\.)+(?:com|org|net|io|dev|edu|gov|co|ai|app|gg)\b(?:/[^\s<>]*)?",
    "path": r"(?<!\w)(?:[a-z]:[\\/]|\\\\|~/|\.{1,2}/|/)[^\s<>\"']+|\b[\w.-]+(?:[/\\][\w.-]+)+",
    "discord": r"<[@#](?:[!&])?\d+>|(?<!\w)\d{17,20}(?!\w)|\b\w+#\d{4}\b",
    "token": r"\b(?:sk[-_](?:proj-)?|hf_|gh[pousr]_|github_pat_|xox[baprs]-)[a-z0-9_-]{8,}|\beyJ[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+|\bmfa\.[a-z0-9_-]{20,}|\b[a-z0-9_-]{23,28}\.[a-z0-9_-]{6}\.[a-z0-9_-]{25,}|\b(?:bearer\s+[^\s,;]+|(?:api[_-]?key|access[_-]?token|token|secret|password)\s*[:=]\s*[\"']?[^\s,;\"']+)",
    "source_hash": r"(?<![a-z0-9])[a-f0-9]{64}(?![a-z0-9])",
    "timestamp": r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?\b",
}
_COMPILED = [(kind, re.compile(pattern, re.IGNORECASE))
             for kind, pattern in _PATTERNS.items()]
_IP = re.compile(r"(?<![\w:])(?:[0-9a-f]*:){2,}[0-9a-f:.]+(?:%[\w.-]+)?(?!\w)|(?<!\w)(?:\d{1,3}\.){3}\d{1,3}(?!\w)", re.I)


def _iter_ip_findings(text: str) -> Iterable[Finding]:
    token_start: int | None = None
    for index, char in enumerate(text + " "):
        if char.isalnum() or char in ".:%_-":
            if token_start is None:
                token_start = index
            continue
        if token_start is None:
            continue
        token = text[token_start:index].rstrip(".")
        if token.count(":") >= 2 or re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", token):
            try:
                ipaddress.ip_address(token)
            except ValueError:
                pass
            else:
                yield Finding("ip", token_start, token_start + len(token))
        token_start = None


class PrivacyRedactor:
    """Normalize, screen and redact text without assigning review status.

    Deny terms are literal, case-insensitive substrings, including Unicode
    casefold expansions. Findings contain offsets and categories, never matches.
    Contextual reidentification and obfuscations still require manual review.
    """

    def __init__(self, deny_terms: Iterable[str] = ()):
        if isinstance(deny_terms, (str, bytes)):
            raise TypeError("deny_terms must be an iterable of strings")
        terms = [normalize_text(term).casefold() for term in deny_terms]
        if any(not term.strip() for term in terms):
            raise ValueError("deny terms must not be empty")
        self.deny_terms = tuple(sorted(set(terms)))

    def screen(self, text: str) -> list[Finding]:
        text = normalize_text(text)
        findings = [Finding(kind, match.start(), match.end())
                    for kind, pattern in _COMPILED for match in pattern.finditer(text)]
        findings.extend(_iter_ip_findings(text))
        folded, positions = [], []
        for index, char in enumerate(text):
            expansion = char.casefold()
            folded.append(expansion)
            positions.extend([index] * len(expansion))
        folded_text = "".join(folded)
        for term in self.deny_terms:
            start = folded_text.find(term)
            while start >= 0:
                before = folded_text[start - 1] if start > 0 else ""
                after_index = start + len(term)
                after = folded_text[after_index] if after_index < len(folded_text) else ""
                bounded = bool(term.strip()) and (
                    any(char.isspace() for char in term)
                    or ((not before or not before.isalnum()) and (not after or not after.isalnum()))
                )
                if bounded:
                    findings.append(Finding("deny_term", positions[start], positions[start + len(term) - 1] + 1))
                start = folded_text.find(term, start + 1)
        return sorted(set(findings), key=lambda item: (item.start, item.end, item.kind))

    def redact(self, text: str) -> str:
        """Return normalized text with overlapping findings replaced once."""
        text = normalize_text(text)
        spans: list[list[int]] = []
        for finding in self.screen(text):
            if spans and finding.start <= spans[-1][1]:
                spans[-1][1] = max(spans[-1][1], finding.end)
            else:
                spans.append([finding.start, finding.end])
        for start, end in reversed(spans):
            text = text[:start] + "[REDACTED]" + text[end:]
        return text


def screen(text: str, deny_terms: Iterable[str] = ()) -> list[Finding]:
    return PrivacyRedactor(deny_terms).screen(text)


def redact(text: str, deny_terms: Iterable[str] = ()) -> str:
    return PrivacyRedactor(deny_terms).redact(text)
