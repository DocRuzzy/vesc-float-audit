"""Compare two bundles: key quantities, rule outcomes and config differences."""
from __future__ import annotations

import datetime as _dt

from . import catalog as cat
from . import engine
from .bundle import Bundle
from .derived import Namespace
from .report import CROSSCHECK_ROWS, OUTCOME_LABEL, _md_escape, fmt


def _cfg_diff(a: Bundle, b: Bundle, kind: str):
    c = cat.load(kind)
    ca = {"mcconf": a.mc, "appconf": a.app, "refloat": a.rf}[kind].values
    cb = {"mcconf": b.mc, "appconf": b.app, "refloat": b.rf}[kind].values
    rows = []
    for name in sorted(set(ca) | set(cb)):
        va, vb = ca.get(name), cb.get(name)
        if va == vb:
            continue
        if isinstance(va, float) and isinstance(vb, float) and abs(va - vb) <= 1e-6 * max(1.0, abs(va)):
            continue
        rows.append((name, c.describe_value(name, va), c.describe_value(name, vb)))
    return rows


def render(a: Bundle, na: Namespace, ra: list, b: Bundle, nb: Namespace, rb: list,
           today: str | None = None) -> str:
    today = today or _dt.date.today().isoformat()
    la, lb = a.label, b.label
    out = [f"# Configuration comparison — {la} vs {lb}", "", f"Generated {today} by vesc-float-audit.", ""]
    if a.hw.id != b.hw.id:
        out += [f"> The bundles are for different hardware ({a.hw.name} vs {b.hw.name}). Limits and "
                "defaults differ; a difference below is not by itself a problem on either board.", ""]
    out += ["| | " + la + " | " + lb + " |", "|---|---|---|",
            f"| Hardware | {a.hw.name} | {b.hw.name} |",
            f"| Firmware | {a.meta['firmware']} | {b.meta['firmware']} |",
            f"| Refloat | {a.meta['package_version']} | {b.meta['package_version']} |",
            f"| Pack | {a.meta['pack']['s']}S{a.meta['pack']['p']}P | {b.meta['pack']['s']}S{b.meta['pack']['p']}P |",
            f"| Motor | {a.motor.name} | {b.motor.name} |", ""]

    def count(rs, sev):
        return sum(1 for r in rs if r.fired and r.rule.severity == sev)

    out += ["## Findings", "", f"| | {la} | {lb} |", "|---|---|---|"]
    for sev in ("critical", "warning", "info"):
        out.append(f"| {sev} fired | {count(ra, sev)} | {count(rb, sev)} |")
    out.append(f"| not evaluated | {sum(r.outcome == 'not_evaluated' for r in ra)} | "
               f"{sum(r.outcome == 'not_evaluated' for r in rb)} |")
    out += ["", "Rules that fired on either board:", "",
            f"| Rule | Severity | {la} | {lb} |", "|---|---|---|---|"]
    ob = {r.rule.id: r for r in rb}
    for r in ra:
        o = ob[r.rule.id]
        if r.fired or o.fired:
            out.append(f"| {r.rule.id} {_md_escape(r.rule.title)} | {r.rule.severity} | "
                       f"{OUTCOME_LABEL[r.outcome]} | {OUTCOME_LABEL[o.outcome]} |")
    out.append("")

    out += ["## Key quantities", ""]
    for key, title in engine.CROSSCHECKS.items():
        out += [f"### {title}", "", f"| Quantity | {la} | {lb} |", "|---|---|---|"]
        for lbl, k, unit in CROSSCHECK_ROWS[key]:
            u = f" {unit}" if unit else ""
            va, vb = na.values.get(k), nb.values.get(k)
            out.append(f"| {lbl} | {fmt(va)}{u if va is not None else ''} | {fmt(vb)}{u if vb is not None else ''} |")
        out.append("")

    out += ["## Config differences", ""]
    for kind, title in (("mcconf", "Motor config"), ("appconf", "App config"), ("refloat", "Refloat config")):
        rows = _cfg_diff(a, b, kind)
        out += [f"### {title} ({len(rows)} differ)", ""]
        if rows:
            out += [f"| Parameter | {la} | {lb} |", "|---|---|---|"]
            out += [f"| `{n}` | {_md_escape(x)} | {_md_escape(y)} |" for n, x, y in rows]
        else:
            out.append("Identical.")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
