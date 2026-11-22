"""Command line: vfa audit | compare | rules.

The analyzer only reads files. It never connects to a controller and never
writes a configuration.
"""
from __future__ import annotations

import argparse
import sys

from . import bundle as bundle_mod
from . import compare, derived, engine, report


def _load(path):
    b = bundle_mod.load(path)
    ns = derived.build(b)
    return b, ns, engine.run(ns)


def _emit(text, out):
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="vfa", description="Audit VESC/Refloat board configurations.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="audit one bundle (directory or zip)")
    a.add_argument("bundle")
    a.add_argument("-o", "--output")
    a.add_argument("--fail-on", choices=("critical", "warning", "never"), default="never",
                   help="exit 3 if a finding of this severity or worse fired")
    c = sub.add_parser("compare", help="compare two bundles")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("-o", "--output")
    sub.add_parser("rules", help="list the rule set")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "audit":
            b, ns, res = _load(args.bundle)
            _emit(report.render(b, ns, res), args.output)
            levels = {"critical": ("critical",), "warning": ("critical", "warning"), "never": ()}
            if any(r.fired and r.rule.severity in levels[args.fail_on] for r in res):
                return 3
            return 0
        if args.cmd == "compare":
            A, B = _load(args.a), _load(args.b)
            _emit(compare.render(*A, *B), args.output)
            return 0
        if args.cmd == "rules":
            for r in engine.load_rules():
                print(f"{r.id:9s} {r.severity:8s} [{r.evidence:10s}] {r.title}")
            return 0
    except (bundle_mod.BundleError, engine.RuleError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
