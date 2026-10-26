# Pattern sources & licenses

We studied these repos first, then imitated their **patterns** (rather than copying
foreign code into here). If code is copied in the future, the original owner's
notice must be carried along.

| Repo | License | What was taken |
|---|---|---|
| [a5c-ai/babysitter](https://github.com/a5c-ai/babysitter) | MIT | Append-only event journal (one event = one file, atomic write) + status rebuilt by re-reading the journal; hashed idempotency markers (`sha256`) instead of flags; deny > warn > allow rule precedence as a pure function `evaluate()` + decision trace. |
| [GammaLabTechnologies/harmonist](https://github.com/GammaLabTechnologies/harmonist) | MIT | Brief contract: first line must be `AGENT:`/`OWNER:` and meet a minimum length, otherwise rejected; `stop` with `loop_limit`; open calls older than a threshold (default 900 seconds) are treated as finished so dead workers do not hang. |
| [VicKayro/leash](https://github.com/VicKayro/leash) | MIT | Loop detection from `tool + input` hashes: threshold of 10x total or 6x within 10 minutes; dedup of cost records; daily/hourly spending fence that is fail-open. |
| [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) | Apache-2.0 | Layered ALLOW/DENY/ASK decision at the request and tool-call phase; limit on the number of tool calls per session as a proxy for "too many steps". |
| [resilience4j](https://github.com/resilience4j/resilience4j) | Apache-2.0 | Circuit breaker state CLOSED → OPEN → HALF_OPEN, not unlimited retries. |

Written sources (not code) are in [`patterns.md`](patterns.md).

Responsibility note: the repos above are far larger and more complete than Ringfence.
If your needs are large (multi-agent orchestration, dashboard, durable workflow),
use the repos above — not this.