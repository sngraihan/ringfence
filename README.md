# Ringfence

A small guard layer for long-running AI workers: so they don't redo finished work,
don't put two workers in the same directory, don't spin until they run out of steps,
and don't drift off their task.

Depends only on the Python 3.11+ standard library. No server, no queue, no database.
It attaches to the work dispatcher you already have (in our case: a kanban task board).

## Honest status

In use in our internal office since October 26, 2026. **Not yet widely tested outside
that.** The contents of this repo come from real incidents, and will change as it gets
used. If you're looking for a complete framework, this isn't it.

## Problems it solves (all of these actually happened)

| Real event | Consequence | Guard |
|---|---|---|
| 250 steps of work for a 1-line code fix | 548 tool calls, ballooning cost, output still truncated | `should_stop()` |
| A card that was already done re-run by the work dispatcher | duplicated work, results under review changing | `completion()` / `mark_done()` |
| Two workers in the same directory | the checker assessing results that had already shifted | `WorkLock` |
| A worker waiting on a job with repeated sleeps (`sleep 45` x dozens) | tokens burned per cycle with no progress | `detect_drift()` |
| A worker checking credentials/infra when its task was measuring a page | 15 minutes lost, no results | `detect_drift()` |

## Contents

```python
from ringfence import WorkLock, completion, mark_done, detect_drift, should_stop

# 1. one directory = one worker
lock = WorkLock("/srv/work/task-42", owner="builder", ttl=1800)
if not lock.acquire():
    raise SystemExit("directory still in use by another worker")

# 2. finished work is not re-run
if (c := completion("/srv/work/task-42")) and c["rc"] == 0:
    raise SystemExit("already done, wait for the checker")

# 3. step/time limits + handoff zone before the hard limit
stop, why = should_stop(turns=61, seconds=300, max_turns=80, max_seconds=2400)
if stop:
    write_progress_note(why)   # close with a note, continue in a new session

# 4. bad patterns in the work log -> hold for review, not auto-kill
drift = detect_drift(open("worker.log").read(), task_title="page display gate")
```

## Rules that go with the guards

Technical guards alone aren't enough if the working rules aren't written down. The rules
template we paste into every worker brief: [`rules/BRIEF_RULES.md`](rules/BRIEF_RULES.md).

The three with the most impact:
1. **Cancel repetition** — all findings are resolved in one round, one commit.
2. **Recitation** — the worker rewrites the progress note every ~5 steps and then reads it.
   Rules in the brief are quickly forgotten in long sessions; rewriting is stronger than remembering.
3. **Handoff, not continuation** — at 60 steps without progress, stop and hand over the
   note; the next session continues from that note, not by starting over.

## What is NOT recommended (and why)

- **Auto-killing a worker because it's suspected of drifting.** A false accusation is expensive.
  `detect_drift()` reports; the decision to stop rests with the supervisor.
- **Raising the step limit so the work can "finish".** An overlong session actually
  lowers compliance; better to split it with a note handoff.
- **Adding many parallel agents.** Adding agent count adds cost far faster
  than it adds output.

## Does something like this already exist?

Yes, there are adjacent ones — we checked first before writing this:

- [a5c-ai/babysitter](https://github.com/a5c-ai/babysitter) — enforces rule compliance across
  a set of agents.
- [GammaLabTechnologies/harmonist](https://github.com/GammaLabTechnologies/harmonist) —
  agent orchestration with mechanical protocol enforcement.
- [VicKayro/leash](https://github.com/VicKayro/leash) — sees agent costs, loops, and dead
  crons.
- [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) — an orchestration meta-harness.

Ringfence is smaller and narrower: three guards + brief rules, no framework,
no service. If your needs are large, use the ones above.

## What is copied from other repos (v0.2)

We looked at repos that solved similar problems earlier, then copied the patterns
(full list + licenses: [`docs/credits.md`](docs/credits.md)):

| Mechanism | From where | Present here |
|---|---|---|
| Append-only journal: done = terminal event, not a flag | babysitter (MIT) | `journal.Journal` |
| Hashed idempotency marker (no database) | babysitter | `journal.done_token` / `already_done` |
| deny > warn > allow rule + decision trail | babysitter, omnigent | `policy.evaluate` |
| Repeated loop: hash `tool + input`, 10x total / 6x within 10 minutes | leash (MIT) | `loopwatch.LoopWatch` |
| Daily & hourly spend fence (fail-open) | leash, omnigent | `loopwatch.CostGuard` |
| Brief rejected if without owner identity / too short | harmonist (MIT) | `brief.check_brief` |

## Grounding in external sources

Summary of sources (Anthropic, Cognition, Manus, OpenAI, arXiv) and what was taken
from each: [`docs/patterns.md`](docs/patterns.md).
Raw incident notes as evidence: [`docs/incidents.md`](docs/incidents.md).

## Test

```bash
python3 tests/test_guard.py
```

## License

MIT — see [LICENSE](LICENSE).