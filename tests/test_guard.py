"""Ringfence guard self-check. Run: python3 tests/test_guard.py"""
import sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ringfence import WorkLock, LockHeld, completion, detect_drift, mark_done, mark_failed, should_stop


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # 1. Lease: the second worker is rejected while the lease is alive.
        a = WorkLock(d, owner="bayu", ttl=60)
        assert a.acquire() is True
        b = WorkLock(d, owner="deva", ttl=60)
        assert b.acquire() is False, "directory still held by bayu"
        try:
            with b:
                raise AssertionError("LockHeld not raised")
        except LockHeld:
            pass

        # 2. Expired lease -> may be taken (a dead worker does not block forever).
        import json
        p = d / ".ringfence" / "lock.json"
        data = json.loads(p.read_text()); data["lease_until"] = time.time() - 1
        p.write_text(json.dumps(data))
        assert b.acquire() is True, "expired lease must be free"

        # 3. Fencing: the old holder cannot extend after the lease was taken over.
        assert a.heartbeat() is False, "fencing token must reject the old holder"
        assert b.heartbeat() is True

        # 4. Completion marker: finished work is detected, so it is not re-run.
        assert completion(d) is None
        mark_done(d, note="fix 1 baris")
        c = completion(d)
        assert c and c["rc"] == 0 and c["note"] == "fix 1 baris"
        mark_failed(d, note="test merah")
        c = completion(d)
        assert c and c["rc"] == 1

        # 5. Looping-pattern detection.
        sleep_tail = "\n".join(["  sleep 45 + 1 command  45.6s"] * 5)
        assert detect_drift(sleep_tail, "Bayu: fix uang")[0] == "sleep_poll"
        off_tail = "\n".join(["grep -n PASSWORD /etc/routerreceh/new-api.env", "docker inspect rr-postgres"])
        assert detect_drift(off_tail, "Visi: gate tampilan")[0] == "off_scope"
        assert detect_drift(off_tail, "Sentinel: review auth dan kredensial") is None, "auth tasks must not be flagged"
        assert detect_drift("langkah biasa\nok", "apa saja") is None

        # 6. Step/time limits + handoff zone.
        assert should_stop(10, 60) == (False, "")
        assert should_stop(61, 60)[0] is True
        assert should_stop(80, 60)[0] is True
        assert should_stop(10, 2400)[0] is True
    print("ALL PASSED: 6 checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())