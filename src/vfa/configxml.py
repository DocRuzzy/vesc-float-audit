"""Parser for VESC Tool "Save XML" config exports.

Format, from vedderb/vesc_tool configparams.cpp ConfigParams::getXML
(release_7_00, lines 1024-1060): a root element named after the config
(MCConfiguration, APPConfiguration or CustomConfiguration, see main.cpp
1293/1332/1371), an optional <ConfigVersion> child, then one child element
per parameter whose text is the raw value: integer for bool/enum/int/bitfield,
QString::number(double) for doubles (6 significant digits), plain text for
strings. Values are stored unscaled (e.g. flux linkage in Wb, not mWb).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from . import catalog as cat


class ConfigError(ValueError):
    pass


@dataclass
class ParsedConfig:
    kind: str
    values: dict
    config_version: int | None = None
    unknown: list = field(default_factory=list)   # in file, not in catalog
    missing: list = field(default_factory=list)   # in catalog, not in file
    bad_values: list = field(default_factory=list)
    out_of_range: list = field(default_factory=list)

    def get(self, name, default=None):
        return self.values.get(name, default)


def _convert(p: dict, text: str):
    t = p["type"]
    text = (text or "").strip()
    if t == "double":
        return float(text)
    if t in ("int", "enum", "bool", "bitfield"):
        # VESC Tool writes ints; tolerate "1.0" from hand-edited files.
        f = float(text)
        if f != int(f):
            raise ValueError(f"non-integer {text!r}")
        return int(f)
    if t == "string":
        return text
    return None


def parse_bytes(data: bytes, kind: str) -> ParsedConfig:
    catalog = cat.load(kind)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise ConfigError(f"{kind}: not well-formed XML: {e}") from e
    if root.tag != catalog.xml_root:
        if root.tag == "ConfigParams":
            raise ConfigError(
                f"{kind}: this is a parameter definition file (ConfigParams), not a "
                f"saved configuration. Export with VESC Tool's Save XML.")
        raise ConfigError(f"{kind}: root element is <{root.tag}>, expected <{catalog.xml_root}>")

    out = ParsedConfig(kind=kind, values={})
    seen = set()
    for child in root:
        name = child.tag
        if name == "ConfigVersion":
            try:
                out.config_version = int((child.text or "").strip())
            except ValueError:
                out.bad_values.append((name, child.text))
            continue
        seen.add(name)
        p = catalog.get(name)
        if p is None:
            out.unknown.append(name)
            continue
        try:
            v = _convert(p, child.text)
        except ValueError:
            out.bad_values.append((name, child.text))
            continue
        out.values[name] = v
        if isinstance(v, (int, float)) and p["type"] in ("double", "int"):
            lo, hi = p.get("min"), p.get("max")
            if lo is not None and hi is not None and not (lo <= v <= hi):
                out.out_of_range.append((name, v, lo, hi))
    out.missing = sorted(n for n, p in catalog.params.items()
                         if n not in seen and p["type"] != "undefined")

    if kind == "refloat":
        sig = out.values.get("config_name")
        if sig is not None and sig != "RefloatConfig":
            raise ConfigError(f"refloat: config_name is {sig!r}, expected 'RefloatConfig' "
                              f"(is this another package's config?)")
    return out


def parse_file(path, kind: str) -> ParsedConfig:
    with open(path, "rb") as f:
        return parse_bytes(f.read(), kind)
