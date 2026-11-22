"""Rule engine. Rules are YAML data under vfa/data/rules/*.yaml.

Rule fields:
  id          unique, e.g. BAT-001
  title       short statement of the problem
  severity    critical | warning | info
  evidence    Source | Dev | Comm | Analysis | UNVERIFIED  (basis of the rule itself)
  category    versions | identity | battery | current | duty | thermal | imu | tune | footpad | log
  crosscheck  optional: cell_vs_battery | cutoffs_vs_tiltback | duty_vs_fw | imu_bus | flux_norm
  when        optional precondition; false -> not applicable
  fail        expression; true -> the rule fires
  message     text with {name} / {name:.1f} placeholders
  rationale   why it matters
  sources     list of URLs / file:line references

Outcomes:
  fired            the condition holds
  passed           the condition does not hold and every input is confirmed
  passed_unverified the condition does not hold, but at least one input is
                   UNVERIFIED (or Comm/Analysis profile data). The report lists
                   these separately and does not call them fine.
  not_evaluated    an input is missing; reported, never treated as a pass
  not_applicable   `when` is false
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources

import yaml

from . import expr
from .derived import Namespace

SEVERITIES = ("critical", "warning", "info")
EVIDENCE = ("Source", "Dev", "Comm", "Analysis", "UNVERIFIED")
CATEGORIES = ("versions", "identity", "battery", "current", "duty", "thermal", "imu",
              "tune", "footpad", "log")
CROSSCHECKS = {
    "cell_vs_battery": "Cell rating vs battery current",
    "cutoffs_vs_tiltback": "Voltage cutoffs vs LV/HV tiltback",
    "duty_vs_fw": "Duty tiltback vs max duty vs field weakening",
    "imu_bus": "IMU type and rate vs bus speed",
    "flux_norm": "Flux linkage vs Refloat torque normalisation",
}
# Input evidence that makes a pass "unconfirmed".
WEAK_INPUT = {"UNVERIFIED", "Comm", "Analysis"}


class RuleError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str
    evidence: str
    category: str
    fail: str
    message: str
    rationale: str
    sources: tuple
    when: str | None = None
    crosscheck: str | None = None

    def inputs(self) -> set[str]:
        out = expr.names(self.fail)
        if self.when:
            out |= expr.names(self.when)
        return out


@dataclass
class Result:
    rule: Rule
    outcome: str
    message: str = ""
    missing: list = field(default_factory=list)
    inputs: dict = field(default_factory=dict)          # name -> value
    weak_inputs: dict = field(default_factory=dict)     # name -> evidence

    @property
    def fired(self) -> bool:
        return self.outcome == "fired"


def _expr_text(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return v if v is None else str(v)


def _validate(r: dict, where: str) -> Rule:
    if not isinstance(r, dict):
        raise RuleError(f"{where}: each rule must be a mapping")
    r = dict(r)
    r["fail"] = _expr_text(r.get("fail"))
    r["when"] = _expr_text(r.get("when"))
    need = ("id", "title", "severity", "evidence", "category", "fail", "message", "rationale", "sources")
    for k in need:
        if k not in r or r[k] in (None, "", []):
            raise RuleError(f"{where}: rule {r.get('id', '?')} lacks '{k}'")
    if r["severity"] not in SEVERITIES:
        raise RuleError(f"{where}: {r['id']}: bad severity {r['severity']!r}")
    if r["evidence"] not in EVIDENCE:
        raise RuleError(f"{where}: {r['id']}: bad evidence {r['evidence']!r}")
    if r["category"] not in CATEGORIES:
        raise RuleError(f"{where}: {r['id']}: bad category {r['category']!r}")
    if r.get("crosscheck") and r["crosscheck"] not in CROSSCHECKS:
        raise RuleError(f"{where}: {r['id']}: bad crosscheck {r['crosscheck']!r}")
    # A rule resting on an unverified claim may warn, never assert a critical fact.
    if r["evidence"] == "UNVERIFIED" and r["severity"] == "critical":
        raise RuleError(f"{where}: {r['id']}: UNVERIFIED rules cannot be critical")
    for e in (r["fail"], r.get("when")):
        if e:
            try:
                expr.parse(e)
            except (SyntaxError, expr.ExprError) as ex:
                raise RuleError(f"{where}: {r['id']}: {ex}") from ex
    srcs = r["sources"] if isinstance(r["sources"], list) else [r["sources"]]
    return Rule(id=r["id"], title=r["title"], severity=r["severity"], evidence=r["evidence"],
                category=r["category"], fail=r["fail"], message=r["message"].strip(),
                rationale=" ".join(str(r["rationale"]).split()), sources=tuple(srcs),
                when=r.get("when"), crosscheck=r.get("crosscheck"))


def load_rules_from(texts: dict[str, str]) -> list[Rule]:
    rules, seen = [], set()
    for where, text in texts.items():
        doc = yaml.safe_load(text) or []
        if not isinstance(doc, list):
            raise RuleError(f"{where}: top level must be a list of rules")
        for r in doc:
            rule = _validate(r, where)
            if rule.id in seen:
                raise RuleError(f"{where}: duplicate rule id {rule.id}")
            seen.add(rule.id)
            rules.append(rule)
    return rules


@lru_cache(maxsize=None)
def load_rules() -> tuple[Rule, ...]:
    d = resources.files("vfa.data.rules")
    texts = {p.name: p.read_text() for p in sorted(d.iterdir(), key=lambda p: p.name)
             if p.name.endswith(".yaml")}
    return tuple(load_rules_from(texts))


def evaluate(rule: Rule, ns: Namespace) -> Result:
    vals = ns.values
    names = sorted(rule.inputs())
    inputs = {n: vals.get(n) for n in names if n in vals}
    weak = {}
    for n in names:
        for base in ns.lineage(n):
            ev = ns.evidence.get(base)
            if ev in WEAK_INPUT:
                weak[base] = ev
    try:
        if rule.when and not expr.evaluate(rule.when, vals):
            return Result(rule, "not_applicable", inputs=inputs)
        fired = bool(expr.evaluate(rule.fail, vals))
    except expr.Missing as m:
        missing = sorted({m.name} | {n for n in names if vals.get(n) is None})
        return Result(rule, "not_evaluated", missing=missing, inputs=inputs, weak_inputs=weak)
    except (TypeError, ZeroDivisionError) as e:
        return Result(rule, "not_evaluated", missing=[f"evaluation error: {e}"], inputs=inputs)
    if fired:
        return Result(rule, "fired", expr.render(rule.message, vals), inputs=inputs, weak_inputs=weak)
    return Result(rule, "passed_unverified" if weak else "passed", inputs=inputs, weak_inputs=weak)


def run(ns: Namespace, rules=None) -> list[Result]:
    rules = load_rules() if rules is None else rules
    order = {s: i for i, s in enumerate(SEVERITIES)}
    results = [evaluate(r, ns) for r in rules]
    results.sort(key=lambda x: (order[x.rule.severity], x.rule.id))
    return results
