#!/usr/bin/env python3
"""Guard CLI: verdicts, path refusals, and the safe write (U4, U7).

Line 1 of stdout is the verdict word (KTD6). Exit status reports whether the
guard ran, not what it decided: every operational outcome exits 0, a usage
error exits 2, and an unhandled failure exits 1 with no status word at all.

Two modes:

* ``--score-only`` (U7) resolves R9's path checks, scores the file, writes the
  receipt carrying the original's hash, and emits ``CLEAN`` or ``PROCEED``. It
  never reads a candidate.
* the default apply mode runs every check in order and applies the candidate
  only when all of them pass, recoverably (R3, R5, R10, R11).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import traceback
from datetime import datetime, timezone

from mdguard.scanner import UnsupportedConstruct, scan_bytes
from mdguard.tells import (
    is_clean,
    read_receipt,
    receipt_path_for,
    score,
    write_receipt,
)
from mdguard.tokens import check_delete_only, prose_word_count

#: Every operational outcome, including a rejection, exits 0 (KTD6).
EXIT_OK = 0
#: An unhandled failure. No status word is printed on this path.
EXIT_CRASH = 1
#: A usage error. Kept out of the verdict space by the parser subclass (KTD6).
EXIT_USAGE = 2

#: Default root for run-scoped backups (KTD10). Never a ``.bak`` sibling.
DEFAULT_BACKUP_ROOT = os.path.join(tempfile.gettempdir(), "md-rewrite-guards")

MARKDOWN_SUFFIXES = (".md", ".markdown")
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")


class UsageError(Exception):
    """The command line was wrong. Never a verdict (KTD6)."""


class PathRefusal(Exception):
    """R9 refused the target. A verdict, not an error."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class BackupFailure(Exception):
    """The backup could not be written or could not be verified (R10). Aborts the run."""


class GuardParser(argparse.ArgumentParser):
    """An ``ArgumentParser`` whose ``error()`` cannot be mistaken for a verdict (KTD6)."""

    def error(self, message: str):  # noqa: D102 - argparse override
        raise UsageError(message)


# --- helpers ----------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    """Hex sha256 of a byte string."""
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: str) -> bytes:
    """Read a file as bytes. Every read and write in this module is binary (R5)."""
    with open(path, "rb") as handle:
        return handle.read()


def sha256_path(path: str) -> str:
    """Hex sha256 of a file's current bytes."""
    return sha256_bytes(read_bytes(path))


def _components(path: str) -> list[str]:
    """Split an absolute path into its components, drive and root removed."""
    parts = []
    head = path
    while True:
        head, tail = os.path.split(head)
        if tail:
            parts.append(tail)
        if not head or head == os.sep:
            break
    parts.reverse()
    return parts


def _is_under(path: str, root: str) -> bool:
    """Report whether ``path`` sits strictly below ``root``."""
    try:
        relative = os.path.relpath(path, root)
    except ValueError:
        return False
    if relative in (os.curdir, os.pardir):
        return False
    return not relative.startswith(os.pardir + os.sep)


def _link_in_chain(root: str, target: str) -> bool:
    """Report whether any component from ``root`` down to ``target`` is a symlink.

    The walk starts at the allowlist root rather than at ``/`` so that a symlink
    somewhere above the configured root -- which the operator chose -- does not
    refuse every file beneath it.
    """
    if os.path.islink(target):
        return True
    relative = os.path.relpath(target, root)
    current = root
    for part in _components(os.path.join(os.sep, relative)):
        current = os.path.join(current, part)
        if os.path.islink(current):
            return True
    return False


def check_target_path(target: str, allow_roots: list[str]) -> str:
    """Resolve ``target`` and apply every R9 refusal, before any candidate is read.

    Returns the absolute target path. Raises ``PathRefusal`` with the reason,
    which the caller routes to the ``UNSUPPORTED`` verdict.
    """
    absolute = os.path.abspath(os.path.expanduser(target))
    if not allow_roots:
        raise PathRefusal("no_allowlist", "configure --allow-root")

    roots = [os.path.abspath(os.path.expanduser(root)) for root in allow_roots]
    real_target = os.path.realpath(absolute)
    matched = None
    for root in roots:
        if _is_under(absolute, root) or _is_under(real_target, os.path.realpath(root)):
            matched = root
            break
    if matched is None:
        raise PathRefusal("not_allowlisted", f"path={absolute}")

    if not os.path.lexists(absolute):
        raise PathRefusal("missing_target", f"path={absolute}")

    if _link_in_chain(matched, absolute):
        raise PathRefusal("symlink", f"path={absolute}")

    stat = os.lstat(absolute)
    if not os.path.isfile(absolute):
        raise PathRefusal("not_a_file", f"path={absolute}")
    if stat.st_nlink > 1:
        raise PathRefusal("hardlink", f"nlink={stat.st_nlink}")

    parts = set(_components(absolute)) | set(_components(real_target))
    if "archive" in parts:
        raise PathRefusal("archive_path", f"path={absolute}")

    directories = set(_components(os.path.dirname(absolute))) | set(
        _components(os.path.dirname(real_target))
    )
    for part in sorted(directories):
        if part.startswith(".") and part not in (os.curdir, os.pardir):
            raise PathRefusal("dot_directory", f"component={part}")

    return absolute


def make_run_dir(root: str) -> str:
    """Create the run-scoped backup directory for this invocation (KTD10, R10).

    Scoped per ``main()`` call, not per process: two sequential runs must not
    share a directory, or run 2 would overwrite run 1's only undo.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    path = os.path.join(root, f"run-{stamp}-{os.getpid()}")
    os.makedirs(path, exist_ok=True)
    return path


def backup_original(run_dir: str, target: str, data: bytes, digest: str) -> str:
    """Copy the original into the run directory and verify the copy by hash (R10).

    Raises ``BackupFailure`` if the copy cannot be written or does not read back
    with the original's hash. That aborts the run rather than producing a
    verdict: an unverifiable backup means the write would be unrecoverable.
    """
    name = SAFE_NAME_RE.sub("_", os.path.basename(target)) or "target"
    marker = hashlib.sha256(target.encode("utf-8")).hexdigest()[:16]
    destination = os.path.join(run_dir, f"{name}.{marker}")
    try:
        os.makedirs(run_dir, exist_ok=True)
        with open(destination, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise BackupFailure(f"backup could not be written: {destination}: {exc}") from exc
    try:
        written = sha256_path(destination)
    except OSError as exc:
        raise BackupFailure(f"backup could not be read back: {destination}: {exc}") from exc
    if written != digest:
        raise BackupFailure(
            f"backup hash {written} does not match original {digest}: {destination}"
        )
    return destination


def replace_bytes(target: str, data: bytes, mode: int) -> None:
    """Write ``data`` over ``target`` atomically, preserving mode (R5).

    ``mkstemp`` creates the temp file 0600; the target is 644, so the mode is
    copied explicitly before the rename.
    """
    directory = os.path.dirname(target) or os.curdir
    handle, temporary = tempfile.mkstemp(dir=directory, prefix=".mdguard-", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def remove_candidate(path: str) -> None:
    """Delete the candidate sidecar. Called on accept and on reject, never in dry run."""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def _ratio(value: float) -> str:
    """Format a ratio for line 1, at the precision the verdict contract shows."""
    return f"{value:.2f}"


# --- the CLI ----------------------------------------------------------------


def build_parser() -> GuardParser:
    """Build the argument parser."""
    parser = GuardParser(
        prog="guard.py",
        description="Decide whether a delete-only markdown rewrite is safe to apply.",
    )
    parser.add_argument("--original", required=True, help="the markdown file to guard")
    parser.add_argument("--candidate", help="the proposed rewrite, written to a sidecar path")
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="score the original and write the receipt; never read a candidate",
    )
    parser.add_argument("--dry-run", action="store_true", help="report a verdict, write nothing")
    parser.add_argument("--json", action="store_true", help="add a JSON object on line 2")
    parser.add_argument(
        "--allow-root",
        action="append",
        default=None,
        metavar="DIR",
        help="a root the target must resolve under; repeatable, and required",
    )
    parser.add_argument(
        "--floor",
        type=float,
        default=None,
        metavar="RATIO",
        help="minimum prose reduction to accept; uncalibrated, so unset by default",
    )
    parser.add_argument(
        "--ceiling",
        type=float,
        default=None,
        metavar="RATIO",
        help="maximum prose reduction to accept; uncalibrated, so unset by default",
    )
    parser.add_argument(
        "--backup-root",
        default=None,
        metavar="DIR",
        help=f"root for run-scoped backups (default {DEFAULT_BACKUP_ROOT})",
    )
    return parser


def backup_root_for(args: argparse.Namespace) -> str:
    """Resolve the backup root at call time, honoring the flag then the environment."""
    if args.backup_root:
        return os.path.abspath(os.path.expanduser(args.backup_root))
    override = os.environ.get("MDGUARD_BACKUP_ROOT")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return DEFAULT_BACKUP_ROOT


def validate(args: argparse.Namespace) -> None:
    """Reject a command line that names the wrong kind of file. A usage error, not a verdict."""
    if not args.original.lower().endswith(MARKDOWN_SUFFIXES):
        raise UsageError(f"--original must be a markdown file, got {args.original}")
    if args.score_only:
        if args.candidate:
            raise UsageError("--score-only never reads a candidate; drop --candidate")
        return
    if not args.candidate:
        raise UsageError("--candidate is required unless --score-only is given")
    if os.path.abspath(args.candidate) == os.path.abspath(args.original):
        raise UsageError("--candidate and --original name the same file")
    for name in ("floor", "ceiling"):
        value = getattr(args, name)
        if value is not None and not 0.0 <= value < 1.0:
            raise UsageError(f"--{name} must be at least 0.0 and below 1.0, got {value}")
    if args.floor is not None and args.ceiling is not None and args.floor > args.ceiling:
        raise UsageError(f"--floor {args.floor} is above --ceiling {args.ceiling}")


class Reporter:
    """Emit the verdict: the status word on line 1, optional JSON on line 2 (KTD6)."""

    def __init__(self, stream, use_json: bool, path: str) -> None:
        self.stream = stream
        self.use_json = use_json
        self.path = path

    def emit(self, word: str, tail: str = "", applied: bool = False, **payload) -> int:
        """Print the verdict and return the exit status, which is always 0."""
        line = f"{word}  {tail}".rstrip() if tail else word
        if word == "ACCEPTED" and not applied:
            line = f"{line} applied=false"
        print(line, file=self.stream)
        if self.use_json:
            body = {
                "verdict": word,
                "path": self.path,
                "applied": applied,
                "check": None,
                "measured": None,
            }
            body.update(payload)
            print(json.dumps(body, sort_keys=True), file=self.stream)
        return EXIT_OK


def run(args: argparse.Namespace, stream) -> int:
    """Run one guard invocation and emit exactly one verdict."""
    validate(args)
    reporter = Reporter(stream, args.json, os.path.abspath(args.original))

    try:
        target = check_target_path(args.original, args.allow_root or [])
    except PathRefusal as refusal:
        return reporter.emit(
            "UNSUPPORTED",
            f"{refusal.reason} {refusal.detail}".strip(),
            check=refusal.reason,
            measured=refusal.detail or None,
        )

    reporter.path = target
    original_bytes = read_bytes(target)
    original_sha = sha256_bytes(original_bytes)

    try:
        scan_bytes(original_bytes)
    except UnsupportedConstruct as refusal:
        return reporter.emit(
            "UNSUPPORTED",
            f"{refusal.reason} line={refusal.line}",
            check=refusal.reason,
            measured=refusal.line,
        )
    original_text = original_bytes.decode("utf-8")

    # Scored here, before anything is written, so that an unreadable marker
    # table crashes on the pre-write side of the run every time.
    tells = score(original_text)
    original_words = tells.prose_words

    if args.score_only:
        receipt = write_receipt(target, original_sha, None, tells)
        if is_clean(tells) or original_words == 0:
            return reporter.emit(
                "CLEAN",
                check="tell_score",
                measured=tells.total,
                score=tells.total,
                prose_words=original_words,
                receipt=receipt,
                original_sha256=original_sha,
            )
        return reporter.emit(
            "PROCEED",
            f"score={tells.total} prose_words={original_words}",
            check="tell_score",
            measured=tells.total,
            score=tells.total,
            prose_words=original_words,
            receipt=receipt,
            original_sha256=original_sha,
        )

    if original_words == 0:
        # No prose to compare and no denominator to divide by (R3).
        return reporter.emit(
            "CLEAN",
            check="empty_prose",
            measured=0,
            score=tells.total,
            prose_words=0,
            original_sha256=original_sha,
        )

    receipt_path = receipt_path_for(target)
    if not os.path.exists(receipt_path):
        return reporter.emit(
            "REJECTED",
            "missing_receipt run=--score-only",
            check="missing_receipt",
            measured=receipt_path,
        )
    try:
        receipt = read_receipt(receipt_path)
    except ValueError as exc:
        return reporter.emit(
            "REJECTED",
            "unusable_receipt",
            check="unusable_receipt",
            measured=str(exc),
        )
    if receipt["path"] != target:
        return reporter.emit(
            "REJECTED",
            f"receipt_mismatch recorded={receipt['path']}",
            check="receipt_mismatch",
            measured=receipt["path"],
        )
    if receipt["original_sha256"] != original_sha:
        return reporter.emit(
            "STALE",
            check="original_sha256",
            measured=original_sha,
            expected_sha256=receipt["original_sha256"],
            original_sha256=original_sha,
        )

    if not os.path.isfile(args.candidate):
        return reporter.emit(
            "REJECTED",
            f"missing_candidate path={os.path.abspath(args.candidate)}",
            check="missing_candidate",
            measured=os.path.abspath(args.candidate),
        )
    candidate_bytes = read_bytes(args.candidate)
    candidate_sha = sha256_bytes(candidate_bytes)

    try:
        scan_bytes(candidate_bytes)
    except UnsupportedConstruct as refusal:
        return reporter.emit(
            "UNSUPPORTED",
            f"{refusal.reason} line={refusal.line} side=candidate",
            check=refusal.reason,
            measured=refusal.line,
        )
    candidate_text = candidate_bytes.decode("utf-8")

    # Nothing below this point may write while a check can still refuse.
    applying = not args.dry_run and args.floor is not None and args.ceiling is not None

    result = check_delete_only(original_text, candidate_text)
    if not result.ok:
        if applying:
            remove_candidate(args.candidate)
        if result.reason == "region_mismatch":
            return reporter.emit(
                "REJECTED",
                f"region_mismatch first_boundary_index={result.detail}",
                check="region_mismatch",
                measured=int(result.detail),
            )
        return reporter.emit(
            "REJECTED",
            f'delete_only inserted_token="{result.detail}"',
            check="delete_only",
            measured=result.detail,
        )

    candidate_words = prose_word_count(candidate_text)
    reduction = (original_words - candidate_words) / original_words
    common = {
        "reduction": reduction,
        "prose_words_original": original_words,
        "prose_words_candidate": candidate_words,
        "floor": args.floor,
        "ceiling": args.ceiling,
        "original_sha256": original_sha,
        "candidate_sha256": candidate_sha,
    }

    if args.floor is not None and reduction < args.floor:
        if applying:
            remove_candidate(args.candidate)
        return reporter.emit(
            "REJECTED",
            f"compression_floor achieved={_ratio(reduction)} required={_ratio(args.floor)}",
            check="compression_floor",
            measured=reduction,
            **common,
        )
    if args.ceiling is not None and reduction > args.ceiling:
        if applying:
            remove_candidate(args.candidate)
        return reporter.emit(
            "REJECTED",
            f"compression_ceiling achieved={_ratio(reduction)} maximum={_ratio(args.ceiling)}",
            check="compression_ceiling",
            measured=reduction,
            **common,
        )

    if not applying:
        # Either --dry-run, or a band that was never calibrated. Both report the
        # verdict and write nothing at all -- not the target, not the backup,
        # not the receipt, and not the candidate sidecar (R3).
        return reporter.emit(
            "ACCEPTED",
            f"reduction={_ratio(reduction)}",
            applied=False,
            check="acceptance_band",
            measured=reduction,
            **common,
        )

    mode = os.stat(target).st_mode & 0o7777
    run_dir = make_run_dir(backup_root_for(args))
    backup = backup_original(run_dir, target, original_bytes, original_sha)

    # R11: re-hash immediately before replacing, so a write that landed while
    # the checks ran is refused rather than silently destroyed.
    if sha256_path(target) != original_sha:
        return reporter.emit(
            "STALE",
            check="original_sha256",
            measured=sha256_path(target),
            expected_sha256=original_sha,
            backup=backup,
        )

    replace_bytes(target, candidate_bytes, mode)
    exit_status = reporter.emit(
        "ACCEPTED",
        f"reduction={_ratio(reduction)}",
        applied=True,
        check="acceptance_band",
        measured=reduction,
        backup=backup,
        **common,
    )
    write_receipt(target, original_sha, candidate_sha, tells)
    remove_candidate(args.candidate)
    return exit_status


def main(argv: list[str] | None = None, stream=None) -> int:
    """Parse, run, and map every failure onto an exit status that is not a verdict."""
    out = sys.stdout if stream is None else stream
    parser = build_parser()
    try:
        args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
        return run(args, out)
    except UsageError as exc:
        print(f"{parser.prog}: usage error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 - the crash path is part of the contract
        traceback.print_exc(file=sys.stderr)
        return EXIT_CRASH


if __name__ == "__main__":
    sys.exit(main())
