"""Deteksi putaran berulang + pagar biaya dari catatan kerja lokal.

Angka ambang ditiru dari `VicKayro/leash` (MIT): hash `tool_name + input`, tandai
bila 10x total atau 6x dalam jendela 10 menit. Pagar biaya harian/per-jam juga dari
pola `leash` ("the loop killer") dan gate biaya `omnigent` (Apache-2.0).

Semua fungsi murni/berkas-lokal: tanpa basis data, tanpa layanan.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

__all__ = ["hash_action", "LoopWatch", "CostGuard"]

LOOP_THRESHOLD = 10
LOOP_FAST_THRESHOLD = 6
LOOP_FAST_WINDOW_S = 10 * 60


def hash_action(tool: str, payload) -> str:
    """Kunci identitas satu aksi: nama alat + isi permintaannya."""
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{tool}|{body}".encode()).hexdigest()[:16]


class LoopWatch:
    """Hitung aksi identik dari event (tool, payload, waktu).

    `observe()` mengembalikan (putaran?, keterangan). Ambang default: 10x total,
    atau 6x dalam 10 menit terakhir.
    """

    def __init__(self, threshold_total: int = LOOP_THRESHOLD,
                 fast_threshold: int = LOOP_FAST_THRESHOLD,
                 fast_window_s: int = LOOP_FAST_WINDOW_S):
        self.threshold_total = threshold_total
        self.fast_threshold = fast_threshold
        self.fast_window_s = fast_window_s
        self.counts: dict[str, int] = {}
        self.times: dict[str, list[float]] = {}

    def observe(self, tool: str, payload, at: float | None = None) -> tuple[bool, str]:
        key = hash_action(tool, payload)
        now = time.time() if at is None else at
        self.counts[key] = self.counts.get(key, 0) + 1
        self.times.setdefault(key, []).append(now)
        if self.counts[key] >= self.threshold_total:
            return True, f"aksi identik {self.counts[key]}x (ambang {self.threshold_total})"
        recent = [t for t in self.times[key] if now - t <= self.fast_window_s]
        if len(recent) >= self.fast_threshold:
            return True, (
                f"aksi identik {len(recent)}x dalam {self.fast_window_s // 60} menit "
                f"(ambang {self.fast_threshold})"
            )
        return False, ""


class CostGuard:
    """Pagar belanja harian/per-jam. Fail-open: galat pencatatan tidak memblokir.

    `fail_open=True` disengaja (pola `leash`): pagar ini penjaga biaya, bukan
    pengaman keamanan. Untuk aksi berisiko, pakai `policy.evaluate` yang fail-closed.
    """

    def __init__(self, state_path: str | Path, daily_cap: float, hourly_cap: float | None = None):
        self.path = Path(state_path)
        self.daily_cap = float(daily_cap)
        self.hourly_cap = float(hourly_cap) if hourly_cap else None

    def _load(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text()).get("entries", [])
        except (OSError, ValueError):
            return []

    def _save(self, entries: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"entries": entries[-2000:]}) + "\n")

    def add(self, cost: float, at: float | None = None) -> tuple[bool, str]:
        """Catat belanja; kembalikan (diblokir?, alasan). Fail-open saat galat."""
        now = time.time() if at is None else at
        try:
            entries = self._load()
            entries.append({"at": now, "cost": float(cost)})
            self._save(entries)
            day = sum(e["cost"] for e in entries if now - e["at"] <= 86400)
            if day > self.daily_cap:
                return True, f"belanja 24 jam {day:.4f} melewati plafon {self.daily_cap:.4f}"
            if self.hourly_cap:
                hour = sum(e["cost"] for e in entries if now - e["at"] <= 3600)
                if hour > self.hourly_cap:
                    return True, f"belanja 1 jam {hour:.4f} melewati plafon {self.hourly_cap:.4f}"
            return False, ""
        except OSError:
            return False, ""  # fail-open: jangan hentikan kerja karena gagal catat
