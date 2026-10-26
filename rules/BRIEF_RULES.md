# Mandatory rules in every worker brief (template)

Paste this block into every task. Task-specific content is written above it; these rules
must not be forgotten because a brief quickly sinks in a long session.

```
MANDATORY EFFICIENCY RULES
1. BATCH findings: clear ALL findings in the brief/probe in ONE round + ONE commit.
   Patching one at a time and then opening a new verification round is forbidden.
2. Focused tests during iteration. Run the full test ONCE on the frozen candidate before handoff.
3. Waiting with repeated sleeps (sleep-poll) is forbidden. Run commands
   blocking, read the result once.
4. Do not re-read files/logs already read. Do not explore outside the files
   named in the brief.
5. Do not re-run a command with identical source code + command.
6. RECITATION: every ~5 steps rewrite PROGRESS.md (done / next /
   prohibitions still in force), then read it back.
7. Handoff zone: at 60 steps without progress, STOP and write a brief handoff to
   PROGRESS.md + send a report. Hard limit 80 steps; the next session continues from
   PROGRESS.md, not by starting over.
8. Stop as soon as affected tests + passing evidence are in hand. No additional audit without a written
   reason.
9. Do not remove quality checks for speed. Only repetition gets trimmed.
```

## Why it is written explicitly

Rules placed elsewhere (skill, brief) lose their effect in long sessions. This block is
installed TWICE: in the brief, and in the work dispatcher (`should_stop()` and handoff).
The second one cannot be forgotten.