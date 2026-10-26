# Patterns from external sources (and what was taken)

All links were verified as reachable when compiled (26 October 2026). Repos were checked via the
GitHub API (stars, last update, archived status).

## Context & long sessions

- Anthropic — **Effective context engineering for AI agents**
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  Taken: aging context degrades quality; the remedy is compaction, structured notes,
  and separating context into sub-agents.
- Anthropic — **Building effective agents**
  https://www.anthropic.com/engineering/building-effective-agents
  Taken: the agent loop must have an explicit stop condition.
- Anthropic — **Multi-agent research system**
  https://www.anthropic.com/engineering/multi-agent-research-system
  Taken: sub-agents isolate context; multi-agent systems use ±15x tokens.
- Manus — **Context engineering**
  https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
  Taken: rewrite the task list (recitation) so the plan is not forgotten; let errors
  surface; do not add context without a reason.
- Cognition — **Don't build multi-agents**
  https://cognition.ai/blog/dont-build-multi-agents
  Taken: separating agents without shared context breaks up implicit decisions.
- arXiv 2505.06120 — **LLMs Get Lost In Multi-Turn Conversation** https://arxiv.org/abs/2505.06120
  Taken: quality drops ±39% in multi-turn conversation vs single turn.
- arXiv 2411.07037 — **LIFBench** https://arxiv.org/abs/2411.07037
  Taken: measurable instruction compliance declines in long contexts.

## Enforcement, limits, and guards

- OpenAI — **A practical guide to building agents** (PDF)
  https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
  Taken: exit condition + step limit + guardrail as three separate things.
- HumanLayer — **12-Factor Agents**
  https://github.com/humanlayer/12-factor-agents
  Taken: the "own your context window" and "control flow" factors; focused agents, not general-purpose ones.
- LangChain — **Context engineering for agents**
  https://blog.langchain.com/context-engineering-for-agents/
  Taken: four ways to handle context: write, select, compress, isolate.
- Resilience4j (circuit breaker) https://github.com/resilience4j/resilience4j
  Taken: breaker state CLOSED → OPEN → HALF_OPEN, not unlimited retries.
- Temporal https://github.com/temporalio/temporal · Restate https://github.com/restatedev/restate ·
  pgmq https://github.com/pgmq/pgmq · BullMQ https://github.com/taskforcesh/bullmq
  Taken: atomic work claim (`FOR UPDATE SKIP LOCKED`), time-bounded lease (`visibility_timeout`,
  `acks_late`), and recovery of dead workers by a reaper.
- Redisson https://github.com/redisson/redisson — a watchdog that auto-renews the lease.
  Taken: the lease must be renewed by a live worker and expire on its own when the worker dies.

## What was not taken

- A full framework (Temporal/Restate/LangGraph) for a need this small — adds
  a service that must be maintained. The pattern was taken, the service was not.
- Automatically killing workers because of a deviation pattern — false accusations are expensive.
- Adding parallel agents as a remedy for slowness — cost rises faster than output.

## Anti-patterns we avoid

`running` status without a lease and without an owner; a lock without a timeout; reassigning an identical
brief without limit; a reviewer whose context is not separated from the producer's; retry
without backoff; declaring a task complete before there is evidence.