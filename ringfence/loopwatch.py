"""Repeated-loop detection + cost fence from the local work log.

Threshold numbers modeled on `VicKayro/leash` (MIT): hash `tool_name + input`, flag
at 10x total or 6x within a 10-minute window. The daily/hourly cost fence also comes
from the `leash` pattern ("the loop killer") and the `omnigent` cost gate (Apache-2.0).

All functions are pure/local-file: no database, no service.
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
    """Identity key of a single action: tool name + its request body."""
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{tool}|{body}".encode()).hexdigest()[:16]


class LoopWatch:
    """Count identical actions from events (tool, payload, time).

    `observe()` returns (loop?, description). Default thresholds: 10x total,
    or 6x in the last 10 minutes.
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
            return True, f"identical action {self.counts[key]}x (threshold {self.threshold_total})"
        recent = [t for t in self.times[key] if now - t <= self.fast_window_s]
        if len(recent) >= self.fast_threshold:
            return True, (
                f"identical action {len(recent)}x within {self.fast_window_s // 60} minutes "
                f"(threshold {self.fast_threshold})"
            )
        return False, ""


class CostGuard:
    """Daily/hourly spend fence. Fail-open: a logging error does not block.

    `fail_open=True` is deliberate (the `leash` pattern): this fence is a cost guard, not
    a security control. For risky actions, use `policy.evaluate`, which is fail-closed.
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
        """Record spend; return (blocked?, reason). Fail-open on error."""
        now = time.time() if at is None else at
        try:
            entries = self._load()
            entries.append({"at": now, "cost": float(cost)})
            self._save(entries)
            day = sum(e["cost"] for e in entries if now - e["at"] <= 86400)
            if day > self.daily_cap:
                return True, f"24-hour spend {day:.4f} exceeds cap {self.daily_cap:.4f}"
            if self.hourly_cap:
                hour = sum(e["cost"] for e in entries if now - e["at"] <= 3600)
                if hour > self.hourly_cap:
                    return True, f"1-hour spend {hour:.4f} exceeds cap {self.hourly_cap:.4f}"
            return False, ""
        except OSError:
            return False, ""  # fail-open: do not stop work because a record write failed