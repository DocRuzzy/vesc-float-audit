import json

from vfa import cli
import builder


def test_audit_writes_report(tmp_path, capsys):
    d = builder.board_a(tmp_path / "a")
    out = tmp_path / "a.md"
    assert cli.main(["audit", str(d), "-o", str(out)]) == 0
    assert out.read_text().startswith("# Configuration audit")


def test_fail_on_critical(tmp_path):
    d = builder.board_a(tmp_path / "a", rf={"tiltback_hv": 200.0})
    assert cli.main(["audit", str(d), "-o", str(tmp_path / "x.md"), "--fail-on", "critical"]) == 3


def test_bad_bundle_exit_1(tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    assert cli.main(["audit", str(tmp_path / "empty")]) == 1
    assert "missing" in capsys.readouterr().err


def test_compare_and_rules(tmp_path, capsys):
    a, b = builder.board_a(tmp_path / "a"), builder.board_b(tmp_path / "b")
    assert cli.main(["compare", str(a), str(b), "-o", str(tmp_path / "c.md")]) == 0
    assert cli.main(["rules"]) == 0
    assert "BAT-001" in capsys.readouterr().out
