"""Ringfence — guard layer for long-running AI agent workers.

Born from a real incident (26/10): one AI worker spent 548 tool calls on a
one-line code fix, one work card was re-run after it finished, and two workers
worked in the same directory so the results under review changed beneath the
reviewer's feet.

This module depends only on the Python standard library. Three guards:

1. WorkLock   — one work directory = one worker (lease + owner + fencing token).
2. Marker     — a finished job must NOT be re-run (completion marker).
3. DriftWatch — looping patterns in the work log: repeated waiting, or going off scope.

Plus `should_stop()`: a step/time budget so a worker stops and hands off a progress
log, instead of spinning until it runs out of steps.

Status: used in our internal office. Not yet widely tested outside it.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

__all__ = [
    "WorkLock",
    "LockHeld",
    "mark_done",
    "mark_failed",
    "completion",
    "is_worker_running",
    "detect_drift",
    "should_stop",
    "SLEEP_RE",
    "OFF_SCOPE_RE",
]

STATE_DIR = ".ringfence"

# Repeated waiting pattern: `sleep 45`, `sleep 60`, ... in the work log.
SLEEP_RE = re.compile(r"\bsleep\s+\d{2,}")

# Off-scope pattern: the worker touches credentials/infra when that isn't its task.
OFF_SCOPE_RE = re.compile(
    r"rate-limit|rate_limit|\.env\b|/etc/[a-z-]+/|docker inspect|docker images"
    r"|admin/login|PASSWORD",
    re.I,
)

# Words that signal the task IS about auth/credentials — do not flag as drift.
AUTH_TASK_RE = re.compile(r"auth|login|credential|secret|token\s*scope|kredensial", re.I)


class LockHeld(RuntimeError):
    """The work directory is already held by another worker whose lease is still alive."""


class WorkLock:
    """Work-directory lease: a directory may have only one active worker.

    Use before assigning a worker:

        with WorkLock("/srv/work/task-42", owner="bayu", ttl=1800):
            ...

    or manually at the work dispatcher:

        lock = WorkLock(dir, owner="bayu", ttl=1800)
        if not lock.acquire():
            skip("directory still in use")

    An expired lease is treated as free, so a worker that dies suddenly does not
    block the directory forever. `heartbeat()` extends a live worker's lease.
    """

    def __init__(self, workdir: str | os.PathLike, owner: str, ttl: int = 1800):
        self.workdir = Path(workdir)
        self.owner = owner
        self.ttl = int(ttl)
        self.path = self.workdir / STATE_DIR / "lock.json"
        self.token = f"{owner}:{os.getpid()}:{int(time.time())}"

    def read(self) -> dict | None:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return None

    def acquire(self) -> bool:
        """True if the lease was obtained. False if still held by another live worker."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        cur = self.read()
        now = time.time()
        if cur and cur.get("owner") != self.owner and float(cur.get("lease_until", 0)) > now:
            return False
        self.path.write_text(
            json.dumps(
                {"owner": self.owner, "token": self.token, "lease_until": now + self.ttl, "pid": os.getpid()},
                indent=2,
            )
            + "\n"
        )
        return True

    def heartbeat(self) -> bool:
        """Extend the lease. False if the lease was already taken by another worker (fencing)."""
        cur = self.read()
        if cur and cur.get("token") != self.token:
            return False
        self.path.write_text(
            json.dumps(
                {
                    "owner": self.owner,
                    "token": self.token,
                    "lease_until": time.time() + self.ttl,
                    "pid": os.getpid(),
                },
                indent=2,
            )
            + "\n"
        )
        return True

    def release(self) -> None:
        cur = self.read()
        if cur and cur.get("token") == self.token:
            try:
                self.path.unlink()
            except OSError:
                pass

    def __enter__(self) -> "WorkLock":
        if not self.acquire():
            raise LockHeld(f"{self.workdir} is still held by another worker")
        return self

    def __exit__(self, *exc) -> None:
        self.release()


def is_worker_running(workdir: str | os.PathLike, marker: str = "rr-runner.sh") -> bool | None:
    """True if some process's working directory = workdir (Linux /proc).

    None means it could not be checked (not Linux, or /proc is unreadable).
    The caller must treat None as "not considered alive", not "alive".
    """
    target = str(Path(workdir).resolve())
    proc = Path("/proc")
    if not proc.is_dir():
        return None
    found = False
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().decode("utf-8", "replace")
            if marker not in cmdline:
                continue
            if os.readlink(entry / "cwd") == target:
                found = True
                break
        except (OSError, ValueError):
            continue
    return found


def mark_done(workdir: str | os.PathLike, rc: int = 0, note: str = "") -> Path:
    """Write the job completion marker. rc=0 means the work is done."""
    path = Path(workdir) / STATE_DIR / "completion.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rc": int(rc), "note": note, "at": time.time()}, indent=2) + "\n")
    return path


def mark_failed(workdir: str | os.PathLike, note: str = "") -> Path:
    return mark_done(workdir, rc=1, note=note)


def completion(workdir: str | os.PathLike) -> dict | None:
    try:
        return json.loads((Path(workdir) / STATE_DIR / "completion.json").read_text())
    except (OSError, ValueError):
        return None


def detect_drift(
    tail: str,
    task_title: str = "",
    sleeps: int = 4,
    off_scope: int = 2,
) -> tuple[str, str] | None:
    """Read the tail of the work log; return a clear bad pattern, or None.

    ('sleep_poll', ...)  — the worker waits with repeated delays, burning tokens each round.
    ('off_scope', ...)   — the worker touches credentials/infra although that isn't its task.

    IMPORTANT: these findings are for HOLDING and having a human/supervisor inspect, not for
    auto-killing. Killing a worker over a suspected drift is often wrong.
    """
    body = "\n".join(tail.splitlines()[-60:])
    n_sleep = len(SLEEP_RE.findall(body))
    if n_sleep >= sleeps:
        return "sleep_poll", f"repeated waiting {n_sleep}x in the last 60 lines"
    if not AUTH_TASK_RE.search(task_title or ""):
        n_off = len(OFF_SCOPE_RE.findall(body))
        if n_off >= off_scope:
            return "off_scope", f"touched credentials/infra {n_off}x although the task is not auth"
    return None


def should_stop(
    turns: int,
    seconds: float,
    max_turns: int = 80,
    max_seconds: int = 2400,
    handoff_at: float = 0.75,
) -> tuple[bool, str]:
    """Stop decision + reason.

    True = the work must be closed with a progress note (handoff), not continued.
    `handoff_at` leaves room before the hard limit so the worker still has time to write
    the note and send a report.
    """
    if turns >= max_turns:
        return True, f"hard step limit {max_turns} reached"
    if seconds >= max_seconds:
        return True, f"hard time limit {max_seconds}s reached"
    if turns >= max_turns * handoff_at:
        return True, f"entered handoff zone ({turns}/{max_turns} steps): close with PROGRESS.md"
    if seconds >= max_seconds * handoff_at:
        return True, f"entered handoff zone ({int(seconds)}/{max_seconds}s): close with PROGRESS.md"
    return False, ""