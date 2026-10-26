# Incident log (provenance evidence)

On 26 October 2026, one office with a kanban task board, several AI workers
per profile. All numbers below come from the board's logs and database, not estimates.

## 1. A 1-line fix, 250 steps

The fix for the monthly subscription money path = one line of code (`summary.ModelQuota = tieredQuota`)
in `service/text_quota.go`. What happened:

- six full matrix tests across 3 databases in a single day (11:12, 11:14, 11:19, 12:37, 12:37, 14:02),
  because the reviewer's findings came out one at a time at the end of each round.
- one run by another worker: `Duration 25m43s`, `Messages 551 (548 tool call)`, ending with
  `Iteration budget reached (250/250) — response may be incomplete`.

Lesson: findings must be batched into a single round, and the step limit must sit well below
the point where the result actually gets truncated.

## 2. Completed work run again

Card `t_c47ba9ce` was already complete: the runner log ended with `rc=0`, the commit exists, the report exists.
The work dispatcher still ran it again 1 minute later because the card was still in `running`
status and the "already complete" marker was not recognized. The second run had already started re-reading
sources and re-running commands, while the reviewer was assessing the same commit.

Lesson: "log ends with rc=0" must be a hard marker that prevents reassignment,
not something inferred from the board status.

## 3. Two workers, one directory

In the middle of incident (2), an independent reviewer was reading commit `b695c80` in the same directory
used by the second worker. Any result from that reviewer could point to
code that had already changed.

Lesson: one directory = one worker, enforced with a lease, not with memory.

## 4. Waiting with repeated delays

One display check ran 22-28 minutes with a repeated `sleep 45` / `sleep 50` /
`sleep 55` pattern, then started checking `docker images` and `docker inspect postgres`
outside its task scope, while its final report was still 117 bytes.

Lesson: waiting with delays turns one job into dozens of model calls.
What works: one blocking command with a long timeout, read the result once.

## 5. Unintended side effects

We once built a sensor that killed workers as soon as a deviation pattern appeared.
Research showed that is an anti-pattern: false accusations are expensive, and workers stopped mid-way
often lose evidence. Now the sensor only holds and reports; the decision
to stop rests with the supervisor.

## The difference after the guard was installed

The same money check, re-run with the new rules: **3 minutes 17 seconds, 28
tool calls, a complete verdict** — compared to 28 minutes with no verdict on the previous
attempt.