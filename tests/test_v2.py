"""Ringfence 0.2 self-check. Run: python3 tests/test_v2.py"""
import sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ringfence import (
    CostGuard, Journal, LoopWatch, Rule, already_done, check_brief, done_token,
    evaluate, hash_action, mark_done_token,
)


def main() -> int:
    # 1. Append-only journal: order, replay, status from terminal event.
    with tempfile.TemporaryDirectory() as td:
        j = Journal(td)
        assert j.state() == "empty"
        j.append("brief", owner="builder", n=1)
        j.append("edit", file="service/text_quota.go")
        assert j.state() == "running"
        j.append("done", rc=0, note="fix 1 baris")
        st = j.state()
        assert st == "done", st
        events = j.replay()
        assert [e["seq"] for e in events] == [1, 2, 3]
        assert j.terminal()["note"] == "fix 1 baris"
        # no leftover .tmp files -> atomic write
        assert not list((Path(td) / ".ringfence" / "journal").glob("*.tmp"))

        # 2. Idempotency marker: matching hash = do not re-run.
        tok = done_token("t_abc", lease_id="l1")
        assert already_done(td, tok) is False
        mark_done_token(td, tok, note="selesai")
        assert already_done(td, tok) is True
        assert already_done(td, done_token("t_abc", lease_id="l2")) is False, "another job must be allowed to run"

    # 3. Repeated loops: 10x total, and 6x within 10 minutes.
    lw = LoopWatch()
    hits = [lw.observe("terminal", {"cmd": "go test ./service"})[0] for _ in range(12)]
    assert hits[-1] is True and hits[0] is False
    lw2 = LoopWatch()
    now = time.time()
    flagged = [lw2.observe("ssh", {"cmd": "tail log"}, at=now + i)[0] for i in range(6)]
    assert flagged[-1] is True
    lw3 = LoopWatch()
    spaced = [lw3.observe("ssh", {"cmd": "tail log"}, at=now + i * 300)[0] for i in range(3)]
    assert any(spaced) is False, "identical actions widely spaced are not a loop"
    assert hash_action("a", {"x": 1}) == hash_action("a", {"x": 1})
    assert hash_action("a", {"x": 1}) != hash_action("a", {"x": 2})

    # 4. Cost fence: daily and hourly.
    with tempfile.TemporaryDirectory() as td:
        cg = CostGuard(Path(td) / "cost.json", daily_cap=1.0, hourly_cap=0.3)
        assert cg.add(0.1)[0] is False
        blocked, why = cg.add(0.25)
        assert blocked is True and "1-hour" in why, why
        cg2 = CostGuard(Path(td) / "cost2.json", daily_cap=0.2)
        cg2.add(0.15)
        blocked, why = cg2.add(0.1)
        assert blocked is True and "24-hour" in why, why

    # 5. Rules: precedence deny > warn > allow, plus decision trail.
    rules = [
        Rule("ubah-harga", "deny", "path", "matches", r"price|harga", "price must not be changed by workers"),
        Rule("perlu-review", "warn", "path", "contains", "auth", "requires human review"),
        Rule("baca-biasa", "allow", "path", "contains", "docs", "read is safe"),
    ]
    d = evaluate({"path": "src/price_table.go"}, rules)
    assert d.allowed is False and d.rule == "ubah-harga" and d.effect == "deny"
    d = evaluate({"path": "src/auth/login.go"}, rules)
    assert d.allowed is True and d.effect == "warn"
    d = evaluate({"path": "docs/index.md"}, rules)
    assert d.effect == "allow"
    d = evaluate({"path": "src/util.go"}, rules)
    assert d.effect == "default" and d.allowed is True
    assert len(d.trail) == 3 and d.trail[0]["matched"] is False

    # 6. Brief contract.
    ok, problems = check_brief("kerjakan ini")
    assert ok is False and any("OWNER" in p for p in problems)
    good = "OWNER: builder\n" + ("Kerjakan perbaikan uang tiered pada service/text_quota.go. " * 4) + \
        "\nDONE: commit + tests pass.\nFORBIDDEN: change pricing."
    ok, problems = check_brief(good)
    assert ok is True, problems
    print("ALL PASSED: 6 checks (v0.2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())