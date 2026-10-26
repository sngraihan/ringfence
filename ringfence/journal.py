"""Jurnal append-only + penanda idempotensi.

Ditiru dari pola `a5c-ai/babysitter` (MIT): satu peristiwa = satu berkas JSON,
ditulis atomic lewat `os.replace`, dan state dibangun ulang dengan membaca ulang
jurnal (`replay`). Selesai = adanya peristiwa terminal, bukan bendera yang bisa
dihapus ulang.

Penanda idempotensi (idem dari `completionProof`): hash dari `lease_id + task_key`,
supaya pekerjaan yang sama tidak dijalankan dua kali tanpa perlu basis data.
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
    """Jurnal peristiwa per direktori kerja: `.ringfence/journal/000001.<ts>.json`."""

    def __init__(self, workdir: str | os.PathLike):
        self.dir = Path(workdir) / ".ringfence" / "journal"

    def append(self, kind: str, **fields) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        seq = len(list(self.dir.glob("*.json"))) + 1
        payload = {"seq": seq, "kind": kind, "at": time.time(), **fields}
        final = self.dir / f"{seq:06d}.{int(payload['at'] * 1000)}.json"
        tmp = final.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(tmp, final)  # atomic: pembaca tidak pernah melihat berkas separuh
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
        """Status dari peristiwa terminal terakhir; 'running' bila belum ada."""
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
    """Hash identitas pekerjaan: kunci idempotensi tanpa basis data."""
    raw = f"{task_key}|{lease_id}|{salt}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def mark_done_token(workdir: str | os.PathLike, token: str, note: str = "") -> Path:
    path = Path(workdir) / ".ringfence" / "done.token"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"token": token, "note": note, "at": time.time()}) + "\n")
    return path


def already_done(workdir: str | os.PathLike, token: str) -> bool:
    """True hanya bila penanda ada DAN hash-nya cocok untuk pekerjaan ini."""
    try:
        data = json.loads((Path(workdir) / ".ringfence" / "done.token").read_text())
    except (OSError, ValueError):
        return False
    return data.get("token") == token
