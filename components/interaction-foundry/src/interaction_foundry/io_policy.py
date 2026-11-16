"""Cooperative storage I/O policy for slow rotational and FUSE-backed disks.

The policy deliberately limits *outstanding work* rather than creating more
threads.  A disk can service many logical tasks, but a single rotational disk
cannot make random concurrent reads non-blocking by adding concurrency.
"""
from __future__ import annotations

import os
import time
from pathlib import Path


class IoBudget:
    """A process-local token bucket for filesystem reads.

    ``rate`` is bytes/second.  ``burst`` bounds one uninterrupted read.  A
    rate of zero disables throttling, which is useful for small local tests.
    """

    def __init__(self, rate: int = 8 * 1024 * 1024, burst: int = 512 * 1024):
        self.rate = max(0, int(rate))
        self.burst = max(4096, int(burst))
        self._tokens = float(self.burst)
        self._last = time.monotonic()

    def consume(self, amount: int) -> None:
        if self.rate <= 0:
            return
        amount = max(0, int(amount))
        while amount:
            now = time.monotonic()
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
            self._last = now
            take = min(amount, max(1, int(self._tokens)))
            if take > self._tokens:
                time.sleep((take - self._tokens) / self.rate)
                continue
            self._tokens -= take
            amount -= take


def source_profile(path: Path) -> str:
    """Return a conservative profile without failing if mount lookup stalls."""
    try:
        mounts = Path("/proc/mounts").read_text(errors="replace").splitlines()
        resolved = path.resolve()
        best = (0, "unknown")
        for line in mounts:
            fields = line.split()
            if len(fields) < 3:
                continue
            target = Path(fields[1].replace("\\040", " "))
            try:
                if str(resolved).startswith(str(target)) and len(str(target)) > best[0]:
                    best = (len(str(target)), fields[2])
            except OSError:
                continue
        return best[1]
    except OSError:
        return "unknown"


def advise_sequential(handle) -> None:
    """Tell the kernel this handle is consumed sequentially when supported."""
    try:
        if hasattr(os, "posix_fadvise"):
            os.posix_fadvise(handle.fileno(), 0, 0, os.POSIX_FADV_SEQUENTIAL)
    except OSError:
        pass


def advise_drop_cache(handle) -> None:
    """Avoid retaining a one-shot archive scan in the page cache."""
    try:
        if hasattr(os, "posix_fadvise"):
            os.posix_fadvise(handle.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    except OSError:
        pass


def launch_command() -> list[str]:
    """Return the recommended wrapper for an archive scan, if installed."""
    return ["ionice", "-c", "3", "nice", "-n", "10"]
