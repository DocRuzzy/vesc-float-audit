#!/usr/bin/env python3
"""Regenerate examples/: two synthetic bundles and their reports.

The bundles are built from catalog defaults plus the example tunes in
tests/builder.py. They are NOT captures from the owner's boards.
Example A keeps Refloat's default HV pushback (4.3 V/cell) to show how that
reads on a 20S pack; example B carries a short synthetic Float Control log.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

import builder  # noqa: E402
from vfa import bundle, compare, derived, engine, report  # noqa: E402

TODAY = "2026-11-22"
FC_LOG = """Time(s),State,Speed(km/h),Duty%,Voltage,I-Battery,I-Motor,I-FldWeak,Pitch,True Pitch,Setpoint,T-Mosfet,T-Mot,ADC1,ADC2,Motor-Fault
0.0,RIDING,5.0,12%,61.8,4.0,10.0,0.0,0.1,0.1,0.0,31.0,30.0,3.05,3.08,0
0.1,RIDING,18.0,55%,58.9,21.0,48.0,0.0,0.4,0.3,0.0,38.0,41.0,3.04,3.06,0
0.2,RIDING,24.0,74%,56.2,36.5,79.0,0.0,1.2,1.0,0.5,44.0,47.0,3.02,3.07,0
0.3,RIDING,26.0,83%,54.1,37.9,92.0,0.0,2.8,2.5,1.1,47.0,50.0,3.01,1.62,0
0.4,RIDING,22.0,70%,57.5,18.0,40.0,0.0,0.9,0.8,0.4,46.0,50.0,3.03,3.05,0
"""


def main():
    out = ROOT / "examples"
    if out.exists():
        shutil.rmtree(out)
    a = builder.board_a(out / "synthetic-board-a", rf={"tiltback_hv": 4.3})
    b = builder.board_b(out / "synthetic-board-b", logs={"logs/ride.csv": FC_LOG})
    (out / "reports").mkdir()
    loaded = []
    for path, name in ((a, "synthetic-board-a.md"), (b, "synthetic-board-b.md")):
        bd = bundle.load(path)
        bd.path = str(path.relative_to(ROOT))
        ns = derived.build(bd)
        res = engine.run(ns)
        (out / "reports" / name).write_text(report.render(bd, ns, res, today=TODAY))
        loaded.append((bd, ns, res))
    (out / "reports" / "compare-a-b.md").write_text(compare.render(*loaded[0], *loaded[1], today=TODAY))
    (out / "README.md").write_text(
        "# Examples\n\nSynthetic bundles built by `tools/make_examples.py` from upstream defaults "
        "and example tunes. **They are not captures from the owner's boards** and nothing in "
        "them has been validated on hardware.\n\n"
        "- `synthetic-board-a/`: Thor 301, 20S2P, with Refloat's default HV pushback "
        "(4.3 V/cell = 86 V)\n"
        "- `synthetic-board-b/`: Ubox Single 100V, 15S1P, with a 5-sample synthetic Float Control log\n"
        "- `reports/`: the audit of each bundle and their comparison\n")
    print("examples regenerated")


if __name__ == "__main__":
    main()
