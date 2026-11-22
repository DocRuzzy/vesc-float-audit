"""Build the flat namespace that rule expressions read.

Prefixes:
  mc.*  app.*  rf.*    raw values from the exported configs
  hw.*  cell.*  motor.*  profile values (evidence per key)
  meta.*               owner-reported bundle metadata
  pack.*  thr.*  torque.*  imu.*  ver.*  log.*   derived quantities

Every derived key records the keys it was computed from (``deps``), so a
finding can name the UNVERIFIED inputs it rests on.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources

from .bundle import Bundle

# Refloat 1.3 reference motor: currents are interpreted as on a 30-pole,
# 27 mWb motor. refloat src/lib/utils.h:37-38 (TORQUE_CONSTANT_COMPAT) and
# ui.qml.in:1449-1458 (torqueConstantRatio). [Source]
REF_POLES = 30
REF_FLUX_WB = 0.027

# Below this, Refloat treats tiltback_hv/lv as volts per cell and multiplies
# by si_battery_cells. refloat src/motor_data.c:78-90. [Source]
PER_CELL_THRESHOLD_V = 10.0


@dataclass
class Namespace:
    values: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    deps: dict = field(default_factory=dict)

    def set(self, key, value, evidence="Source", source="", deps=()):
        self.values[key] = value
        self.evidence[key] = evidence
        self.sources[key] = source
        if deps:
            self.deps[key] = tuple(deps)

    def lineage(self, key, _seen=None) -> set[str]:
        """The key and every key it was derived from, transitively."""
        _seen = set() if _seen is None else _seen
        if key in _seen:
            return set()
        _seen.add(key)
        out = {key}
        for d in self.deps.get(key, ()):
            out |= self.lineage(d, _seen)
        return out

    def get(self, key, default=None):
        v = self.values.get(key)
        return default if v is None else v


@lru_cache(maxsize=None)
def refloat_tags() -> frozenset:
    with resources.files("vfa.data.upstream").joinpath("refloat_tags.json").open() as f:
        return frozenset(json.load(f)["tags"])


def _norm_version(v: str) -> str:
    return str(v).strip().lstrip("vV")


def build(b: Bundle) -> Namespace:
    ns = Namespace()
    for prefix, cfg in (("mc", b.mc), ("app", b.app), ("rf", b.rf)):
        for k, v in cfg.values.items():
            ns.set(f"{prefix}.{k}", v, "config", f"{prefix} export")
    for prefix, prof in (("hw", b.hw), ("cell", b.cell), ("motor", b.motor)):
        for k, v in prof.values.items():
            ns.set(f"{prefix}.{k}", v, prof.evidence.get(k, "n/a"), prof.sources.get(k, ""))

    m = b.meta
    for k in ("hardware", "firmware", "firmware_variant", "package_version", "bms",
              "tune_conversions_from_1_2", "battery_temp_monitored"):
        ns.set(f"meta.{k}", m.get(k), "owner-reported", "meta.json")
    ns.set("meta.measured.control_loop_hz", (m.get("measured") or {}).get("control_loop_hz"),
           "owner-reported", "meta.json")
    ns.set("meta.charge_only_bms", str(m.get("bms", "")).lower() in ("charge-only", "charge_only"),
           "owner-reported", "meta.json", deps=["meta.bms"])

    for prefix, cfg in (("mc", b.mc), ("app", b.app), ("rf", b.rf)):
        ns.set(f"cfg.{prefix}_unknown", len(cfg.unknown), "derived")
        ns.set(f"cfg.{prefix}_missing", len(cfg.missing), "derived")
        ns.set(f"cfg.{prefix}_out_of_range", len(cfg.out_of_range), "derived")
        ns.set(f"cfg.{prefix}_bad_values", len(cfg.bad_values), "derived")
        ns.set(f"cfg.{prefix}_config_version", cfg.config_version, "config")
    ns.set("meta.export_source", m.get("export_source", "vesc_tool"), "owner-reported", "meta.json")

    _versions(ns, m)
    _pack(ns, m)
    _thermal(ns)
    _erpm(ns)
    _thresholds(ns)
    _torque(ns)
    _speed(ns)
    _imu(ns, b)
    _misc(ns)
    _log_metrics(ns, b)
    return ns


def _versions(ns: Namespace, m):
    pv = _norm_version(m["package_version"])
    tags = refloat_tags()
    is_tag = f"v{pv}" in tags
    pinned = pv
    if not is_tag:
        # "1.3.1.1" style: strip trailing components until a real tag matches.
        parts = pv.split(".")
        while len(parts) > 1 and f"v{'.'.join(parts)}" not in tags:
            parts = parts[:-1]
        pinned = ".".join(parts) if f"v{'.'.join(parts)}" in tags else None
    ns.set("ver.package", pv, "owner-reported", "meta.json", deps=["meta.package_version"])
    ns.set("ver.package_is_tag", is_tag, "Source",
           "lukash/refloat tags (src/vfa/data/upstream/refloat_tags.json)", deps=["meta.package_version"])
    ns.set("ver.package_pinned", pinned, "Source", "nearest lukash/refloat tag", deps=["meta.package_version"])
    ns.set("ver.firmware", _norm_version(m["firmware"]), "owner-reported", "meta.json",
           deps=["meta.firmware"])


def _pack(ns: Namespace, m):
    s, p = m["pack"]["s"], m["pack"]["p"]
    ns.set("pack.s", s, "owner-reported", "meta.json")
    ns.set("pack.p", p, "owner-reported", "meta.json")

    def mul(key, a, factor, deps):
        v = ns.values.get(a)
        ns.set(key, None if v is None else v * factor, "derived", "", deps=deps)

    mul("pack.continuous_a", "cell.continuous_discharge_a", p, ["pack.p", "cell.continuous_discharge_a"])
    if ns.values.get("pack.continuous_a") is not None and ns.values.get("cell.durable_derate") is not None:
        ns.set("pack.durable_a", ns.values["pack.continuous_a"] * ns.values["cell.durable_derate"],
               "derived", deps=["pack.continuous_a", "cell.durable_derate"])
    mul("pack.charge_max_a", "cell.charge_max_a", p, ["pack.p", "cell.charge_max_a"])
    if ns.values.get("pack.charge_max_a") is not None and ns.values.get("cell.regen_pulse_factor"):
        ns.set("pack.regen_pulse_a", ns.values["pack.charge_max_a"] * ns.values["cell.regen_pulse_factor"],
               "derived", deps=["pack.charge_max_a", "cell.regen_pulse_factor"])
    mul("pack.full_v", "cell.v_max", s, ["pack.s", "cell.v_max"])
    mul("pack.empty_v", "cell.v_min", s, ["pack.s", "cell.v_min"])
    if ns.values.get("cell.dcr_ohm_max") is not None:
        ns.set("pack.dcr_ohm_max", ns.values["cell.dcr_ohm_max"] * s / p, "derived",
               deps=["cell.dcr_ohm_max", "pack.s", "pack.p"])


def _thermal(ns: Namespace):
    # Firmware lowers the acceleration current limits' temperature window:
    # start' = map(accel_dec, 0..1, start..25 °C). bldc motor/mc_interface.c:2392-2395. [Source]
    dec = ns.values.get("mc.l_temp_accel_dec")
    if dec is None:
        return
    for which in ("fet", "motor"):
        for edge in ("start", "end"):
            v = ns.values.get(f"mc.l_temp_{which}_{edge}")
            if v is not None:
                ns.set(f"thm.{which}_accel_{edge}", v + dec * (25.0 - v), "Source",
                       "bldc motor/mc_interface.c:2392-2395",
                       deps=["mc.l_temp_accel_dec", f"mc.l_temp_{which}_{edge}"])


def _erpm(ns: Namespace):
    # Approximate no-load electrical speed at full charge and max duty:
    # w_e = V * duty / (sqrt(3) * lambda), ERPM = w_e * 60 / (2 pi). [Analysis]
    v = ns.values.get("pack.full_v")
    duty = ns.values.get("mc.l_max_duty")
    flux = ns.values.get("mc.foc_motor_flux_linkage")
    if v and duty and flux and flux > 0.001:
        import math
        erpm = v * duty / (math.sqrt(3) * flux) * 60 / (2 * math.pi)
        ns.set("erpm.no_load_max", erpm, "Analysis", "SVPWM linear-range estimate",
               deps=["pack.full_v", "mc.l_max_duty", "mc.foc_motor_flux_linkage"])


def _thresholds(ns: Namespace):
    cells_cfg = ns.values.get("mc.si_battery_cells")
    s = ns.values["pack.s"]
    for kind in ("lv", "hv"):
        raw = ns.values.get(f"rf.tiltback_{kind}")
        if raw is None:
            continue
        per_cell = raw < PER_CELL_THRESHOLD_V
        if per_cell and cells_cfg and cells_cfg > 0:
            eff = raw * cells_cfg
        else:
            eff = raw   # absolute volts, or per-cell value used as-is when cells = 0
        src = "refloat src/motor_data.c:78-90"
        ns.set(f"thr.{kind}_is_per_cell", per_cell, "Source", src, deps=[f"rf.tiltback_{kind}"])
        ns.set(f"thr.{kind}_v", eff, "Source", src, deps=[f"rf.tiltback_{kind}", "mc.si_battery_cells"])
        ns.set(f"thr.{kind}_v_per_cell", eff / s, "derived", deps=[f"thr.{kind}_v", "pack.s"])
    for key in ("l_battery_cut_start", "l_battery_cut_end"):
        v = ns.values.get(f"mc.{key}")
        if v is not None:
            ns.set(f"thr.{key}_per_cell", v / s, "derived", deps=[f"mc.{key}", "pack.s"])


def _torque(ns: Namespace):
    poles = ns.values.get("mc.si_motor_poles")
    flux = ns.values.get("mc.foc_motor_flux_linkage")
    if poles and flux and flux > 0.001:
        k = poles * flux / (REF_POLES * REF_FLUX_WB)
        ns.set("torque.k", k, "Source", "refloat ui.qml.in:1449-1458",
               deps=["mc.si_motor_poles", "mc.foc_motor_flux_linkage"])
        # Phase amps actually commanded per "Refloat amp" at runtime:
        # gain * TORQUE_CONSTANT_COMPAT / Kt_actual = 1/k (pid.c:61, motor_data.c:106,194)
        ns.set("torque.amps_per_ref_amp", 1 / k, "Source", "refloat src/pid.c:61, src/motor_data.c:106,194",
               deps=["torque.k"])
        mp = ns.values.get("motor.poles")
        if mp:
            kp_ = mp * flux / (REF_POLES * REF_FLUX_WB)
            ns.set("torque.k_profile_poles", kp_, "derived",
                   deps=["motor.poles", "mc.foc_motor_flux_linkage"])
            # Factor by which Refloat currently over-commands current relative to the
            # profile's pole count, and the speed over-report factor
            # (bldc mc_interface.c:1626: rpm = erpm / (poles / 2)).
            ns.set("torque.pole_error_factor", kp_ / k, "derived",
                   deps=["torque.k_profile_poles", "torque.k"])
            ns.set("speed.report_factor", mp / poles, "derived",
                   deps=["motor.poles", "mc.si_motor_poles"])
    else:
        ns.set("torque.k", None, "Source", "flux linkage or poles missing/zero: Refloat falls back "
               "to the reference motor (motor_data.c:105-109)",
               deps=["mc.si_motor_poles", "mc.foc_motor_flux_linkage"])


def _speed(ns: Namespace):
    f, ts = ns.values.get("speed.report_factor"), ns.values.get("rf.tiltback_speed")
    if f and ts:
        ns.set("speed.pushback_true_kmh", ts / f, "derived", deps=["speed.report_factor", "rf.tiltback_speed"])


def _imu(ns: Namespace, b: Bundle):
    variant = b.meta.get("firmware_variant", "stock")
    ns.set("imu.variant", variant, "owner-reported", "meta.json")
    for field_ in ("kind", "khz", "max_rate_hz"):
        key = f"hw.imu.bus.{variant}.{field_}"
        ns.set(f"imu.bus_{field_}", ns.values.get(key), b.hw.evidence.get(f"imu.bus.{variant}.{field_}", "UNVERIFIED"),
               b.hw.sources.get(f"imu.bus.{variant}.{field_}", "no profile entry for this variant"), deps=[key])
    ns.set("imu.part", ns.values.get("hw.imu.part"), b.hw.evidence.get("imu.part", "UNVERIFIED"),
           b.hw.sources.get("imu.part", ""), deps=["hw.imu.part"])
    rate = ns.values.get("app.imu_conf.sample_rate_hz")
    cap = ns.values.get("imu.bus_max_rate_hz")
    if rate is not None:
        eff = min(rate, cap) if cap else rate
        ns.set("imu.effective_rate_hz", eff, "Source", "firmware rate cap where known",
               deps=["app.imu_conf.sample_rate_hz", "imu.bus_max_rate_hz"])


def _misc(ns: Namespace):
    fw = ns.values.get("mc.foc_fw_current_max")
    if fw is not None:
        ns.set("fw.enabled", fw > 0, "derived", deps=["mc.foc_fw_current_max"])
    cmax = ns.values.get("mc.l_current_max")
    absmax = ns.values.get("mc.l_abs_current_max")
    if cmax and absmax is not None:
        ns.set("cur.abs_ratio", absmax / cmax, "derived", deps=["mc.l_abs_current_max", "mc.l_current_max"])
    if fw is not None and cmax:
        ns.set("fw.fraction_of_motor_max", fw / cmax, "derived",
               deps=["mc.foc_fw_current_max", "mc.l_current_max"])
    # l_max_duty - 0.05. Refloat computes the same value (motor_data.c:100) but only uses
    # it in its wheelslip/traction-control logic (main.c:502, 652), not as a pushback.
    md = ns.values.get("mc.l_max_duty")
    if md is not None:
        ns.set("duty.margin_point", md - 0.05, "Analysis", "l_max_duty - 0.05",
               deps=["mc.l_max_duty"])
    dcr, imax, vfull = (ns.values.get(k) for k in ("pack.dcr_ohm_max", "mc.l_in_current_max", "pack.full_v"))
    if dcr is not None and imax is not None and vfull:
        ns.set("duty.sag_v", dcr * imax, "derived", deps=["pack.dcr_ohm_max", "mc.l_in_current_max"])
        ns.set("duty.sag_fraction", dcr * imax / vfull, "derived", deps=["duty.sag_v", "pack.full_v"])
    a1, a2 = ns.values.get("rf.fault_adc1"), ns.values.get("rf.fault_adc2")
    if a1 is not None and a2 is not None:
        mode = "disabled" if (a1 == 0 and a2 == 0) else ("single" if (a1 == 0 or a2 == 0) else "dual")
        ns.set("footpad.mode", mode, "Source", "refloat src/footpad_sensor.c:33-46",
               deps=["rf.fault_adc1", "rf.fault_adc2"])


# ---- log metrics ------------------------------------------------------------

_RUNNING = re.compile(r"run|rid", re.I)


def _running(r) -> bool:
    st = r.get("state")
    if isinstance(st, str):
        return bool(_RUNNING.search(st))
    if isinstance(st, (int, float)):
        # Refloat state numbering is not stable across versions; treat
        # nonzero as running only when motor current is flowing.
        return abs(r.get("i_motor") or 0) > 0.5
    return abs(r.get("i_motor") or 0) > 0.5


def _log_metrics(ns: Namespace, b: Bundle):
    ns.set("log.present", bool(b.logs), "derived")
    if not b.logs:
        return
    rows = [r for lg in b.logs for r in lg.rows]
    run = [r for r in rows if _running(r)]
    evidence = "UNVERIFIED" if any(lg.evidence != "Source" for lg in b.logs) else "Source"
    src = ", ".join(lg.name for lg in b.logs)

    def put(key, value, deps=()):
        ns.set(key, value, evidence, src, deps=deps)

    def mx(seq):
        seq = [x for x in seq if x is not None]
        return max(seq) if seq else None

    put("log.samples", len(rows))
    put("log.running_samples", len(run))
    put("log.duty_max", mx(abs(r["duty"]) if r["duty"] is not None else None for r in run))
    vs = [r["v_batt"] for r in rows if r["v_batt"] is not None and r["v_batt"] > 1]
    put("log.v_min", min(vs) if vs else None)
    put("log.v_max", max(vs) if vs else None)
    put("log.i_motor_abs_max", mx(abs(r["i_motor"]) if r["i_motor"] is not None else None for r in run))
    put("log.i_batt_max", mx(r["i_batt"] for r in run))
    ib = [r["i_batt"] for r in run if r["i_batt"] is not None]
    put("log.i_batt_min", min(ib) if ib else None)
    put("log.temp_mos_max", mx(r["temp_mos"] for r in rows))
    put("log.temp_motor_max", mx(r["temp_motor"] for r in rows))
    faults = sorted({int(r["fault"]) for r in rows if r["fault"] not in (None, 0)})
    put("log.fault_codes", tuple(faults))
    put("log.fault_count", len(faults))

    cmax = ns.values.get("mc.l_current_max")
    if cmax and run:
        at = sum(1 for r in run if r["i_motor"] is not None and abs(r["i_motor"]) >= 0.97 * cmax)
        put("log.frac_motor_at_limit", at / len(run), deps=["mc.l_current_max"])
    bmax = ns.values.get("mc.l_in_current_max")
    if bmax and run:
        at = sum(1 for r in run if r["i_batt"] is not None and r["i_batt"] >= 0.97 * bmax)
        put("log.frac_batt_at_limit", at / len(run), deps=["mc.l_in_current_max"])
    # Footpad: samples while running where a sensor read below its threshold.
    a1, a2 = ns.values.get("rf.fault_adc1"), ns.values.get("rf.fault_adc2")
    if run and a1 and a2:
        low = sum(1 for r in run if (r["adc1"] is not None and r["adc1"] < a1)
                  or (r["adc2"] is not None and r["adc2"] < a2))
        put("log.footpad_low_while_running", low, deps=["rf.fault_adc1", "rf.fault_adc2"])
    # Sag: lowest voltage seen while battery current is high, against the max seen.
    hi = [r["v_batt"] for r in run if r["v_batt"] and r["i_batt"] is not None and bmax
          and r["i_batt"] >= 0.5 * bmax]
    if hi and vs:
        put("log.v_min_under_load", min(hi), deps=["mc.l_in_current_max"])
