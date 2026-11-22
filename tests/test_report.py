import re

from vfa import compare, engine, report
from helpers import audit


def _render(tmp_path, **kw):
    b, ns, res = audit(tmp_path, **kw)
    return report.render(b, ns, sorted(res.values(), key=lambda r: r.rule.id), today="2026-11-22")


def test_section_order_red_flags_first(tmp_path):
    md = _render(tmp_path, rf={"tiltback_hv": 4.3, "fault_adc1": 0.0, "fault_adc2": 0.0})
    heads = [h for h in re.findall(r"^## (.+)$", md, re.M)]
    assert heads[:3] == ["Summary", "Red flags", "Cross-checks"]
    red = md.split("## Red flags", 1)[1].split("## Cross-checks", 1)[0]
    assert "BAT-012" in red and "FP-001" in red
    assert "**2 red flag(s)**" in md


def test_all_crosschecks_present(tmp_path):
    md = _render(tmp_path)
    for title in engine.CROSSCHECKS.values():
        assert f"### {title}" in md


def test_diff_against_hardware_defaults(tmp_path):
    md = _render(tmp_path)
    diff = md.split("## Diff against defaults", 1)[1]
    # Thor 301 hwconf default battery current is 100 A; the example sets 70 A.
    assert re.search(r"`l_in_current_max` \| Battery Current Max \| 70 A \| 100 A \| thor301 hwconf", diff)
    # Detected motor values go in the collapsed calibration list.
    assert "detection / calibration values" in diff
    calib = diff.split("detection / calibration values", 1)[1].split("</details>", 1)[0]
    assert "`foc_motor_flux_linkage`" in calib


def test_no_reassurance_without_evidence(tmp_path):
    md = _render(tmp_path, board="b")
    assert "## Not evaluated" in md and "BAT-012" in md.split("## Not evaluated", 1)[1]
    assert "No critical rule fired. Check the *not evaluated*" in md
    for phrase in ("is safe", "is fine", "looks good"):
        assert phrase not in md.lower()


def test_flux_table(tmp_path):
    md = _render(tmp_path)
    assert "| `kp` | 20 | 20 |" in md       # value, default, then the 1.2-equivalent


def test_compare(tmp_path):
    a = audit(tmp_path, name="a")
    b = audit(tmp_path, board="b", name="b2")
    ra = sorted(a[2].values(), key=lambda r: r.rule.id)
    rb = sorted(b[2].values(), key=lambda r: r.rule.id)
    md = compare.render(a[0], a[1], ra, b[0], b[1], rb, today="2026-11-22")
    assert "different hardware" in md
    assert re.search(r"`l_in_current_max` \| 70 A \| 38 A", md)
    assert "### Cell rating vs battery current" in md


def test_compare_flags_identical_configs(tmp_path):
    a = audit(tmp_path, name="a1")
    b = audit(tmp_path, name="a2")
    ra = sorted(a[2].values(), key=lambda r: r.rule.id)
    rb = sorted(b[2].values(), key=lambda r: r.rule.id)
    md = compare.render(a[0], a[1], ra, b[0], b[1], rb, today="2026-11-22")
    assert "identical motor configs" in md
