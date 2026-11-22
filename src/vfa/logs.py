"""Ride log parsers, normalised to one row format.

Common row keys (missing values are None):
    t (s from start), duty (fraction 0..1, signed where the source is),
    erpm, speed_kmh, v_batt, i_motor, i_batt, i_fw, pitch, true_pitch,
    setpoint, adc1, adc2, state, fault, temp_mos, temp_motor

Sources and evidence:
- VESC Tool RT log CSV: header written by vedderb/vesc_tool
  vescinterface.cpp (release_7_00) lines 1772-1830; ';'-separated with ','
  accepted on load (lines 1922-1925). duty_cycle is a fraction, ms_today in
  ms. [Source]
- Float Control CSV / .csv.zip and Floaty JSON: closed-source apps. Column
  and field names follow the third-party parser acheronfail/float-view
  (src/lib/parse/*.types.ts at fae12e5). [UNVERIFIED]: names and units are
  reverse-engineered, not documented by the app authors. Floaty speed units
  are not documented anywhere found; it is reported as-is.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass, field

ROW_KEYS = ("t", "duty", "erpm", "speed_kmh", "v_batt", "i_motor", "i_batt", "i_fw",
            "pitch", "true_pitch", "setpoint", "adc1", "adc2", "state", "fault",
            "temp_mos", "temp_motor")


class LogError(ValueError):
    pass


@dataclass
class RideLog:
    name: str
    source: str            # "float_control" | "floaty" | "vesc_tool"
    rows: list
    evidence: str          # "Source" or "UNVERIFIED"
    notes: list = field(default_factory=list)

    def series(self, key):
        return [r[key] for r in self.rows if r.get(key) is not None]


def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().rstrip("%")
    if s == "" or s.lower() in ("nan", "null", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _row(**kw):
    r = dict.fromkeys(ROW_KEYS)
    r.update(kw)
    return r


# ---- Float Control ----------------------------------------------------------

_FC = {
    "Time(s)": "t", "Duty%": "duty", "ERPM": "erpm", "Voltage": "v_batt",
    "I-Motor": "i_motor", "I-Battery": "i_batt", "I-FldWeak": "i_fw",
    "Pitch": "pitch", "True Pitch": "true_pitch", "Setpoint": "setpoint",
    "ADC1": "adc1", "ADC2": "adc2", "State": "state", "Motor-Fault": "fault",
    "T-Mosfet": "temp_mos", "T-Mot": "temp_motor",
}


def parse_float_control(text: str, name="float_control.csv") -> RideLog:
    reader = csv.reader(io.StringIO(text))
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        raise LogError(f"{name}: empty file")
    if "Time(s)" not in header or "Duty%" not in header:
        raise LogError(f"{name}: not a Float Control CSV (no Time(s)/Duty% columns)")
    idx = {h: i for i, h in enumerate(header)}
    mph = "Speed(mph)" in idx
    rows, skipped = [], 0
    for rec in reader:
        if len(rec) != len(header):
            skipped += 1   # e.g. the "Upgrade to Float Control Pro" line
            continue
        r = _row()
        for col, key in _FC.items():
            if col in idx:
                raw = rec[idx[col]]
                r[key] = raw.strip() if key == "state" else _num(raw)
        if r["duty"] is not None:
            r["duty"] /= 100.0
        sp = _num(rec[idx["Speed(mph)"]]) if mph else (
            _num(rec[idx["Speed(km/h)"]]) if "Speed(km/h)" in idx else None)
        r["speed_kmh"] = sp * 1.609344 if (mph and sp is not None) else sp
        rows.append(r)
    log = RideLog(name, "float_control", rows, "UNVERIFIED")
    if skipped:
        log.notes.append(f"skipped {skipped} line(s) that do not match the header")
    return log


# ---- Floaty -----------------------------------------------------------------

def parse_floaty_json(text: str, name="floaty.json") -> RideLog:
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise LogError(f"{name}: invalid JSON: {e}") from e
    logs = doc.get("logs") if isinstance(doc, dict) else None
    if not isinstance(logs, list):
        raise LogError(f"{name}: not a Floaty export (no 'logs' array)")
    t0 = logs[0].get("timestamp", 0) if logs else 0
    rows = []
    for e in logs:
        rows.append(_row(
            t=(_num(e.get("timestamp")) - t0) / 1000.0 if e.get("timestamp") is not None else None,
            duty=_num(e.get("dutyCycle")), v_batt=_num(e.get("batteryVolts")),
            i_motor=_num(e.get("motorCurrent")), i_batt=_num(e.get("batteryCurrent")),
            pitch=_num(e.get("pitchAngle")), true_pitch=_num(e.get("truePitchAngle")),
            adc1=_num(e.get("adc1")), adc2=_num(e.get("adc2")),
            state=e.get("state"), fault=_num(e.get("faultCode")),
            temp_mos=_num(e.get("controllerTemp")) or None,   # Floaty writes 0 on read failure
            temp_motor=_num(e.get("motorTemp")) or None,
            speed_kmh=_num(e.get("speed")),
        ))
    log = RideLog(name, "floaty", rows, "UNVERIFIED")
    log.notes.append("Floaty speed units are undocumented; speed_kmh is the raw 'speed' field")
    if isinstance(doc, dict) and "schemaVersion" in doc:
        log.notes.append(f"schemaVersion {doc['schemaVersion']}")
    return log


# ---- VESC Tool --------------------------------------------------------------

_VT = {
    "duty_cycle": "duty", "erpm": "erpm", "input_voltage": "v_batt",
    "current_motor": "i_motor", "current_in": "i_batt",
    "fault_code": "fault", "temp_mos_max": "temp_mos", "temp_motor": "temp_motor",
}


def parse_vesc_tool(text: str, name="vesc_tool.csv") -> RideLog:
    lines = text.splitlines()
    if not lines:
        raise LogError(f"{name}: empty file")
    sep = ";" if ";" in lines[0] else ","
    header = [h.strip() for h in lines[0].split(sep)]
    if "ms_today" not in header or "duty_cycle" not in header:
        raise LogError(f"{name}: not a VESC Tool RT log (no ms_today/duty_cycle columns)")
    idx = {h: i for i, h in enumerate(header)}
    rows, t0 = [], None
    for line in lines[1:]:
        rec = line.split(sep)
        if len(rec) < len(header):
            continue
        ms = _num(rec[idx["ms_today"]])
        if ms is None:
            continue
        t0 = ms if t0 is None else t0
        r = _row(t=(ms - t0) / 1000.0)
        for col, key in _VT.items():
            if col in idx:
                r[key] = _num(rec[idx[col]])
        if "speed_meters_per_sec" in idx:
            v = _num(rec[idx["speed_meters_per_sec"]])
            r["speed_kmh"] = None if v is None else v * 3.6
        rows.append(r)
    log = RideLog(name, "vesc_tool", rows, "Source")
    log.notes.append("IMU columns (roll/pitch/yaw) are not mapped: their units were not "
                     "confirmed from source")
    return log


# ---- dispatch ---------------------------------------------------------------

def parse_named(name: str, data: bytes) -> RideLog:
    lower = name.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            members = [m for m in z.namelist() if m.lower().endswith(".csv")]
            if not members:
                raise LogError(f"{name}: zip holds no .csv")
            text = z.read(members[0]).decode("utf-8-sig", errors="replace")
        return parse_float_control(text, name)
    text = data.decode("utf-8-sig", errors="replace")
    if lower.endswith(".json"):
        return parse_floaty_json(text, name)
    if lower.endswith(".csv"):
        first = text.split("\n", 1)[0]
        if "ms_today" in first:
            return parse_vesc_tool(text, name)
        if "Time(s)" in first:
            return parse_float_control(text, name)
        raise LogError(f"{name}: unrecognised CSV header (Floaty CSV is not supported; "
                       f"export Floaty as JSON)")
    raise LogError(f"{name}: unsupported log type")
