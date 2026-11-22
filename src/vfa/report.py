"""Markdown audit report, one per board."""
from __future__ import annotations

import datetime as _dt
import re

from . import catalog as cat
from . import engine, profiles
from .bundle import Bundle
from .derived import Namespace

DISCLAIMER = (
    "This report is generated from exported configuration files and the rule set in "
    "`src/vfa/data/rules/`. It does not certify any setting as safe. A rule that did not fire "
    "only means that rule's condition did not hold; rules whose inputs are missing or "
    "unconfirmed are listed separately, never as passes. Nothing here has been validated on a board."
)

# Parameters expected to differ from defaults on any detected motor / calibrated board.
_CALIBRATION = re.compile(
    r"^(foc_offsets_|foc_hall_table__|imu_conf\.(accel|gyro)_offsets|imu_conf\.rot_|"
    r"foc_motor_(r|l|ld_lq_diff|flux_linkage)$|foc_observer_gain$|foc_current_k[pi]$|"
    r"foc_encoder_|controller_id$|foc_hall_interp_erpm$)")

OUTCOME_LABEL = {
    "fired": "FIRED", "passed": "no finding", "passed_unverified": "no finding (unconfirmed inputs)",
    "not_evaluated": "NOT EVALUATED", "not_applicable": "n/a",
}


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        if v != 0 and (abs(v) < 0.01 or abs(v) >= 1e6):
            return f"{v:.4g}"
        return f"{v:.4g}" if abs(v) < 100 else f"{v:.1f}"
    if isinstance(v, tuple):
        return ", ".join(map(str, v)) or "none"
    return str(v)


def _md_escape(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _row(ns: Namespace, label: str, key: str, unit: str = "") -> str:
    v = ns.values.get(key)
    ev = ns.evidence.get(key, "")
    if key in ns.deps:
        weak = sorted({ns.evidence.get(k) for k in ns.lineage(key) - {key}} & engine.WEAK_INPUT)
        ev = (ev or "derived") + (f" (rests on {', '.join(weak)})" if weak else "")
    val = fmt(v) + (f" {unit}" if unit and v is not None else "")
    return f"| {label} | {val} | `{key}` | {ev} |"


CROSSCHECK_ROWS = {
    "cell_vs_battery": [
        ("Pack", "pack.s", "S"), ("Parallel groups", "pack.p", "P"),
        ("Cell continuous discharge", "cell.continuous_discharge_a", "A"),
        ("Pack continuous rating", "pack.continuous_a", "A"),
        ("Durable figure", "pack.durable_a", "A"),
        ("Battery Current Max", "mc.l_in_current_max", "A"),
        ("Cell max charge", "cell.charge_max_a", "A"),
        ("Pack rated charge", "pack.charge_max_a", "A"),
        ("Regen pulse allowance", "pack.regen_pulse_a", "A"),
        ("Battery Current Max Regen", "mc.l_in_current_min", "A"),
    ],
    "cutoffs_vs_tiltback": [
        ("Full charge", "pack.full_v", "V"), ("Empty (cell min)", "pack.empty_v", "V"),
        ("si_battery_cells", "mc.si_battery_cells", ""),
        ("Cutoff start", "mc.l_battery_cut_start", "V"),
        ("Cutoff start per cell", "thr.l_battery_cut_start_per_cell", "V"),
        ("Cutoff end", "mc.l_battery_cut_end", "V"),
        ("Cutoff end per cell", "thr.l_battery_cut_end_per_cell", "V"),
        ("tiltback_lv (raw)", "rf.tiltback_lv", "V"), ("LV is per-cell", "thr.lv_is_per_cell", ""),
        ("LV pushback effective", "thr.lv_v", "V"), ("LV per cell", "thr.lv_v_per_cell", "V"),
        ("tiltback_hv (raw)", "rf.tiltback_hv", "V"), ("HV is per-cell", "thr.hv_is_per_cell", ""),
        ("HV pushback effective", "thr.hv_v", "V"),
        ("Undervoltage fault (l_min_vin)", "mc.l_min_vin", "V"),
        ("Overvoltage fault (l_max_vin)", "mc.l_max_vin", "V"),
        ("Controller max operating", "hw.vendor.max_operating_v", "V"),
        ("Firmware Vin limit", "hw.fw_limits.vin_max", "V"),
    ],
    "duty_vs_fw": [
        ("Max duty", "mc.l_max_duty", ""), ("Max duty − 0.05", "duty.margin_point", ""),
        ("Duty pushback threshold", "rf.tiltback_duty", ""),
        ("Duty current limit start", "mc.l_duty_start", ""),
        ("FW current max", "mc.foc_fw_current_max", "A"), ("FW duty start", "mc.foc_fw_duty_start", ""),
        ("FW / motor max", "fw.fraction_of_motor_max", ""),
        ("Worst-case sag at battery max", "duty.sag_v", "V"),
        ("Sag / full charge", "duty.sag_fraction", ""),
    ],
    "imu_bus": [
        ("IMU part", "imu.part", ""), ("Firmware variant", "imu.variant", ""),
        ("Bus", "imu.bus_kind", ""), ("Bus speed", "imu.bus_khz", "kHz"),
        ("Configured sample rate", "app.imu_conf.sample_rate_hz", "Hz"),
        ("Firmware rate cap", "imu.bus_max_rate_hz", "Hz"),
        ("Effective loop rate", "imu.effective_rate_hz", "Hz"),
        ("Measured control loop", "meta.measured.control_loop_hz", "Hz"),
        ("Zero vector frequency", "mc.foc_f_zv", "Hz"),
        ("App Mahony KP", "app.imu_conf.mahony_kp", ""), ("App Mahony KI", "app.imu_conf.mahony_ki", ""),
        ("Accel/gyro filter", "app.imu_conf.filter", ""),
    ],
    "flux_norm": [
        ("Motor poles", "mc.si_motor_poles", ""), ("Flux linkage", "mc.foc_motor_flux_linkage", "Wb"),
        ("k = poles·λ / (30 · 0.027)", "torque.k", ""),
        ("Phase amps per configured amp (1/k)", "torque.amps_per_ref_amp", ""),
        ("Times converted from 1.2", "meta.tune_conversions_from_1_2", ""),
    ],
}

# Refloat parameters the 1.2 -> 1.3 conversion scales (ui.qml.in:1436-1444).
TORQUE_MULTIPLY = ("kp", "kp2", "ki", "ki_limit", "booster_current", "brkbooster_current",
                   "torquetilt_start_current", "atr_amps_accel_ratio", "atr_amps_decel_ratio")
TORQUE_DIVIDE = ("torquetilt_strength", "torquetilt_strength_regen")


def _finding_block(r: engine.Result) -> list[str]:
    rule = r.rule
    lines = [f"#### {rule.id} — {rule.title}",
             f"*{rule.severity}* · rule basis **[{rule.evidence}]** · category {rule.category}", "",
             r.message, "", f"Why: {rule.rationale}"]
    if r.weak_inputs:
        lines += ["", "Rests on unconfirmed inputs: " + ", ".join(
            f"`{k}` [{v}]" for k, v in sorted(r.weak_inputs.items())) + "."]
    lines += ["", "Sources: " + "; ".join(_link(s) for s in rule.sources), ""]
    return lines


def _link(s: str) -> str:
    if s.startswith("http"):
        tail = s.split("/blob/", 1)[-1].split("/", 1)[-1] if "/blob/" in s else s
        return f"[{tail}]({s})"
    return f"`{s}`"


def _diff_rows(b: Bundle, kind: str):
    c = cat.load(kind)
    cfg = {"mcconf": b.mc, "appconf": b.app, "refloat": b.rf}[kind]
    overrides = profiles.default_overrides(b.hw) if kind == "mcconf" else {}
    rows, calib = [], []
    for name in sorted(cfg.values):
        p = c.get(name)
        if p is None or p["type"] in ("string", "undefined"):
            continue
        v = cfg.values[name]
        if name in overrides:
            d, dsrc = overrides[name][0], f"{b.hw.id} hwconf"
        else:
            d, dsrc = p.get("default"), p.get("default_source", "")
            dsrc = "firmware header" if "header" in dsrc or dsrc.startswith("bldc") else (
                "settings.xml" if "settings.xml" in dsrc else "vesc_tool XML")
        if d is None:
            continue
        same = (abs(v - d) <= 1e-6 * max(1.0, abs(d))) if isinstance(v, float) or isinstance(d, float) else v == d
        if same:
            continue
        row = (name, p.get("long_name") or "", c.describe_value(name, v), c.describe_value(name, d), dsrc)
        (calib if _CALIBRATION.match(name) else rows).append(row)
    return rows, calib


def _diff_section(b: Bundle) -> list[str]:
    out = ["## Diff against defaults", "",
           "Defaults are what a freshly flashed controller holds: `motor/mcconf_default.h` and "
           "`applications/appconf_default.h` from bldc `release_7_00`, overlaid with this hardware's "
           "hwconf overrides, and `src/conf/settings.xml` from Refloat v1.3.1. The vesc_tool "
           "`res/config` XML defaults are a snapshot from one board and are only used where the "
           "header value is not numeric (enums).", ""]
    for kind, title in (("mcconf", "Motor config"), ("appconf", "App config"), ("refloat", "Refloat config")):
        rows, calib = _diff_rows(b, kind)
        out += [f"### {title} ({len(rows)} changed)", ""]
        if rows:
            out += ["| Parameter | Name | Value | Default | Default from |", "|---|---|---|---|---|"]
            out += [f"| `{n}` | {_md_escape(ln)} | {_md_escape(v)} | {_md_escape(d)} | {s} |"
                    for n, ln, v, d, s in rows]
        else:
            out.append("No changes from defaults.")
        if calib:
            out += ["", f"<details><summary>{len(calib)} detection / calibration values "
                    f"(expected to differ)</summary>", "",
                    "| Parameter | Value | Default |", "|---|---|---|"]
            out += [f"| `{n}` | {_md_escape(v)} | {_md_escape(d)} |" for n, _, v, d, _ in calib]
            out += ["", "</details>"]
        out.append("")
    return out


def _flux_table(b: Bundle, ns: Namespace) -> list[str]:
    k = ns.values.get("torque.k")
    out = ["", "Torque-scaled Refloat parameters. *1.2-equivalent* is the value a 1.2 tune would "
           "have needed for the same phase current (value ÷ k, or × k for strengths); if this tune "
           "was converted exactly once, that column is the original 1.2 tune.", "",
           "| Parameter | Value | Default | 1.2-equivalent |", "|---|---|---|---|"]
    rf = cat.load("refloat")
    for name in TORQUE_MULTIPLY + TORQUE_DIVIDE:
        v = b.rf.values.get(name)
        if v is None:
            continue
        eq = None if not k else (v / k if name in TORQUE_MULTIPLY else v * k)
        out.append(f"| `{name}` | {fmt(v)} | {fmt(rf.default(name))} | {fmt(eq)} |")
    return out


def render(b: Bundle, ns: Namespace, results: list[engine.Result], today: str | None = None) -> str:
    today = today or _dt.date.today().isoformat()
    by = {o: [r for r in results if r.outcome == o] for o in OUTCOME_LABEL}
    fired = by["fired"]
    crit = [r for r in fired if r.rule.severity == "critical"]
    m = b.meta
    out = [f"# Configuration audit — {b.label}", "",
           f"Generated {today} by vesc-float-audit from `{b.path}`.", "", f"> {DISCLAIMER}", "",
           "| | |", "|---|---|",
           f"| Hardware | {b.hw.name} (`{b.hw.id}`) |",
           f"| Firmware | {m['firmware']} ({m.get('firmware_variant', 'stock')}) |",
           f"| Package | Refloat {m['package_version']}"
           + ("" if ns.values.get("ver.package_is_tag") else
              f" — not a release tag; audited as v{ns.values.get('ver.package_pinned') or '?'}") + " |",
           f"| Motor | {m['motor'].get('name', '')} (profile `{b.motor.id}`) |",
           f"| Pack | {m['pack']['s']}S{m['pack']['p']}P {b.cell.name} |",
           f"| BMS | {m['bms']} |", "",
           "## Summary", "",
           f"- **{len(crit)} red flag(s)** (critical findings)",
           f"- {sum(1 for r in fired if r.rule.severity == 'warning')} warning(s), "
           f"{sum(1 for r in fired if r.rule.severity == 'info')} info note(s)",
           f"- {len(by['not_evaluated'])} rule(s) not evaluated (missing inputs)",
           f"- {len(by['passed_unverified'])} rule(s) without a finding but resting on unconfirmed inputs",
           f"- {len(by['passed'])} rule(s) without a finding on confirmed inputs",
           f"- {len(by['not_applicable'])} rule(s) not applicable", ""]

    out += ["## Red flags", ""]
    if crit:
        for r in crit:
            out += _finding_block(r)
    else:
        out += ["No critical rule fired. Check the *not evaluated* and *unconfirmed* lists "
                "before reading this as reassurance.", ""]

    out += ["## Cross-checks", ""]
    for key, title in engine.CROSSCHECKS.items():
        out += [f"### {title}", "", "| Quantity | Value | Key | Evidence |", "|---|---|---|---|"]
        out += [_row(ns, lbl, k, u) for lbl, k, u in CROSSCHECK_ROWS[key]]
        if key == "flux_norm":
            out += _flux_table(b, ns)
        rel = [r for r in results if r.rule.crosscheck == key and r.outcome != "not_applicable"]
        out += ["", "| Rule | Severity | Outcome | Detail |", "|---|---|---|---|"]
        for r in rel:
            detail = r.message if r.fired else (
                "missing: " + ", ".join(f"`{x}`" for x in r.missing) if r.outcome == "not_evaluated" else
                ("unconfirmed: " + ", ".join(f"`{x}`" for x in sorted(r.weak_inputs))
                 if r.outcome == "passed_unverified" else ""))
            out.append(f"| {r.rule.id} {_md_escape(r.rule.title)} | {r.rule.severity} | "
                       f"{OUTCOME_LABEL[r.outcome]} | {_md_escape(detail)} |")
        out.append("")

    others = [r for r in fired if r.rule.severity != "critical"]
    out += ["## Other findings", ""]
    for sev in ("warning", "info"):
        lst = [r for r in others if r.rule.severity == sev]
        out += [f"### {sev.capitalize()}s ({len(lst)})", ""]
        for r in lst:
            out += _finding_block(r)
        if not lst:
            out += ["None.", ""]

    out += ["## Not evaluated", "",
            "These rules could not run because an input is missing (no vendor figure, no "
            "reference value for this motor, no log, or a parameter absent from the export). "
            "Each is an open question, not a pass.", ""]
    if by["not_evaluated"]:
        out += ["| Rule | Severity | Missing |", "|---|---|---|"]
        out += [f"| {r.rule.id} {_md_escape(r.rule.title)} | {r.rule.severity} | "
                f"{', '.join(f'`{x}`' for x in r.missing)} |" for r in by["not_evaluated"]]
    else:
        out.append("None.")
    out += ["", "## No finding, but unconfirmed", "",
            "These rules did not fire, but at least one input is UNVERIFIED or a community/analysis "
            "figure. Confirm the inputs before relying on them.", ""]
    if by["passed_unverified"]:
        out += ["| Rule | Severity | Unconfirmed inputs |", "|---|---|---|"]
        out += [f"| {r.rule.id} {_md_escape(r.rule.title)} | {r.rule.severity} | "
                + ", ".join(f"`{k}` [{v}]" for k, v in sorted(r.weak_inputs.items())) + " |"
                for r in by["passed_unverified"]]
    else:
        out.append("None.")
    out += ["", "## No finding on confirmed inputs", "",
            ", ".join(r.rule.id for r in by["passed"]) or "None.", ""]

    out += _diff_section(b)
    out += _logs_section(b, ns)
    out += _notes_section(b)
    out += _provenance(b)
    return "\n".join(out).rstrip() + "\n"


def _logs_section(b: Bundle, ns: Namespace) -> list[str]:
    out = ["## Ride logs", ""]
    if not b.logs:
        return out + ["No ride logs in the bundle; log rules were not applicable.", ""]
    for lg in b.logs:
        out.append(f"- `{lg.name}`: {lg.source}, {len(lg.rows)} samples, format evidence [{lg.evidence}]"
                   + ("".join(f"; {n}" for n in lg.notes)))
    out += ["", "| Metric | Value |", "|---|---|"]
    for k in sorted(x for x in ns.values if x.startswith("log.") and x != "log.present"):
        out.append(f"| `{k}` | {fmt(ns.values[k])} |")
    return out + [""]


def _notes_section(b: Bundle) -> list[str]:
    out = ["## Parse notes", ""]
    any_ = False
    for kind, cfg in (("mcconf", b.mc), ("appconf", b.app), ("refloat", b.rf)):
        bits = []
        if cfg.config_version is not None:
            bits.append(f"ConfigVersion {cfg.config_version}")
        if cfg.unknown:
            bits.append("unknown: " + ", ".join(f"`{x}`" for x in cfg.unknown))
        if cfg.missing:
            bits.append(f"{len(cfg.missing)} missing: " + ", ".join(f"`{x}`" for x in cfg.missing[:20])
                        + (" …" if len(cfg.missing) > 20 else ""))
        if cfg.out_of_range:
            bits.append("out of range: " + ", ".join(f"`{n}`={v} (allowed {lo}…{hi})"
                                                       for n, v, lo, hi in cfg.out_of_range))
        if cfg.bad_values:
            bits.append("unparseable: " + ", ".join(f"`{n}`" for n, _ in cfg.bad_values))
        if bits:
            any_ = True
            out.append(f"- {kind}: " + "; ".join(bits))
    for n in b.load_notes:
        any_ = True
        out.append(f"- {n}")
    if not any_:
        out.append("None.")
    return out + [""]


def _provenance(b: Bundle) -> list[str]:
    out = ["## Provenance", "", "Parameter catalogs:", ""]
    seen = set()
    for kind in ("mcconf", "appconf", "refloat"):
        for name, p in cat.load(kind).provenance.items():
            if name in seen:
                continue
            seen.add(name)
            out.append(f"- {p['repo']} `{p['ref']}` @ `{p['commit'][:12]}`")
    out += ["", f"Profiles: hardware `{b.hw.id}`, cell `{b.cell.id}`, motor `{b.motor.id}` "
            "(`src/vfa/data/profiles/`). Evidence labels: Source = confirmed in pinned upstream "
            "source; Dev = documented by an author or vendor, not re-read; Comm = community rule "
            "of thumb; Analysis = engineering reasoning; UNVERIFIED = not confirmed from a primary "
            "source.", ""]
    return out
