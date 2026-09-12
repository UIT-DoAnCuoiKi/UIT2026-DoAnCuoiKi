import subprocess
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1]


def test_check_uses_50_100_bounds_not_35():
    src = (REPORT / "check.py").read_text(encoding="utf-8")
    assert "35" not in src.split("PAGE")[1][:80]  # old cap gone near PAGE config
    assert "PAGE_FLOOR = 50" in src
    assert "PAGE_CAP = 100" in src


def test_check_has_langid_gate():
    src = (REPORT / "check.py").read_text(encoding="utf-8")
    assert "langid" in src
