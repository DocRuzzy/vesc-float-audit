import pytest

from vfa import expr


NS = {"mc.l_current_max": 120.0, "rf.atr.filter.time_constant": 0.3, "meta.bms": "charge-only",
      "x.none": None, "v": "1.3.1"}


def test_arithmetic_and_dotted_names():
    assert expr.evaluate("mc.l_current_max * 2 + 1", NS) == 241
    assert expr.evaluate("rf.atr.filter.time_constant < 0.5", NS) is True
    assert expr.evaluate("meta.bms in ('charge-only', 'none')", NS) is True
    assert expr.evaluate("1 < mc.l_current_max < 200", NS) is True


def test_missing_and_none_raise_missing():
    with pytest.raises(expr.Missing) as e:
        expr.evaluate("mc.nope > 1", NS)
    assert e.value.name == "mc.nope"
    with pytest.raises(expr.Missing):
        expr.evaluate("x.none > 1", NS)


def test_has_get_and_short_circuit():
    assert expr.evaluate("has(mc.l_current_max)", NS) is True
    assert expr.evaluate("has(x.none)", NS) is False
    assert expr.evaluate("has(mc.nope) and mc.nope > 1", NS) is False
    assert expr.evaluate("get(mc.nope, 5) + 1", NS) == 6
    assert expr.evaluate("version(v) >= (1, 3, 1)", NS) is True


@pytest.mark.parametrize("bad", [
    "__import__('os')", "mc.l_current_max.__class__", "[x for x in (1,2)]",
    "(lambda: 1)()", "NS['a']", "open('f')", "mc.l_current_max.real()",
])
def test_disallowed_syntax(bad):
    with pytest.raises((expr.ExprError, SyntaxError)):
        expr.parse(bad)


def test_names_and_render():
    assert expr.names("has(a.b) and c.d > max(1, e.f)") == {"a.b", "c.d", "e.f"}
    assert expr.render("{mc.l_current_max:.0f} A, {missing.key}", NS) == "120 A, <missing.key: n/a>"
