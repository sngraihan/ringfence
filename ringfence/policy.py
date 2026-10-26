"""Pure rule evaluator with precedence deny > warn > allow.

Modeled on `a5c-ai/babysitter` `engine.ts` (MIT, pure `evaluate(context)`) and the
ALLOW/DENY/ASK pattern of `omnigent-ai/omnigent` (Apache-2.0). No side effects: rules
in, decision out, and the decision trail is recorded too so it can be audited.
"""

from __future__ import annotations

import re

__all__ = ["Rule", "Decision", "evaluate", "OPS"]

OPS = ("eq", "neq", "gt", "lt", "gte", "lte", "contains", "matches", "in")


class Rule:
    def __init__(self, name: str, effect: str, field: str, op: str, value, reason: str = ""):
        if effect not in ("allow", "warn", "deny"):
            raise ValueError(f"unknown effect: {effect}")
        if op not in OPS:
            raise ValueError(f"unknown op: {op}")
        self.name, self.effect, self.field, self.op, self.value = name, effect, field, op, value
        self.reason = reason

    def matches(self, context: dict) -> bool:
        if self.field not in context:
            return False
        got = context[self.field]
        v = self.value
        try:
            if self.op == "eq":
                return got == v
            if self.op == "neq":
                return got != v
            if self.op == "gt":
                return got > v
            if self.op == "lt":
                return got < v
            if self.op == "gte":
                return got >= v
            if self.op == "lte":
                return got <= v
            if self.op == "contains":
                return v in got
            if self.op == "matches":
                return bool(re.search(str(v), str(got)))
            if self.op == "in":
                return got in v
        except TypeError:
            return False
        return False


class Decision:
    def __init__(self, allowed: bool, effect: str, rule: Rule | None, reason: str, trail: list[dict]):
        self.allowed = allowed
        self.effect = effect
        self.rule = rule.name if rule else None
        self.reason = reason
        self.trail = trail

    def __repr__(self) -> str:
        return f"Decision(allowed={self.allowed}, effect={self.effect}, rule={self.rule})"


def evaluate(context: dict, rules: list[Rule]) -> Decision:
    """Matching rules are collected; the strongest wins.

    Precedence: deny > warn > allow, and if nothing matches -> allowed
    (default-allow) as in the source pattern. Fail-closed is installed by the caller
    for risky actions (see `docs/patterns.md`).
    """
    trail = []
    hits: list[Rule] = []
    for rule in rules:
        ok = rule.matches(context)
        trail.append({"rule": rule.name, "effect": rule.effect, "matched": ok})
        if ok:
            hits.append(rule)
    for effect, allowed in (("deny", False), ("warn", True), ("allow", True)):
        for rule in hits:
            if rule.effect == effect:
                return Decision(allowed, effect, rule, rule.reason or f"rule {rule.name} applies", trail)
    return Decision(True, "default", None, "no matching rule (default-allow)", trail)