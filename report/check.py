#!/usr/bin/env python3
"""Cổng kiểm tra báo cáo. Chạy: python3 report/check.py

Dùng Python chứ không dùng grep: grep trên macOS không bắt được ký tự đa byte
như gạch dài U+2013 và U+2014 hay chữ tiếng Việt có dấu, nên cổng viết bằng
grep sẽ pass giả. Đã kiểm chứng ngày 09/09/2026 trên chính repo này: 8 dòng
chứa U+2014 mà grep bracket, grep -e, LC_ALL=en_US.UTF-8 grep và grep -P đều
trả về 0.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent).resolve()
SRC_DIRS = ["chapters", "frontmatter", "appendices"]
DASHES = "\u2013\u2014"
# LaTeX ligature: "--" ra gạch ngắn, "---" ra gạch dài. Pandoc sinh dạng này
# khi chuyển từ Markdown, nên phải bắt cả hai chứ không chỉ ký tự Unicode.
DASH_LIGATURE = re.compile(r"(?<!-)--(?!-)|---")
FIRST_PERSON = re.compile(r"chúng\s+(em|tôi|ta)|nhóm\s+em", re.IGNORECASE)
PLACEHOLDER = re.compile(r"\\(wip|ph)\{")
LABEL = re.compile(r"\\label\{((?:fig|tab):[^}]+)\}")
PAGE_FLOOR = 50
PAGE_CAP = 100
failures = []


def tex_files():
    for d in SRC_DIRS:
        yield from sorted((ROOT / d).glob("*.tex"))


def prose_lines():
    """Sinh (file, số dòng, nội dung) cho các dòng KHÔNG phải comment LaTeX."""
    for f in tex_files():
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("%"):
                continue
            yield f, i, line


def report(name, hits, note=""):
    if hits:
        failures.append(name)
        print(f"{name:<28} FAIL ({len(hits)}) {note}")
        for h in hits[:5]:
            print(f"    {h}")
        if len(hits) > 5:
            print(f"    ... còn {len(hits) - 5} chỗ nữa")
    else:
        print(f"{name:<28} OK {note}")


def loc(f, i, line):
    return f"{f.relative_to(ROOT)}:{i}: {line.strip()[:80]}"


report("R1 placeholder wip/ph",
       [loc(f, i, l) for f, i, l in prose_lines() if PLACEHOLDER.search(l)])

report("R9 en/em dash (unicode)",
       [loc(f, i, l) for f, i, l in prose_lines() if any(c in l for c in DASHES)])

report("R9 dash ligature (-- ---)",
       [loc(f, i, l) for f, i, l in prose_lines() if DASH_LIGATURE.search(l)])

report("R5 ngoi thu nhat",
       [loc(f, i, l) for f, i, l in prose_lines() if FIRST_PERSON.search(l)])

body = "\n".join(f.read_text(encoding="utf-8") for f in tex_files())
unref = [lb for lb in sorted(set(LABEL.findall(body)))
         if f"ref{{{lb}}}" not in body]
report("Nhan chua duoc nhac", unref)

REFS = ROOT / "refs.bib"
if REFS.exists():
    bib = REFS.read_text(encoding="utf-8")
    entries = re.findall(r"@\w+\{([^,]+),(.*?)(?=\n@|\Z)", bib, re.DOTALL)
    no_lang = [k for k, b in entries
               if not re.search(r"langid\s*=\s*\{(vietnamese|english)\}", b)]
    report("refs.bib thieu langid", no_lang)

CAPTION = re.compile(r"\\caption\{")
cap_no_src = []
for f in tex_files():
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if CAPTION.search(line):
            window = "\n".join(lines[max(0, i - 3):i + 4])
            # Mọi caption phải có dòng nguồn. KHÔNG bỏ qua khi có \label: gần như
            # hình/bảng nào cũng có \label, nếu bỏ qua thì cổng nguồn vô dụng.
            if "Nguồn:" not in window:
                cap_no_src.append(loc(f, i + 1, line))
report("Caption thieu nguon", cap_no_src)

log = ROOT / "main.log"
if log.exists():
    text = log.read_text(encoding="utf-8", errors="replace")
    report("R8 undefined citation",
           re.findall(r"Citation '([^']+)' .*undefined", text))
    report("R8 undefined reference",
           re.findall(r"Reference '([^']+)' .*undefined", text))
else:
    print(f"{'R8 (chua co main.log)':<28} SKIP")

pdf = ROOT / "main.pdf"
if pdf.exists():
    out = subprocess.run(["mdls", "-raw", "-name", "kMDItemNumberOfPages", str(pdf)],
                         capture_output=True, text=True).stdout.strip()
    pages = int(out) if out.isdigit() else len(
        re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
    # `pages` là TỔNG trang toàn quyển (kể cả bìa, front matter, TLTK, phụ lục).
    # Sàn 50 trần 100 là cho THÂN BÀI. Vì tổng >= thân bài, chỉ khẳng định được
    # lỗi khi tổng < sàn (thân bài chắc chắn dưới sàn). Trần thân bài không suy
    # ra được từ tổng nên chỉ báo tin, soát tay theo mục 12 của spec.
    if pages < PAGE_FLOOR:
        failures.append("R4 so trang")
        print(f"{'R4 so trang':<28} FAIL ({pages} tong < san {PAGE_FLOOR}; "
              f"than bai duoi san)")
    else:
        print(f"{'R4 so trang':<28} INFO ({pages} tong; than bai phai "
              f"{PAGE_FLOOR}..{PAGE_CAP}, soat tay muc 12)")
else:
    print(f"{'R4 (chua co main.pdf)':<28} SKIP")

# Tên chương IN HOA: KHÔNG kiểm ở nguồn. Nguồn .tex để chữ thường có chủ đích;
# viết hoa tự động khi render (titleformat \MakeUppercase cho PDF, hàm
# uppercase_chapter_titles cho DOCX). Kiểm bằng mắt trên main.docx, không cổng nguồn.
print(f"{'Ten chuong IN HOA':<28} INFO (render-time: titleformat + postprocess)")

print()
if failures:
    print(f"HONG {len(failures)} cong: {', '.join(failures)}")
    sys.exit(1)
print("Moi cong OK")
