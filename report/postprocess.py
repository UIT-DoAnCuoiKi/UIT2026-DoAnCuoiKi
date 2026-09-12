#!/usr/bin/env python3
"""Biến body.docx (pandoc) thành main.docx khớp BieuMau.

Chạy sau pandoc trong build.sh. Dựng front matter động, cắt section và đánh
số trang, chèn field danh mục, tách thư mục Việt/Anh, ép tên chương IN HOA.
Xem docs/superpowers/specs/2026-09-10-hinh-thuc-docx-design.md.
"""
import re
import sys
from pathlib import Path

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent


def read_thesis_meta(main_tex: Path) -> dict:
    """Đọc các \\newcommand thông tin đề tài trong main.tex (nguồn duy nhất)."""
    text = Path(main_tex).read_text(encoding="utf-8")

    def cmd(name: str) -> str:
        m = re.search(r"\\newcommand\{\\" + name + r"\}\{(.+?)\}\s*(?:%|$)",
                      text, re.MULTILINE)
        if not m:
            raise ValueError(f"missing \\newcommand{{\\{name}}} in {main_tex}")
        # Bỏ ligature "--" của LaTeX trong giá trị năm học.
        return m.group(1).replace("--", "-").strip()

    return {
        "title_vi": cmd("ThesisTitleVi"),
        "title_en": cmd("ThesisTitleEn"),
        "supervisor": cmd("Supervisor"),
        "student_a": cmd("StudentA"),
        "student_a_id": cmd("StudentAId"),
        "student_b": cmd("StudentB"),
        "student_b_id": cmd("StudentBId"),
        "year": cmd("AcademicYear"),
        "defense": cmd("DefenseDate"),
    }


def add_field(paragraph, instruction: str) -> None:
    """Chèn một Word simple field (TOC/PAGE/SEQ...) vào cuối paragraph.

    Word cập nhật khi mở (hoặc Ctrl+A, F9). Dùng fldSimple cho gọn.
    """
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instruction)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = ""
    r.append(t)
    fld.append(r)
    paragraph._p.append(fld)


from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_BREAK


def _centered(doc, text, bold=False, upper=False, size=None):
    from docx.shared import Pt
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text.upper() if upper else text)
    r.bold = bold
    if size:
        r.font.size = Pt(size)
    return p


def _page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def build_cover(doc, meta: dict, with_supervisor: bool) -> None:
    """Bìa chính (with_supervisor=False) hoặc bìa phụ (True, có GVHD)."""
    _centered(doc, "ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH", bold=True)
    _centered(doc, "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN", bold=True)
    _centered(doc, "")
    _centered(doc, f"{meta['student_a']} - {meta['student_a_id']}", bold=True)
    _centered(doc, f"{meta['student_b']} - {meta['student_b_id']}", bold=True)
    _centered(doc, "")
    _centered(doc, "ĐỒ ÁN TỐT NGHIỆP", bold=True, size=16)
    _centered(doc, meta["title_vi"], bold=True, upper=True, size=15)
    _centered(doc, meta["title_en"], bold=False)
    _centered(doc, "")
    _centered(doc, "CỬ NHÂN NGÀNH KỸ THUẬT MÁY TÍNH", bold=True)
    if with_supervisor:
        _centered(doc, "")
        _centered(doc, "GIẢNG VIÊN HƯỚNG DẪN", bold=True)
        _centered(doc, meta["supervisor"], bold=True)
    _centered(doc, "")
    _centered(doc, f"THÀNH PHỐ HỒ CHÍ MINH, {meta['year']}", bold=True)
    _page_break(doc)


def build_council_page(doc) -> None:
    _centered(doc, "THÔNG TIN HỘI ĐỒNG CHẤM ĐỒ ÁN TỐT NGHIỆP", bold=True)
    doc.add_paragraph(
        "Hội đồng chấm Đồ án tốt nghiệp, thành lập theo Quyết định số "
        "........................ ngày ....................... của Hiệu trưởng "
        "Trường Đại học Công nghệ Thông tin."
    )
    _page_break(doc)


def build_acknowledgement(doc, text: str) -> None:
    _centered(doc, "LỜI CẢM ƠN", bold=True)
    doc.add_paragraph(text)
    _page_break(doc)


def _heading_caps(doc, text):
    p = doc.add_paragraph()
    p.style = doc.styles["Heading 1"]
    p.add_run(text.upper()).bold = True
    return p


def build_toc_lists(doc) -> None:
    """MỤC LỤC + DANH MỤC HÌNH/BẢNG (Word field) + DANH MỤC TỪ VIẾT TẮT."""
    _heading_caps(doc, "Mục lục")
    add_field(doc.add_paragraph(), 'TOC \\o "1-4" \\h \\z \\u')
    _page_break(doc)

    _heading_caps(doc, "Danh mục hình")
    add_field(doc.add_paragraph(), 'TOC \\h \\z \\c "Hình"')
    _page_break(doc)

    _heading_caps(doc, "Danh mục bảng")
    add_field(doc.add_paragraph(), 'TOC \\h \\z \\c "Bảng"')
    _page_break(doc)

    _heading_caps(doc, "Danh mục từ viết tắt")
    lines = (HERE / "frontmatter" / "vietat.txt").read_text(
        encoding="utf-8").splitlines()
    for line in sorted(l for l in lines if l.strip()):
        doc.add_paragraph(line.strip())
    _page_break(doc)


def _para_index_of_heading(doc, needle: str) -> int:
    for i, p in enumerate(doc.paragraphs):
        if needle.lower() in p.text.lower() and p.style.name.startswith("Heading"):
            return i
    return -1


def find_abstract_index(doc) -> int:
    return _para_index_of_heading(doc, "Tóm tắt")


def strip_before_abstract(doc) -> None:
    """Xóa mọi phần tử body đứng trước heading Tóm tắt (rác front matter pandoc)."""
    idx = find_abstract_index(doc)
    if idx < 0:
        raise ValueError("khong tim thay heading 'Tóm tắt' trong body.docx")
    target = doc.paragraphs[idx]._p
    body = doc.element.body
    for child in list(body):
        if child is target:
            break
        if child.tag.endswith("}sectPr"):
            continue
        body.remove(child)


from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH as _AL


def _insert_section_break_before(doc, paragraph):
    """Chèn một section break (NEW_PAGE) ngay trước paragraph.

    Cách làm: thêm section mới ở cuối doc để lấy sectPr, rồi chuyển sectPr đó
    vào một đoạn trống đặt trước paragraph. python-docx add_section gắn sectPr
    cuối body, nên ta di chuyển nó lên.
    """
    new_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    sectPr = new_sec._sectPr
    sep_p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    # sectPr của section TRƯỚC nằm trong pPr của đoạn cuối section đó.
    pPr.append(sectPr)
    sep_p.append(pPr)
    paragraph._p.addprevious(sep_p)
    return new_sec


def set_page_numbering(doc, abstract_para) -> None:
    """Front matter không số; từ abstract_para trở đi số Ả Rập, bắt đầu 1, giữa dưới."""
    _insert_section_break_before(doc, abstract_para)
    body_sec = doc.sections[-1]

    # pgNumType start=1 trên sectPr cuối (section thân bài).
    sectPr = body_sec._sectPr
    pgNum = sectPr.find(qn("w:pgNumType"))
    if pgNum is None:
        pgNum = OxmlElement("w:pgNumType")
        sectPr.append(pgNum)
    pgNum.set(qn("w:start"), "1")

    # Footer thân bài: PAGE field canh giữa. Ngắt liên kết với section trước.
    body_sec.footer.is_linked_to_previous = False
    fp = body_sec.footer.paragraphs[0]
    fp.alignment = _AL.CENTER
    add_field(fp, "PAGE")

    # Front matter section: footer trống, không số.
    front_sec = doc.sections[0]
    front_sec.footer.is_linked_to_previous = False
    for p in list(front_sec.footer.paragraphs):
        p.clear()


def _insert_heading_before(ref_para, text: str, style) -> None:
    """Chèn một đoạn Heading 1 chứa `text` ngay trước ref_para (đoạn tham khảo)."""
    h = OxmlElement("w:p")
    ref_para._p.addprevious(h)
    hp = docx.text.paragraph.Paragraph(h, ref_para._parent)
    hp.style = style
    hp.add_run(text).bold = True


LANG_MARKER = re.compile(r"^\s*\{\{lang:([^}]*)\}\}\s*")


def _strip_lang_marker(para) -> str:
    """Xóa marker {{lang:xx-YY}} ở đầu đoạn tham khảo, trả về mã ngôn ngữ.

    ieee-vi-en.csl in mã ngôn ngữ (từ trường langid) ở đầu mỗi mục để ta phân
    nhóm. citeproc đã đánh số [n] theo thứ tự (tiếng Việt trước, rồi tên tác
    giả) nên trích dẫn trong bài tự khớp; ở đây chỉ bóc marker và chia nhóm.
    """
    full = "".join(r.text for r in para.runs)
    m = LANG_MARKER.match(full)
    if not m:
        return ""
    lang = m.group(1)
    marker = m.group(0)
    # Bóc `marker` khỏi các run đầu (marker luôn nằm ở đầu đoạn).
    remaining = marker
    for r in para.runs:
        if not remaining:
            break
        if len(r.text) <= len(remaining):
            remaining = remaining[len(r.text):]
            r.text = ""
        else:
            r.text = r.text[len(remaining):]
            remaining = ""
    return lang


def split_bibliography(doc) -> None:
    """Bóc marker ngôn ngữ, chia danh sách tham khảo thành hai nhóm Việt/Anh.

    pandoc bỏ heading \\printbibliography của biblatex và nối danh sách tham
    khảo vào cuối tài liệu không kèm heading. ieee-vi-en.csl đã xếp mục tiếng
    Việt trước, tiếng Anh sau (mỗi mục mở đầu bằng {{lang:...}}) và đánh số [n]
    liên tục theo đúng thứ tự đó. Ta bóc marker rồi chèn hai heading Heading 1
    tại ranh giới Việt/Anh. Số trích dẫn trong bài do citeproc giữ khớp.
    """
    refs = [p for p in doc.paragraphs if LANG_MARKER.match(
        "".join(r.text for r in p.runs))]
    if not refs:
        return
    langs = [_strip_lang_marker(p) for p in refs]
    heading = doc.styles["Heading 1"]
    # Ranh giới: mục tiếng Anh đầu tiên (mã ngôn ngữ không bắt đầu bằng "vi").
    n_vi = sum(1 for lang in langs if lang.lower().startswith("vi"))
    _insert_heading_before(refs[0], "Tài liệu tiếng Việt", heading)
    if 0 <= n_vi < len(refs):
        _insert_heading_before(refs[n_vi], "Tài liệu tiếng Anh", heading)


def uppercase_chapter_titles(doc) -> None:
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and "tóm tắt" not in p.text.lower():
            for r in p.runs:
                r.text = r.text.upper()


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]
    body_docx, main_tex, out_docx = argv[0], argv[1], argv[2]

    doc = docx.Document(body_docx)
    meta = read_thesis_meta(Path(main_tex))
    ack = (HERE / "frontmatter" / "loicamon.txt").read_text(encoding="utf-8")

    strip_before_abstract(doc)
    uppercase_chapter_titles(doc)
    split_bibliography(doc)

    # Dựng front matter vào một doc mới rồi ghép body vào sau.
    front = docx.Document(str(HERE / "reference.docx"))
    # reference.docx có 1 đoạn trống; xóa để bắt đầu sạch.
    for p in list(front.paragraphs):
        p._p.getparent().remove(p._p)
    build_cover(front, meta, with_supervisor=False)
    build_cover(front, meta, with_supervisor=True)
    build_council_page(front)
    build_acknowledgement(front, ack)
    build_toc_lists(front)

    # Ghép mọi phần tử body (đã strip) vào cuối front.
    for child in list(doc.element.body):
        if child.tag.endswith("}sectPr"):
            continue
        front.element.body.append(child)

    abstract = next(p for p in front.paragraphs if "tóm tắt" in p.text.lower()
                    and p.style.name.startswith("Heading"))
    set_page_numbering(front, abstract)
    front.save(out_docx)
    print(f"wrote {out_docx}")


if __name__ == "__main__":
    main()
