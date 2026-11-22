"""Parameter catalogs generated from pinned upstream sources.

See tools/gen_catalog.py for how they are built and which commits they come
from. Each catalog maps a parameter name to its metadata and default.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

KINDS = {
    "mcconf": ("mcconf_7.00.json", "MCConfiguration"),
    "appconf": ("appconf_7.00.json", "APPConfiguration"),
    "refloat": ("refloat_1.3.1.json", "CustomConfiguration"),
}

# What the catalogs are pinned to. A bundle that reports other versions is
# still parsed, but the report says the names and defaults may not match.
PINNED_FIRMWARE = "7.00"
PINNED_REFLOAT = "1.3.1"


@dataclass(frozen=True)
class Catalog:
    kind: str
    xml_root: str
    params: dict
    provenance: dict

    def __contains__(self, name: str) -> bool:
        return name in self.params

    def get(self, name: str) -> dict | None:
        return self.params.get(name)

    def default(self, name: str):
        p = self.params.get(name)
        return None if p is None else p.get("default")

    def describe_value(self, name: str, value) -> str:
        """Human form of a raw value: enum name, or value in display units."""
        p = self.params.get(name)
        if p is None or value is None:
            return "—" if value is None else str(value)
        if p["type"] == "enum":
            names = p.get("enum_names") or []
            if isinstance(value, int) and 0 <= value < len(names):
                return f"{names[value]} ({value})"
            return str(value)
        if p["type"] == "bool":
            return "true" if value else "false"
        if p["type"] in ("double", "int"):
            scale = p.get("editor_scale") or 1
            suffix = p.get("suffix") or ""
            shown = value * scale
            if suffix == "%" or (scale == 100 and not suffix):
                suffix = "%"
            txt = f"{shown:.6g}"
            return f"{txt} {suffix}".strip() if suffix else txt
        return str(value)


@lru_cache(maxsize=None)
def load(kind: str) -> Catalog:
    fname, root = KINDS[kind]
    with resources.files("vfa.data.upstream").joinpath(fname).open() as f:
        doc = json.load(f)
    return Catalog(kind=kind, xml_root=root, params=doc["params"], provenance=doc["provenance"])
