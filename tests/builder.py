"""Build synthetic audit bundles for tests and examples.

Configs start from the pinned catalog defaults (with the hardware's hwconf
overrides for mcconf) and are written exactly as VESC Tool's
ConfigParams::getXML writes them. Nothing here is real board data.
"""
from __future__ import annotations

import json
import pathlib
import xml.sax.saxutils as sx

from vfa import catalog as cat
from vfa import profiles


def defaults(kind: str, hardware: str | None = None) -> dict:
    c = cat.load(kind)
    vals = {}
    for name, p in c.params.items():
        if p["type"] == "undefined":
            continue
        v = p.get("default")
        if v is None:
            v = p.get("xml_default")
        if v is None:
            if p["type"] == "string":
                v = ""
            else:
                continue
        vals[name] = v
    if kind == "mcconf" and hardware:
        for name, (v, _src) in profiles.default_overrides(profiles.load("hardware", hardware)).items():
            vals[name] = v
    return vals


def to_xml(kind: str, values: dict) -> str:
    root = cat.load(kind).xml_root
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', f"<{root}>", "    <ConfigVersion>4</ConfigVersion>"]
    for name, v in values.items():
        if isinstance(v, bool):
            v = int(v)
        if isinstance(v, float):
            text = f"{v:.6g}"     # QString::number(double): 6 significant digits
        else:
            text = sx.escape(str(v))
        lines.append(f"    <{name}>{text}</{name}>")
    lines.append(f"</{root}>")
    return "\n".join(lines) + "\n"


BOARD_A_META = {
    "board_name": "Example A (synthetic)",
    "hardware": "thor301", "firmware": "7.00", "firmware_variant": "stock",
    "package": "Refloat", "package_version": "1.3.1",
    "motor": {"name": "Hypercore stator, TFL MTE 5in hub, N52", "profile": "hypercore_mte5_n52"},
    "pack": {"s": 20, "p": 2, "cell": "molicel_p45b"},
    "bms": "charge-only",
}
BOARD_B_META = {
    "board_name": "Example B (synthetic)",
    "hardware": "ubox_single_100", "firmware": "7.00", "firmware_variant": "stock",
    "package": "Refloat", "package_version": "1.3.1",
    "motor": {"name": "Onewheel Pint hub (original)", "profile": "pint_stock"},
    "pack": {"s": 15, "p": 1, "cell": "molicel_p45b"},
    "bms": "charge-only",
}

# A deliberately reasonable Board A tune, per docs/knowledge-base.md §2.
BOARD_A_MC = {
    "si_motor_poles": 30, "si_battery_cells": 20, "si_battery_ah": 9.0,
    "foc_motor_flux_linkage": 0.0295, "foc_motor_r": 0.092, "foc_motor_l": 0.000210,
    "foc_motor_ld_lq_diff": 0.0, "foc_observer_gain": 1.1e6,
    "foc_current_kp": 0.21, "foc_current_ki": 92.0,
    "l_current_max": 120.0, "l_current_min": -120.0, "l_abs_current_max": 200.0,
    "l_in_current_max": 70.0, "l_in_current_min": -45.0,
    "l_battery_cut_start": 54.0, "l_battery_cut_end": 50.0,
    "l_temp_accel_dec": 0.0, "foc_f_zv": 25000.0,
}
BOARD_A_APP = {"imu_conf.sample_rate_hz": 832, "imu_conf.mahony_kp": 0.2, "imu_conf.mahony_ki": 0.0,
               "app_to_use": 0}
BOARD_A_RF = {"tiltback_hv": 4.2, "tiltback_lv": 3.0, "fault_delay_switch_full": 300,
              "fault_delay_switch_half": 500, "meta.is_default": 0}

BOARD_B_MC = {
    "si_motor_poles": 30, "si_battery_cells": 15, "si_battery_ah": 4.5,
    "foc_motor_flux_linkage": 0.0240, "foc_motor_r": 0.140, "foc_motor_l": 0.000250,
    "l_current_max": 110.0, "l_current_min": -110.0, "l_abs_current_max": 160.0,
    "l_in_current_max": 38.0, "l_in_current_min": -22.0,
    "l_battery_cut_start": 40.5, "l_battery_cut_end": 37.5,
    "l_temp_accel_dec": 0.0, "foc_f_zv": 25000.0,
}
BOARD_B_APP = {"imu_conf.sample_rate_hz": 832, "imu_conf.mahony_kp": 0.2, "imu_conf.mahony_ki": 0.0,
               "app_to_use": 0}
BOARD_B_RF = {"tiltback_hv": 4.2, "tiltback_lv": 3.0, "tiltback_duty": 0.78,
              "fault_delay_switch_full": 300, "fault_delay_switch_half": 500, "meta.is_default": 0}


def write_bundle(path, meta, mc=None, app=None, rf=None, logs=None, drop=()):
    path = pathlib.Path(path)
    path.mkdir(parents=True, exist_ok=True)
    m = defaults("mcconf", meta.get("hardware"))
    m.update(mc or {})
    a = defaults("appconf")
    a.update(app or {})
    r = defaults("refloat")
    r.update(rf or {})
    for kind, vals, fname in (("mcconf", m, "mcconf.xml"), ("appconf", a, "appconf.xml"),
                              ("refloat", r, "refloat.xml")):
        vals = {k: v for k, v in vals.items() if k not in drop}
        (path / fname).write_text(to_xml(kind, vals))
    (path / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    for name, content in (logs or {}).items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content)
    return path


def board_a(path, mc=None, app=None, rf=None, meta=None, **kw):
    mm = dict(BOARD_A_MC); mm.update(mc or {})
    aa = dict(BOARD_A_APP); aa.update(app or {})
    rr = dict(BOARD_A_RF); rr.update(rf or {})
    me = json.loads(json.dumps(BOARD_A_META)); me.update(meta or {})
    return write_bundle(path, me, mm, aa, rr, **kw)


def board_b(path, mc=None, app=None, rf=None, meta=None, **kw):
    mm = dict(BOARD_B_MC); mm.update(mc or {})
    aa = dict(BOARD_B_APP); aa.update(app or {})
    rr = dict(BOARD_B_RF); rr.update(rf or {})
    me = json.loads(json.dumps(BOARD_B_META)); me.update(meta or {})
    return write_bundle(path, me, mm, aa, rr, **kw)
