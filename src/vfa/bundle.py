"""Audit bundle: one directory or zip per board.

Required files: mcconf.xml, appconf.xml, refloat.xml, meta.json.
Optional ride logs anywhere in the bundle (or under logs/):
  *.csv.zip / *.zip  Float Control
  *.json other than meta.json  Floaty
  *.csv              VESC Tool RT log or Float Control (detected by header)

meta.json fields (see docs/bundle-format.md):
  hardware          profile id: thor301 | ubox_single_100          (required)
  firmware          e.g. "7.00"                                    (required)
  firmware_variant  "stock" (default) | "rflt-xtras-0.5"
  package           "Refloat"                                      (required)
  package_version   e.g. "1.3.1"                                   (required)
  motor             {name, profile}  profile id under profiles/motors (required)
  pack              {s, p, cell}     cell = profile id under profiles/cells (required)
  bms               "charge-only" | "can" | "none" | free text    (required)
  board_name        free text
  tune_conversions_from_1_2   int or null (how many times "Convert from 1.2" was applied)
  battery_temp_monitored      bool or null
  measured          {control_loop_hz: number}  (from Refloat realtime data)
  export_source     "vesc_tool" (default) | "float_control" | free text
  hw_status         terminal `hw_status` output pasted as a string (or list of lines)
"""
from __future__ import annotations

import io
import json
import pathlib
import zipfile
from dataclasses import dataclass, field

from . import configxml, logs, profiles

REQUIRED = ("mcconf.xml", "appconf.xml", "refloat.xml", "meta.json")


class BundleError(ValueError):
    pass


@dataclass
class Bundle:
    path: str
    meta: dict
    mc: configxml.ParsedConfig
    app: configxml.ParsedConfig
    rf: configxml.ParsedConfig
    hw: profiles.Profile
    cell: profiles.Profile
    motor: profiles.Profile
    logs: list = field(default_factory=list)
    load_notes: list = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.meta.get("board_name") or pathlib.Path(self.path).stem


def _read_members(path: pathlib.Path) -> dict[str, bytes]:
    if path.is_dir():
        return {str(p.relative_to(path)).replace("\\", "/"): p.read_bytes()
                for p in sorted(path.rglob("*")) if p.is_file()}
    if zipfile.is_zipfile(path):
        out = {}
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            # Accept a single top-level folder inside the zip.
            tops = {n.split("/", 1)[0] for n in names}
            strip = len(tops) == 1 and all("/" in n for n in names)
            for n in names:
                key = n.split("/", 1)[1] if strip else n
                out[key] = z.read(n)
        return out
    raise BundleError(f"{path}: not a directory or zip file")


def validate_meta(meta) -> list[str]:
    errs = []
    if not isinstance(meta, dict):
        return ["meta.json must hold a JSON object"]
    for k in ("hardware", "firmware", "package", "package_version", "motor", "pack", "bms"):
        if meta.get(k) in (None, ""):
            errs.append(f"meta.json: '{k}' is required")
    pack = meta.get("pack")
    if pack is not None:
        if not isinstance(pack, dict):
            errs.append("meta.json: 'pack' must be an object {s, p, cell}")
        else:
            for k in ("s", "p"):
                if not isinstance(pack.get(k), int) or pack.get(k) < 1:
                    errs.append(f"meta.json: pack.{k} must be a positive integer")
            if not pack.get("cell"):
                errs.append("meta.json: pack.cell is required (cell profile id)")
    motor = meta.get("motor")
    if motor is not None and (not isinstance(motor, dict) or not motor.get("profile")):
        errs.append("meta.json: motor must be an object with a 'profile' id")
    if meta.get("package") not in (None, "") and str(meta["package"]).lower() != "refloat":
        errs.append(f"meta.json: package is {meta['package']!r}; only Refloat is supported")
    tc = meta.get("tune_conversions_from_1_2")
    if tc is not None and (not isinstance(tc, int) or tc < 0):
        errs.append("meta.json: tune_conversions_from_1_2 must be a non-negative integer or null")
    variant = meta.get("firmware_variant", "stock")
    if variant not in ("stock", "rflt-xtras-0.5"):
        errs.append(f"meta.json: firmware_variant {variant!r} unknown (stock | rflt-xtras-0.5)")
    return errs


def load(path) -> Bundle:
    path = pathlib.Path(path)
    members = _read_members(path)
    lower = {k.lower(): k for k in members}
    missing = [f for f in REQUIRED if f not in lower]
    if missing:
        raise BundleError(f"{path}: missing {', '.join(missing)}")
    try:
        meta = json.loads(members[lower["meta.json"]].decode("utf-8-sig"))
    except json.JSONDecodeError as e:
        raise BundleError(f"{path}: meta.json is not valid JSON: {e}") from e
    errs = validate_meta(meta)
    if errs:
        raise BundleError(f"{path}:\n  " + "\n  ".join(errs))
    meta.setdefault("firmware_variant", "stock")

    try:
        hw = profiles.load("hardware", meta["hardware"])
        cell = profiles.load("cell", meta["pack"]["cell"])
        motor = profiles.load("motor", meta["motor"]["profile"])
    except KeyError as e:
        raise BundleError(f"{path}: {e.args[0]}") from e

    try:
        mc = configxml.parse_bytes(members[lower["mcconf.xml"]], "mcconf")
        app = configxml.parse_bytes(members[lower["appconf.xml"]], "appconf")
        rf = configxml.parse_bytes(members[lower["refloat.xml"]], "refloat")
    except configxml.ConfigError as e:
        raise BundleError(f"{path}: {e}") from e

    b = Bundle(str(path), meta, mc, app, rf, hw, cell, motor)
    for name, data in members.items():
        low = name.lower()
        base = low.rsplit("/", 1)[-1]
        if base in REQUIRED:
            continue
        if base.endswith((".csv", ".zip", ".json")):
            try:
                b.logs.append(logs.parse_named(name, data))
            except (logs.LogError, zipfile.BadZipFile, UnicodeDecodeError) as e:
                b.load_notes.append(f"log not loaded: {e}")
    return b
