from vfa import bundle, derived, engine
import builder


def audit(tmp_path, board="a", name="b", **kw):
    make = builder.board_a if board == "a" else builder.board_b
    b = bundle.load(make(tmp_path / name, **kw))
    ns = derived.build(b)
    res = {r.rule.id: r for r in engine.run(ns)}
    return b, ns, res


def fired(res):
    return {k for k, r in res.items() if r.fired}
