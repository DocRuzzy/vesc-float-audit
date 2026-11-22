"""The analyzer must never talk to a controller or the network (CLAUDE.md: capture is
read-only; Phase 1 only reads exported files)."""
import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "vfa"
FORBIDDEN = re.compile(r"^\s*(import|from)\s+(serial|socket|bleak|bluetooth|requests|urllib|http|asyncio|subprocess)\b", re.M)


def test_no_device_or_network_io():
    for p in SRC.rglob("*.py"):
        assert not FORBIDDEN.search(p.read_text()), p
