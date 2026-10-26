"""Append-only journal + idempotency marker.

Modeled on the `a5c-ai/babysitter` pattern (MIT): one event = one JSON file,
written atomically via `os.replace`, and state is rebuilt by re-reading the
journal (`replay`). Done = the presence of a terminal event, not a flag that can
be deleted again.

Idempotency marker (idem from `completionProof`): a hash of `lease_id + task_key`,
so the same job is not run twice without needing a database.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

__all__ = ["Journal", "done_token", "already_done", "mark_done_token", "TERMINAL"]

TERMINAL = {"done", "failed", "abandoned"}


class Journal:
    """Event journal per work directory: `.ringfence/journal/000001.<ts>.json`."""

    def __init__(self, workdir: str | os.PathLike):
        self.dir = Path(workdir) / ".ringfence" / "journal"

    def append(self, kind: str, **fields) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        seq = len(list(self.dir.glob("*.json"))) + 1
        payload = {"seq": seq, "kind": kind, "at": time.time(), **fields}
        final = self.dir / f"{seq:06d}.{int(payload['at'] * 1000)}.json"
        tmp = final.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(tmp, final)  # atomic: readers never see a half-written file
        return final

    def replay(self) -> list[dict]:
        out = []
        for path in sorted(self.dir.glob("[0-9]*.json")):
            try:
                out.append(json.loads(path.read_text()))
            except (OSError, ValueError):
                continue
        return out

    def state(self) -> str:
        """Status from the last terminal event; 'running' if none yet."""
        for ev in reversed(self.replay()):
            if ev.get("kind") in TERMINAL:
                return ev["kind"]
        return "running" if self.replay() else "empty"

    def terminal(self) -> dict | None:
        for ev in reversed(self.replay()):
            if ev.get("kind") in TERMINAL:
                return ev
        return None


def done_token(task_key: str, lease_id: str = "", salt: str = "") -> str:
    """Job identity hash: an idempotency key without a database."""
    raw = f"{task_key}|{lease_id}|{salt}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def mark_done_token(workdir: str | os.PathLike, token: str, note: str = "") -> Path:
    path = Path(workdir) / ".ringfence" / "done.token"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"token": token, "note": note, "at": time.time()}) + "\n")
    return path


def already_done(workdir: str | os.PathLike, token: str) -> bool:
    """True only if the marker exists AND its hash matches this job."""
    try:
        data = json.loads((Path(workdir) / ".ringfence" / "done.token").read_text())
    except (OSError, ValueError):
        return False
    return data.get("token") == token