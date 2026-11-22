"""Safe evaluator for the small expression language used in rule files.

Rules are data, so their conditions are strings. They are parsed with `ast`
and only a whitelist of node types is evaluated: literals, dotted names,
arithmetic, comparisons, boolean logic, conditional expressions, list/tuple
literals and calls to a few pure functions. Nothing else (attribute access
on objects, subscripts, lambdas, comprehensions, imports) is accepted.

Dotted names such as ``mc.l_current_max`` or ``rf.atr.filter.time_constant``
are looked up as whole strings in a flat namespace. A name that is absent, or
present with value ``None``, raises :class:`Missing`; the rule engine turns
that into a "not evaluated" result instead of a pass.
"""
from __future__ import annotations

import ast
import operator
import re
from functools import lru_cache
from typing import Any, Mapping


class Missing(Exception):
    """A name used by the expression has no value."""

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class ExprError(ValueError):
    """The expression uses syntax outside the whitelist."""


_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_CMPOPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}


def _dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        raise ExprError("only dotted names may use '.'")
    parts.append(node.id)
    return ".".join(reversed(parts))


@lru_cache(maxsize=None)
def parse(expr: str) -> ast.Expression:
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
                raise ExprError(f"call not allowed in {expr!r}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ExprError(f"names starting with '_' not allowed in {expr!r}")
        elif isinstance(node, ast.Name) and node.id.startswith("_"):
            raise ExprError(f"names starting with '_' not allowed in {expr!r}")
        elif not isinstance(node, _ALLOWED_NODES):
            raise ExprError(f"{type(node).__name__} not allowed in {expr!r}")
    return tree


def names(expr: str) -> set[str]:
    """Dotted names an expression reads (excluding function names)."""
    out: set[str] = set()

    def visit(node):
        if isinstance(node, (ast.Attribute, ast.Name)):
            n = _dotted(node)
            if n not in FUNCTIONS and n not in _CONSTANTS:
                out.add(n)
            return
        if isinstance(node, ast.Call):
            for a in node.args:
                visit(a)
            return
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(parse(expr).body)
    return out


def evaluate(expr: str, ns: Mapping[str, Any]) -> Any:
    return _eval(parse(expr).body, ns)


def _lookup(name: str, ns: Mapping[str, Any]):
    if name in _CONSTANTS:
        return _CONSTANTS[name]
    if name not in ns or ns[name] is None:
        raise Missing(name)
    return ns[name]


def _eval(node: ast.AST, ns: Mapping[str, Any]):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Name, ast.Attribute)):
        return _lookup(_dotted(node), ns)
    if isinstance(node, ast.BinOp):
        return _BINOPS[type(node.op)](_eval(node.left, ns), _eval(node.right, ns))
    if isinstance(node, ast.UnaryOp):
        return _UNARY[type(node.op)](_eval(node.operand, ns))
    if isinstance(node, ast.BoolOp):
        # Short-circuit, so `has(x) and x > 1` works when x is missing.
        if isinstance(node.op, ast.And):
            result = True
            for v in node.values:
                result = _eval(v, ns)
                if not result:
                    return result
            return result
        result = False
        for v in node.values:
            result = _eval(v, ns)
            if result:
                return result
        return result
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ns)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, ns)
            if not _CMPOPS[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return _eval(node.body, ns) if _eval(node.test, ns) else _eval(node.orelse, ns)
    if isinstance(node, (ast.List, ast.Tuple)):
        return tuple(_eval(e, ns) for e in node.elts)
    if isinstance(node, ast.Call):
        fn = node.func.id
        if fn == "has":
            # has("a.b") or has(a.b): true when the name has a value.
            arg = node.args[0]
            name = arg.value if isinstance(arg, ast.Constant) else _dotted(arg)
            return name in ns and ns[name] is not None
        if fn == "get":
            # get(a.b, default)
            name = _dotted(node.args[0])
            v = ns.get(name)
            return _eval(node.args[1], ns) if v is None else v
        return FUNCTIONS[fn](*[_eval(a, ns) for a in node.args])
    raise ExprError(f"cannot evaluate {type(node).__name__}")


def _version_tuple(v) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", str(v)))


FUNCTIONS = {
    "abs": abs, "min": min, "max": max, "round": round,
    "has": None, "get": None,
    "version": _version_tuple,
}
_CONSTANTS = {"true": True, "false": False, "none": None}
_ALLOWED_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Attribute, ast.Load,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.List, ast.Tuple, ast.Call,
    *(_BINOPS.keys()), *(_CMPOPS.keys()), *(_UNARY.keys()), ast.And, ast.Or,
)


_FIELD = re.compile(r"\{([A-Za-z_][\w.]*)(?::([^}]*))?\}")


def render(template: str, ns: Mapping[str, Any]) -> str:
    """Fill ``{name}`` / ``{name:.1f}`` placeholders from the namespace."""

    def sub(m):
        name, fmt = m.group(1), m.group(2)
        if name not in ns or ns[name] is None:
            return f"<{name}: n/a>"
        v = ns[name]
        try:
            return format(v, fmt) if fmt else _plain(v)
        except (TypeError, ValueError):
            return str(v)

    return _FIELD.sub(sub, template)


def _plain(v) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)
