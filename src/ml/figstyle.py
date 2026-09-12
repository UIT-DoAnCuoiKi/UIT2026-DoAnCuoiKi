"""Cấu hình matplotlib dùng chung cho mọi figure đưa vào báo cáo.

Báo cáo dùng Times New Roman 13pt (xem report/preamble.tex), nên figure phải
dùng cùng họ font, nếu không chữ trong hình lệch hẳn chữ trong prose.

Mỗi figure xuất hai định dạng vào report/figures/:
  - .pdf  vector, XeLaTeX bắt file này khi \\includegraphics viết không đuôi
  - .png  300dpi, pandoc bắt file này khi nhúng vào .docx
"""
from pathlib import Path

import matplotlib as mpl

FIG_DIR = Path(__file__).resolve().parents[2] / "report" / "figures"


def apply_report_style() -> None:
    """Đặt font và cỡ chữ khớp báo cáo. Gọi một lần trước khi vẽ."""
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.dpi": 110,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    })


def save_report_figure(fig, name: str) -> list[Path]:
    """Ghi fig ra report/figures/<name>.pdf và <name>.png. Trả danh sách file."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for ext, dpi in ((".pdf", None), (".png", 300)):
        p = FIG_DIR / f"{name}{ext}"
        fig.savefig(p, dpi=dpi) if dpi else fig.savefig(p)
        out.append(p)
    return out
