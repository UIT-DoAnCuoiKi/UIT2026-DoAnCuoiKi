import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tới src/ml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from figstyle import FIG_DIR, apply_report_style, save_report_figure


def test_apply_report_style_sets_serif():
    apply_report_style()
    assert matplotlib.rcParams["font.family"] == ["serif"]
    assert "Times New Roman" in matplotlib.rcParams["font.serif"]


def test_save_report_figure_writes_both_formats():
    apply_report_style()
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    paths = save_report_figure(fig, "_smoke_test")
    plt.close(fig)
    assert len(paths) == 2
    assert {p.suffix for p in paths} == {".pdf", ".png"}
    for p in paths:
        assert p.exists() and p.stat().st_size > 0
        p.unlink()
