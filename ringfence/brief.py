"""Kontrak brief: tugas tanpa identitas pemilik dan tanpa isi ditolak.

Ditiru dari harmonist (MIT): baris pertama prompt subagen wajib `AGENT: <slug>`,
dan panjang delegasi minimal. Tanpa penanda itu, pemanggilan tidak dihitung sebagai
kerja — di sini: brief ditolak sebelum pekerja dijalankan.
"""

from __future__ import annotations

import re

__all__ = ["check_brief", "OWNER_RE"]

OWNER_RE = re.compile(r"^\s*OWNER:\s*([A-Za-z0-9_.-]+)\s*$", re.M)


def check_brief(text: str, min_chars: int = 80, require_owner: bool = True) -> tuple[bool, list[str]]:
    """Kembalikan (lolos?, daftar masalah)."""
    problems: list[str] = []
    if not text or not text.strip():
        return False, ["brief kosong"]
    first_line = text.strip().splitlines()[0].strip()
    if require_owner and not OWNER_RE.match(first_line):
        problems.append("baris pertama wajib `OWNER: <nama>`")
    body = OWNER_RE.sub("", text).strip()
    if len(body) < min_chars:
        problems.append(f"isi brief terlalu pendek ({len(body)} < {min_chars} karakter)")
    for marker in ("SELESAI", "DILARANG"):
        if marker not in text.upper():
            problems.append(f"brief wajib menyebut bagian {marker}")
    return (not problems), problems
