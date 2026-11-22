"""Hardware, cell and motor profiles (YAML under vfa/data/profiles).

Profile values are written as ``{value, evidence, source}``. They are
flattened into dotted keys, e.g. ``hw.fw_limits.abs_current``, with the
evidence and source kept alongside so a finding can say what it rests on.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

import yaml


@dataclass
class Profile:
    kind: str
    id: str
    name: str
    raw: dict
    values: dict      # dotted key -> value
    evidence: dict    # dotted key -> evidence label
    sources: dict     # dotted key -> source string


def _is_leaf(v) -> bool:
    return isinstance(v, dict) and "value" in v


def _flatten(d: dict, prefix: str, values, evidence, sources):
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if _is_leaf(v):
            values[key] = v["value"]
            evidence[key] = v.get("evidence", "UNVERIFIED")
            sources[key] = v.get("source", "")
        elif isinstance(v, dict):
            _flatten(v, key, values, evidence, sources)
        else:
            values[key] = v
            evidence[key] = "n/a"
            sources[key] = ""


@lru_cache(maxsize=None)
def load(kind: str, pid: str) -> Profile:
    folder = {"hardware": "hardware", "cell": "cells", "motor": "motors"}[kind]
    path = resources.files("vfa.data.profiles").joinpath(folder, f"{pid}.yaml")
    if not path.is_file():
        raise KeyError(f"no {kind} profile '{pid}' (available: {', '.join(available(kind))})")
    raw = yaml.safe_load(path.read_text())
    values, evidence, sources = {}, {}, {}
    _flatten(raw, "", values, evidence, sources)
    return Profile(kind, raw["id"], raw.get("name", pid), raw, values, evidence, sources)


def available(kind: str) -> list[str]:
    folder = {"hardware": "hardware", "cell": "cells", "motor": "motors"}[kind]
    d = resources.files("vfa.data.profiles").joinpath(folder)
    return sorted(p.name[:-5] for p in d.iterdir() if p.name.endswith(".yaml"))


def default_overrides(hw: Profile) -> dict:
    """mcconf parameter -> (value, source) compiled in for this hardware."""
    out = {}
    for name, v in (hw.raw.get("default_overrides") or {}).items():
        out[name] = (v["value"], v.get("source", ""))
    return out
