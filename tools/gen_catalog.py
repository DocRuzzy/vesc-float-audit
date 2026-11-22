#!/usr/bin/env python3
"""Regenerate the vendored parameter catalogs from pinned upstream checkouts.

Usage:
    python3 tools/gen_catalog.py --vesc-tool DIR --bldc DIR --refloat DIR

The checkouts must be at the commits recorded in PINS below; the script
refuses to run otherwise. Output goes to src/vfa/data/upstream/.

Each catalog entry carries:
  name, long_name, type, min, max, editor_scale, suffix, enum_names, c_define
  default        - the value a freshly flashed controller holds (see below)
  default_source - where `default` came from
  xml_default    - the value in the upstream ConfigParams XML

For mcconf/appconf the firmware headers (motor/mcconf_default.h,
applications/appconf_default.h) are authoritative: the vesc_tool
res/config XML defaults are a snapshot from one board and differ for 28
mcconf parameters (e.g. foc_motor_flux_linkage, l_abs_current_max). Where
a header value cannot be parsed to a number (enum constants, expressions),
the XML default is used and default_source says so.
For Refloat, settings.xml is the source of the compiled defaults.
"""
import argparse, json, pathlib, re, subprocess, sys
import xml.etree.ElementTree as ET

PINS = {
    "vesc_tool": ("vedderb/vesc_tool", "release_7_00", "6528c4e2a963e86ae4104737ddf7c76ffc987d84"),
    "bldc": ("vedderb/bldc", "release_7_00", "e877eaead23e23cc0e160302d75554eaeb2c98d0"),
    "refloat": ("lukash/refloat", "v1.3.1", "a2b55d96f508653b0436b21410100aaf91f14b04"),
}
TYPES = {0: "undefined", 1: "double", 2: "int", 3: "string", 4: "enum", 5: "bool", 6: "bitfield"}
OUT = pathlib.Path(__file__).resolve().parent.parent / "src" / "vfa" / "data" / "upstream"


def head(d):
    return subprocess.check_output(["git", "-C", str(d), "rev-parse", "HEAD"], text=True).strip()


def header_defines(path):
    defs = {}
    for m in re.finditer(r"^\s*#define\s+(\w+)\s+(.+?)\s*(?://.*)?$", path.read_text(), re.M):
        defs.setdefault(m.group(1), m.group(2).strip())
    return defs


def to_number(text):
    t = text.strip().rstrip("fF")
    if t in ("true", "false"):
        return 1 if t == "true" else 0
    try:
        return float(t)
    except ValueError:
        return None


def parse_params(xml_path):
    root = ET.parse(xml_path).getroot().find("Params")
    out = {}
    for e in root:
        g = lambda k: e.findtext(k)
        t = TYPES.get(int(g("type") or 0), "undefined")
        entry = {
            "name": e.tag,
            "long_name": g("longName"),
            "type": t,
            "c_define": g("cDefine") or None,
            "suffix": (g("suffix") or "").strip() or None,
        }
        if t == "double":
            entry.update(min=float(g("minDouble")), max=float(g("maxDouble")),
                         editor_scale=float(g("editorScale") or 1), xml_default=float(g("valDouble")))
        elif t == "int":
            entry.update(min=int(g("minInt")), max=int(g("maxInt")),
                         editor_scale=float(g("editorScale") or 1), xml_default=int(g("valInt")))
        elif t in ("enum", "bool", "bitfield"):
            v = g("valInt")
            entry["xml_default"] = int(v) if v not in (None, "") else None
            if t == "enum":
                entry["enum_names"] = [x.text for x in e.findall("enumNames")]
        elif t == "string":
            entry["xml_default"] = g("valString")
        else:
            entry["xml_default"] = None
        out[e.tag] = entry
    return out


def apply_header_defaults(params, defs, header_label):
    for p in params.values():
        cd = p.get("c_define")
        val = to_number(defs[cd]) if cd and cd in defs else None
        in_range = val is not None and ("min" not in p or p["min"] <= val <= p["max"])
        if val is not None and not in_range:
            # e.g. APPCONF_CONTROLLER_ID -1: a "derive at boot" sentinel, never exported.
            p["default"] = p["xml_default"]
            p["default_source"] = f"vesc_tool res/config XML ({header_label} value {val:g} is a sentinel outside the range)"
        elif val is not None and p["type"] in ("double", "int", "bool", "enum"):
            p["default"] = int(val) if p["type"] != "double" else val
            p["default_source"] = header_label
        else:
            p["default"] = p["xml_default"]
            p["default_source"] = "vesc_tool res/config XML (header value not numeric or absent)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vesc-tool", required=True, type=pathlib.Path)
    ap.add_argument("--bldc", required=True, type=pathlib.Path)
    ap.add_argument("--refloat", required=True, type=pathlib.Path)
    a = ap.parse_args()
    dirs = {"vesc_tool": a.vesc_tool, "bldc": a.bldc, "refloat": a.refloat}
    for k, d in dirs.items():
        if head(d) != PINS[k][2]:
            sys.exit(f"{k} checkout is at {head(d)}, expected {PINS[k][2]}")

    prov = {k: {"repo": v[0], "ref": v[1], "commit": v[2]} for k, v in PINS.items()}
    mc = parse_params(a.vesc_tool / "res/config/7.00/parameters_mcconf.xml")
    apply_header_defaults(mc, header_defines(a.bldc / "motor/mcconf_default.h"), "bldc motor/mcconf_default.h")
    app = parse_params(a.vesc_tool / "res/config/7.00/parameters_appconf.xml")
    apply_header_defaults(app, header_defines(a.bldc / "applications/appconf_default.h"),
                          "bldc applications/appconf_default.h")
    rf = parse_params(a.refloat / "src/conf/settings.xml")
    for p in rf.values():
        p["default"] = p["xml_default"]
        p["default_source"] = "refloat src/conf/settings.xml"

    for fname, params, srcs in (
        ("mcconf_7.00.json", mc, ["vesc_tool", "bldc"]),
        ("appconf_7.00.json", app, ["vesc_tool", "bldc"]),
        ("refloat_1.3.1.json", rf, ["refloat"]),
    ):
        doc = {"provenance": {k: prov[k] for k in srcs}, "params": params}
        (OUT / fname).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print(f"wrote {fname}: {len(params)} params")


if __name__ == "__main__":
    main()
