"""Ringfence — guard layer for long-running AI agent workers.

Lahir dari insiden nyata (26/10): satu pekerja AI menghabiskan 548 pemanggilan alat
untuk perbaikan 1 baris kode, satu kartu kerja dijalankan ulang setelah selesai, dan
dua pekerja bekerja di direktori yang sama sehingga hasil yang sedang diperiksa
berubah di bawah kaki pemeriksa.

Modul ini hanya bergantung pada pustaka standar Python. Tiga penjaga:

1. WorkLock   — satu direktori kerja = satu pekerja (lease + pemilik + token pagar).
2. Marker     — satu pekerjaan selesai TIDAK boleh dijalankan ulang (penanda hasil).
3. DriftWatch — pola berputar di catatan kerja: menunggu berulang, atau keluar cakupan.

Ditambah `should_stop()`: batas langkah/waktu supaya pekerja berhenti dan menyerahkan
catatan progres, bukan berputar sampai kehabisan langkah.

Status: dipakai di kantor internal kami. Belum diuji luas di luar itu.
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

# Pola menunggu berulang: `sleep 45`, `sleep 60`, ... di catatan kerja.
SLEEP_RE = re.compile(r"\bsleep\s+\d{2,}")

# Pola keluar cakupan: pekerja menyentuh kredensial/infra saat itu bukan tugasnya.
OFF_SCOPE_RE = re.compile(
    r"rate-limit|rate_limit|\.env\b|/etc/[a-z-]+/|docker inspect|docker images"
    r"|admin/login|PASSWORD",
    re.I,
)

# Kata yang menandakan tugas MEMANG soal auth/kredensial — jangan ditandai drift.
AUTH_TASK_RE = re.compile(r"auth|login|credential|secret|token\s*scope|kredensial", re.I)


class LockHeld(RuntimeError):
    """Direktori kerja sudah dipegang pekerja lain yang lease-nya masih hidup."""


class WorkLock:
    """Lease direktori kerja: satu direktori hanya boleh satu pekerja aktif.

    Dipakai sebelum menugaskan pekerja:

        with WorkLock("/srv/work/task-42", owner="bayu", ttl=1800):
            ...

    atau secara manual di pengirim kerja:

        lock = WorkLock(dir, owner="bayu", ttl=1800)
        if not lock.acquire():
            skip("direktori masih dipakai")

    Lease kedaluwarsa dianggap bebas, sehingga pekerja yang mati mendadak tidak
    memblokir direktori selamanya. `heartbeat()` memperpanjang lease pekerja hidup.
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
        """True bila lease didapat. False bila masih dipegang pekerja lain yang hidup."""
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
        """Perpanjang lease. False bila lease sudah diambil pekerja lain (fencing)."""
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
            raise LockHeld(f"{self.workdir} masih dipegang pekerja lain")
        return self

    def __exit__(self, *exc) -> None:
        self.release()


def is_worker_running(workdir: str | os.PathLike, marker: str = "rr-runner.sh") -> bool | None:
    """True bila ada proses yang direktori kerjanya = workdir (Linux /proc).

    None berarti tidak bisa diperiksa (bukan Linux, atau /proc tidak terbaca).
    Pemeriksa harus memperlakukan None sebagai "tidak dianggap hidup", bukan "hidup".
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
    """Tulis penanda hasil pekerjaan. rc=0 berarti kerja selesai."""
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
    """Baca ekor catatan kerja; kembalikan pola buruk yang jelas, atau None.

    ('sleep_poll', ...)  — pekerja menunggu dengan jeda berulang, membakar token per putaran.
    ('off_scope', ...)   — pekerja menyentuh kredensial/infra padahal tugasnya bukan itu.

    PENTING: temuan ini untuk DITAHAN dan diperiksa manusia/pengawas, bukan dibunuh
    otomatis. Mematikan pekerja karena tuduhan melenceng sering salah.
    """
    body = "\n".join(tail.splitlines()[-60:])
    n_sleep = len(SLEEP_RE.findall(body))
    if n_sleep >= sleeps:
        return "sleep_poll", f"menunggu berulang {n_sleep}x di 60 baris terakhir"
    if not AUTH_TASK_RE.search(task_title or ""):
        n_off = len(OFF_SCOPE_RE.findall(body))
        if n_off >= off_scope:
            return "off_scope", f"menyentuh kredensial/infra {n_off}x padahal tugas bukan auth"
    return None


def should_stop(
    turns: int,
    seconds: float,
    max_turns: int = 80,
    max_seconds: int = 2400,
    handoff_at: float = 0.75,
) -> tuple[bool, str]:
    """Keputusan berhenti + alasan.

    Benar = pekerjaan harus ditutup dengan catatan progres (handoff), bukan diteruskan.
    `handoff_at` memberi ruang sebelum batas keras supaya pekerja masih sempat menulis
    catatan dan mengirim laporan.
    """
    if turns >= max_turns:
        return True, f"batas langkah keras {max_turns} tercapai"
    if seconds >= max_seconds:
        return True, f"batas waktu keras {max_seconds}s tercapai"
    if turns >= max_turns * handoff_at:
        return True, f"masuk zona handoff ({turns}/{max_turns} langkah): tutup dengan PROGRESS.md"
    if seconds >= max_seconds * handoff_at:
        return True, f"masuk zona handoff ({int(seconds)}/{max_seconds}s): tutup dengan PROGRESS.md"
    return False, ""