#!/usr/bin/env python3
"""Biến body.docx (pandoc) thành main.docx khớp BieuMau.

Chạy sau pandoc trong build.sh. Dựng front matter động, cắt section và đánh
số trang, chèn field danh mục, tách thư mục Việt/Anh, ép tên chương IN HOA.
Xem docs/superpowers/specs/2026-09-10-hinh-thuc-docx-design.md.
"""
import copy
import re
import sys
from pathlib import Path

import docx
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

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
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER


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
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Hai dòng cuối (địa điểm + ký tên) canh phải theo lệ trình bày; phần còn lại
    # là các đoạn thân canh đều. Mỗi dòng trong loicamon.txt là một đoạn.
    body_lines = lines[:-2] if len(lines) > 2 else lines
    tail_lines = lines[-2:] if len(lines) > 2 else []
    for line in body_lines:
        doc.add_paragraph(line).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for line in tail_lines:
        doc.add_paragraph(line).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _page_break(doc)


def _heading_caps(doc, text, page_break_before=False):
    p = doc.add_paragraph()
    p.style = doc.styles["Heading 1"]
    if page_break_before:
        # pageBreakBefore mở đầu mỗi danh mục ở trang mới mà KHÔNG sinh trang trắng:
        # nếu nội dung trước vừa hết trang, Word/LibreOffice bỏ qua ngắt ở đầu trang;
        # nếu còn dở trang thì sang trang mới. Hơn hẳn page break cứng ở cuối khối
        # (page break cứng luôn tạo trang mới, kể cả khi khối trước lấp vừa đủ trang
        # -> trang trắng, đúng lỗi từng thấy giữa MỤC LỤC và DANH MỤC HÌNH).
        p.paragraph_format.page_break_before = True
    p.add_run(text.upper()).bold = True
    return p


def _read_abbreviations() -> list:
    """Đọc cặp (từ viết tắt, giải nghĩa) từ frontmatter/vietat.tex.

    vietat.tex là nguồn DUY NHẤT của danh mục từ viết tắt (bản đầy đủ 29 mục);
    trước đây front matter dùng vietat.txt cắt ngắn nên thiếu mục. Mỗi dòng dạng
    "\\textbf{TERM} & Định nghĩa \\\\". Trả về danh sách đã xếp alphabet."""
    text = (HERE / "frontmatter" / "vietat.tex").read_text(encoding="utf-8")
    pairs = re.findall(r"\\textbf\{([^}]+)\}\s*&\s*(.+?)\s*\\\\", text)
    return sorted(((t.strip(), d.strip()) for t, d in pairs),
                  key=lambda x: x[0].lower())


def _build_abbrev_table(doc) -> None:
    """Danh mục từ viết tắt thành bảng 4 cột (từ | nghĩa | từ | nghĩa) để tiết
    kiệm không gian. Chia đôi danh sách theo cột: nửa đầu (alphabet) xuống cột
    trái, nửa sau xuống cột phải, mỗi cột đọc từ trên xuống vẫn đúng thứ tự.
    Bề rộng và viền do format_data_tables xử lý sau."""
    pairs = _read_abbreviations()
    half = (len(pairs) + 1) // 2
    left, right = pairs[:half], pairs[half:]
    table = doc.add_table(rows=half, cols=4)
    for i in range(half):
        cells = table.rows[i].cells
        term, definition = left[i]
        cells[0].paragraphs[0].add_run(term).bold = True
        cells[1].paragraphs[0].add_run(definition)
        if i < len(right):
            term, definition = right[i]
            cells[2].paragraphs[0].add_run(term).bold = True
            cells[3].paragraphs[0].add_run(definition)


_BMID = [4000]  # id bookmark bắt đầu cao để không đụng bookmark pandoc


def _add_bookmark(paragraph, name: str) -> None:
    """Đánh dấu bookmark tại một caption trong thân để PAGEREF trỏ tới lấy số trang."""
    _BMID[0] += 1
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(_BMID[0]))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(_BMID[0]))
    p = paragraph._p
    pPr = p.find(qn("w:pPr"))
    if pPr is not None:
        pPr.addnext(start)
    else:
        p.insert(0, start)
    p.append(end)


def _add_list_entry(doc, text: str, bookmark: str, indent_cm=0.0, bold=False) -> None:
    """Một dòng mục lục/danh mục: toàn dòng là siêu liên kết nội bộ trỏ tới
    bookmark ở section/hình/bảng (bấm để nhảy tới), gồm nội dung + dấu chấm dẫn
    + số trang (PAGEREF). Không tô style Hyperlink để chữ giữ màu đen như mục lục
    chuẩn của luận văn."""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    if indent_cm:
        p.paragraph_format.left_indent = Cm(indent_cm)
    p.paragraph_format.tab_stops.add_tab_stop(
        Cm(15.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

    hyper = OxmlElement("w:hyperlink")
    hyper.set(qn("w:anchor"), bookmark)

    r = OxmlElement("w:r")
    if bold:
        rPr = OxmlElement("w:rPr")
        rPr.append(OxmlElement("w:b"))
        r.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    r.append(t)
    hyper.append(r)

    rt = OxmlElement("w:r")
    rt.append(OxmlElement("w:tab"))
    hyper.append(rt)

    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), f"PAGEREF {bookmark} \\h")
    fr = OxmlElement("w:r")
    ft = OxmlElement("w:t")
    ft.text = ""
    fr.append(ft)
    fld.append(fr)
    hyper.append(fld)

    p._p.append(hyper)


def _build_toc(front, body) -> None:
    """MỤC LỤC dạng dữ liệu thật: duyệt heading H1..H4 trong thân, gắn bookmark và
    tạo dòng có PAGEREF (thụt lề theo cấp, H1 in đậm). Không dùng field TOC vì
    LibreOffice không tái tạo field TOC của Word khi xuất PDF."""
    levels = {"Heading1": 1, "Heading2": 2, "Heading3": 3, "Heading4": 4}
    n = 0
    for p in body.paragraphs:
        lvl = levels.get(_para_style_id(p._p))
        if lvl and p.text.strip():
            n += 1
            bm = f"_toc_{n}"
            _add_bookmark(p, bm)
            _add_list_entry(front, p.text.strip(), bm,
                            indent_cm=0.6 * (lvl - 1), bold=(lvl == 1))
    if n == 0:
        front.add_paragraph("")


def _build_caption_list(front, body, style_id: str, tag: str) -> None:
    """Dựng DANH MỤC HÌNH/BẢNG dạng dữ liệu thật: duyệt caption theo đúng thứ tự
    xuất hiện trong thân (theo style pandoc), gắn bookmark tại từng caption và
    tạo dòng danh mục có PAGEREF. Nhờ vậy các mục hiện ngay, số trang tự điền khi
    Word cập nhật field (mở file hoặc Ctrl+A, F9)."""
    n = 0
    for p in body.paragraphs:
        if _para_style_id(p._p) == style_id and p.text.strip():
            n += 1
            bm = f"_lst_{tag}_{n}"
            _add_bookmark(p, bm)
            _add_list_entry(front, p.text.strip(), bm)
    if n == 0:
        front.add_paragraph("")


def build_toc_lists(doc, body) -> None:
    """MỤC LỤC (Word field) + DANH MỤC HÌNH/BẢNG (dữ liệu thật) + DANH MỤC TỪ VIẾT TẮT."""
    # Mỗi danh mục mở đầu bằng heading có pageBreakBefore (xem _heading_caps) thay
    # cho page break cứng ở cuối khối trước, nên không còn trang trắng chen giữa các
    # danh mục. Riêng "Mục lục" dựa vào page break sẵn có sau trang Lời cảm ơn.
    _heading_caps(doc, "Mục lục")
    _build_toc(doc, body)

    # Danh mục hình/bảng liệt kê trực tiếp từ caption trong thân (style ImageCaption
    # cho hình, TableCaption cho bảng) thay vì để trống chờ field TOC. Số "Hình 3.1"
    # là chữ literal do apply_numbering chèn; số trang qua PAGEREF, điền khi Word
    # cập nhật field.
    _heading_caps(doc, "Danh mục hình", page_break_before=True)
    _build_caption_list(doc, body, "ImageCaption", "fig")

    _heading_caps(doc, "Danh mục bảng", page_break_before=True)
    _build_caption_list(doc, body, "TableCaption", "tab")

    _heading_caps(doc, "Danh mục từ viết tắt", page_break_before=True)
    _build_abbrev_table(doc)


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


from docx.enum.text import WD_ALIGN_PARAGRAPH as _AL


def _insert_section_break_before(doc, paragraph):
    """Chèn DUY NHẤT một section break (nextPage) ngay trước `paragraph`.

    `paragraph` (abstract) trở thành nội dung ĐẦU TIÊN của section cuối (thân bài,
    mô tả bởi sectPr cuối tài liệu, mang pgNumType start=1) nên rơi đúng vào trang
    đánh số 1. Đoạn rỗng chèn thêm chỉ để KẾT THÚC section front matter bằng bản
    sao thuộc tính trang của sectPr cuối, đã bỏ pgNumType để front matter không tự
    khởi động lại số trang.

    Trước đây dùng python-docx add_section: nó sinh THÊM một section rỗng cũng mang
    pgNumType start=1, tạo một trang trắng bị đánh số 1 và đẩy abstract sang trang 2
    (mục lục lệch một trang). Đồng thời gỡ đoạn chỉ chứa page break đứng liền trước
    abstract vì section break nextPage đã tự sang trang, page break kia là thừa và
    sinh trang trắng.
    """
    body = doc.element.body
    # Sau khi ghép, sectPr của reference.docx nằm LẠC ở giữa (sau front matter,
    # trước body) và body KHÔNG có sectPr ở cuối. Lấy nó ra làm sectPr THÂN BÀI.
    sectprs = body.findall(qn("w:sectPr"))
    body_sectPr = sectprs[-1] if sectprs else OxmlElement("w:sectPr")
    if body_sectPr.getparent() is body:
        body.remove(body_sectPr)

    # Gỡ các đoạn rỗng/chỉ chứa page break đứng liền trước abstract (thừa vì
    # section break nextPage đã tự sang trang).
    prev = paragraph._p.getprevious()
    while prev is not None and prev.tag == qn("w:p"):
        pPr = prev.find(qn("w:pPr"))
        has_sect = pPr is not None and pPr.find(qn("w:sectPr")) is not None
        has_text = any(r.findall(qn("w:t")) for r in prev.findall(qn("w:r")))
        if has_sect or has_text:
            break
        nxt = prev.getprevious()
        body.remove(prev)
        prev = nxt

    # Đoạn KẾT THÚC section front matter: bản sao thuộc tính trang của sectPr thân
    # bài, bỏ pgNumType để front matter không tự khởi động lại số trang.
    sep_p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    front_sectPr = copy.deepcopy(body_sectPr)
    pgnum = front_sectPr.find(qn("w:pgNumType"))
    if pgnum is not None:
        front_sectPr.remove(pgnum)
    pPr.append(front_sectPr)
    sep_p.append(pPr)
    paragraph._p.addprevious(sep_p)

    # sectPr thân bài về CUỐI body (sentinel cho section cuối, đúng lược đồ OOXML).
    body.append(body_sectPr)
    return doc.sections[-1]


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


def set_update_fields_on_open(doc) -> None:
    """Bật cờ để Word/LibreOffice tự cập nhật mọi field khi mở.

    Mục lục và danh mục hình/bảng là Word field, để trống trong file cho tới khi
    field được cập nhật. Nếu không có cờ này, người mở phải tự bấm Ctrl+A, F9 và
    thường không biết nên thấy "thiếu mục lục". Đặt <w:updateFields val="true">
    khiến Word hỏi cập nhật khi mở (LibreOffice tự cập nhật). Chèn ngay trước
    <w:footnotePr> cho đúng thứ tự lược đồ CT_Settings."""
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is not None:
        return
    el = OxmlElement("w:updateFields")
    el.set(qn("w:val"), "true")
    ref = settings.find(qn("w:footnotePr"))
    if ref is not None:
        ref.addprevious(el)
    else:
        settings.append(el)


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


def carry_images(src_doc, dst_doc) -> None:
    """Chép mọi image part từ src sang dst và ánh xạ lại r:embed/r:id.

    python-docx gộp phần thân bằng cách append phần tử XML, nhưng không mang
    theo part ảnh lẫn quan hệ rId. Hàm này thêm từng image part vào dst (nhận
    rId mới, không đụng rId sẵn có của dst) rồi ghi lại tham chiếu trong thân
    src trước khi các phần tử đó được chuyển sang dst.
    """
    IMG = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    id_map = {}
    for rId, rel in list(src_doc.part.rels.items()):
        if rel.reltype == IMG and not rel.is_external:
            id_map[rId] = dst_doc.part.relate_to(rel.target_part, IMG)
    if not id_map:
        return
    body = src_doc.element.body
    for blip in body.iter(qn("a:blip")):
        for attr in (qn("r:embed"), qn("r:link")):
            old = blip.get(attr)
            if old in id_map:
                blip.set(attr, id_map[old])


# Thứ tự phần tử con hợp lệ trong CT_TblPr (lược đồ OOXML). Chèn sai thứ tự làm
# Word báo hỏng file, nên mọi lần thêm con vào tblPr phải theo bảng này.
_TBLPR_ORDER = [
    "w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual",
    "w:tblStyleRowBandSize", "w:tblStyleColBandSize", "w:tblW", "w:jc",
    "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd", "w:tblLayout",
    "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription",
]


def _set_tblpr_child(tblPr, el):
    """Thay/chèn một con của tblPr đúng thứ tự lược đồ (bỏ bản cũ cùng thẻ)."""
    order = [qn(t) for t in _TBLPR_ORDER]
    for old in tblPr.findall(el.tag):
        tblPr.remove(old)
    idx = order.index(el.tag)
    ref = next((c for c in tblPr if c.tag in order and order.index(c.tag) > idx),
               None)
    if ref is None:
        tblPr.append(el)
    else:
        ref.addprevious(el)


def format_data_tables(doc, sz="6", color="000000"):
    """Ép mọi bảng dữ liệu vừa bề rộng trang và có viền.

    pandoc xuất bảng với tblW auto (rộng theo nội dung) nên bảng co cụm, lệch
    trái. Đặt bề rộng 100% (pct 5000), canh giữa, tblLayout autofit để Word dàn
    cột lấp đầy lề, và bỏ bề rộng ô cố định. Viền đơn 0,75 pt (sz=6, 1/8 pt) cả
    cạnh ngoài lẫn đường trong cho dễ đọc. Chạy sau khi figure đã được gỡ khỏi
    bảng nên chỉ còn bảng dữ liệu thật."""
    edges = ("top", "left", "bottom", "right", "insideH", "insideV")
    for table in doc.tables:
        tblPr = table._tbl.tblPr

        w = OxmlElement("w:tblW")
        w.set(qn("w:type"), "pct")
        w.set(qn("w:w"), "5000")
        _set_tblpr_child(tblPr, w)

        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "center")
        _set_tblpr_child(tblPr, jc)

        borders = OxmlElement("w:tblBorders")
        for edge in edges:
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), sz)
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), color)
            borders.append(el)
        _set_tblpr_child(tblPr, borders)

        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "autofit")
        _set_tblpr_child(tblPr, lay)

        # Bỏ bề rộng ô cố định để autofit phân bổ lại theo bề rộng 100%.
        for tcW in table._tbl.iter(qn("w:tcW")):
            tcW.set(qn("w:type"), "auto")
            tcW.set(qn("w:w"), "0")


def ensure_caption_styles(doc):
    """Định nghĩa style caption/nguồn trong doc cuối.

    pandoc gắn nhãn caption bằng styleId ImageCaption/TableCaption nhưng KHÔNG
    định nghĩa style, nên Word coi như Normal và công tắc TOC \\t không gom được.
    Định nghĩa hai style này (Times, canh giữa, giữ cùng khối với hình/bảng) để
    danh mục hình/bảng gom đúng, thêm SourceNote cho dòng Nguồn (nhỏ, nghiêng)."""
    existing = {s.style_id for s in doc.styles}
    for sid, size, italic in (("ImageCaption", 12, False),
                              ("TableCaption", 12, False),
                              ("SourceNote", 11, True)):
        if sid in existing:
            st = doc.styles[sid]
        else:
            st = doc.styles.add_style(sid, WD_STYLE_TYPE.PARAGRAPH)
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.italic = italic
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER


def set_heading_format(doc):
    """Ép cỡ chữ tiêu đề theo phụ lục hình thức UIT: Chương (Heading 1) 14pt in
    đậm, mục và tiểu mục (Heading 2..4) 13pt in đậm, chữ đen, Times New Roman.

    BieuMau kế thừa heading Word mặc định (20/16/14pt, màu xanh theme) nên nếu
    không ép lại thì cỡ chữ và màu tiêu đề sai so với quy định (Chương font 14,
    mục/tiểu mục font 13, in đậm)."""
    from docx.shared import RGBColor
    for name, size in (("Heading 1", 14), ("Heading 2", 13),
                       ("Heading 3", 13), ("Heading 4", 13)):
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)


def _cell_paragraphs(tc):
    return tc.findall(qn("w:p"))


def _center_paragraph(p):
    pPr = p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p.insert(0, pPr)
    for old in pPr.findall(qn("w:jc")):
        pPr.remove(old)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    pPr.append(jc)


def _set_pstyle(p, style_id):
    pPr = p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p.insert(0, pPr)
    for old in pPr.findall(qn("w:pStyle")):
        pPr.remove(old)
    ps = OxmlElement("w:pStyle")
    ps.set(qn("w:val"), style_id)
    pPr.insert(0, ps)


def _resize_drawing(scope, target_w_emu, max_h_emu):
    """Đặt lại bề rộng ảnh về target, giữ tỉ lệ; hạ xuống nếu vượt chiều cao."""
    for dr in scope.iter(qn("w:drawing")):
        ext = dr.find(".//" + qn("wp:extent"))
        if ext is None:
            continue
        cx, cy = int(ext.get("cx")), int(ext.get("cy"))
        if cx <= 0 or cy <= 0:
            continue
        new_cx = int(target_w_emu)
        new_cy = int(cy * new_cx / cx)
        if new_cy > max_h_emu:
            new_cy = int(max_h_emu)
            new_cx = int(cx * new_cy / cy)
        ext.set("cx", str(new_cx))
        ext.set("cy", str(new_cy))
        for aext in dr.iter(qn("a:ext")):
            aext.set("cx", str(new_cx))
            aext.set("cy", str(new_cy))


def unwrap_figures(doc):
    """Gỡ figure khỏi bảng 2 cột mà pandoc dựng.

    pandoc gói mỗi hình (ảnh + khối {\\footnotesize Nguồn}) thành bảng style
    FigureTable hai cột: ô trái là ảnh bị co vào ~2,75 inch, ô phải là dòng
    Nguồn; caption nằm dưới bảng. Kết quả sai hình thức. Hàm này thay mỗi bảng
    FigureTable bằng: đoạn ảnh căn giữa cỡ lớn (đứng trước bảng), giữ nguyên
    caption ngay sau, rồi chèn dòng Nguồn xuống sau caption. Chạy trên body
    trước carry_images (blip vẫn nằm trong body nên rId được ánh xạ như cũ)."""
    target_w = Cm(14)          # bề rộng ảnh mục tiêu (lề trong ~15,5 cm)
    max_h = Cm(19)             # trần chiều cao để ảnh dọc không tràn trang
    body = doc.element.body
    for tbl in list(body.iter(qn("w:tbl"))):
        tblPr = tbl.find(qn("w:tblPr"))
        st = tblPr.find(qn("w:tblStyle")) if tblPr is not None else None
        if st is None or st.get(qn("w:val")) != "FigureTable":
            continue
        tr = tbl.find(qn("w:tr"))
        if tr is None:
            continue
        tcs = tr.findall(qn("w:tc"))
        if not tcs:
            continue
        img_cell = tcs[0]
        src_cell = tcs[1] if len(tcs) > 1 else None

        _resize_drawing(img_cell, target_w, max_h)

        # caption = đoạn kế tiếp bảng (bỏ qua bookmark), style ImageCaption.
        caption = tbl.getnext()
        while caption is not None and not caption.tag.endswith("}p"):
            caption = caption.getnext()

        # Đưa đoạn ảnh ra trước bảng, căn giữa.
        for p in _cell_paragraphs(img_cell):
            _center_paragraph(p)
            tbl.addprevious(p)

        # Đưa dòng Nguồn xuống sau caption (giữ mọi run gốc), style SourceNote.
        anchor = caption if caption is not None else tbl
        prev = anchor
        if src_cell is not None:
            for p in _cell_paragraphs(src_cell):
                _set_pstyle(p, "SourceNote")
                _center_paragraph(p)
                prev.addnext(p)
                prev = p

        body.remove(tbl)


_SKIP_HEADINGS = {"tóm tắt nội dung", "danh mục từ viết tắt"}
_BIBLIO_HEADINGS = {"tài liệu tiếng việt", "tài liệu tiếng anh"}


def _para_text(p):
    return "".join(t.text or "" for t in p.findall(".//" + qn("w:t")))


def _para_style_id(p):
    sp = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    return sp.get(qn("w:val")) if sp is not None else "Normal"


def _prepend_label(p, text, bold=True):
    """Chèn một run nhãn (số thứ tự) vào đầu đoạn, sau pPr."""
    r = OxmlElement("w:r")
    if bold:
        rPr = OxmlElement("w:rPr")
        rPr.append(OxmlElement("w:b"))
        r.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    pPr = p.find(qn("w:pPr"))
    if pPr is not None:
        pPr.addnext(r)
    else:
        p.insert(0, r)


def read_appendix_titles(main_tex) -> set:
    """Tập tiêu đề (IN HOA) các chương phụ lục, lấy từ appendices/*.tex.

    Cần phân biệt phụ lục với chương thân bài: citeproc của pandoc dồn danh mục
    tham khảo xuống CUỐI tài liệu (sau phụ lục), nên không thể suy phụ lục từ vị
    trí danh mục tham khảo. Dựa vào chính tiêu đề chương trong nguồn LaTeX."""
    text = Path(main_tex).read_text(encoding="utf-8")
    titles = set()
    for name in re.findall(r"\\input\{appendices/([^}]+)\}", text):
        f = HERE / "appendices" / f"{name}.tex"
        if not f.exists():
            continue
        m = re.search(r"\\chapter\*?\{([^}]+)\}", f.read_text(encoding="utf-8"))
        if m:
            titles.add(m.group(1).strip().upper())
    return titles


def apply_numbering(doc, appendix_titles=frozenset()):
    """Đánh số literal cho tiêu đề và caption theo chương (như BieuMau).

    Tiêu đề: "Chương N. " cho H1 chương, "Phụ lục X. " cho H1 phụ lục, "N.M. ",
    "N.M.P. ", "N.M.P.Q. " cho H2/H3/H4; bỏ qua Tóm tắt và hai heading tài liệu
    tham khảo. Caption: "Hình N.k: " (ImageCaption) và "Bảng N.k: " (TableCaption)
    đếm lại theo mỗi chương. Số là chữ literal nên hiện đúng ngay; mục lục và
    danh mục hình/bảng lấy chính chuỗi này. Chạy sau uppercase_chapter_titles
    (để "Chương" giữ chữ thường) và split_bibliography (để có heading tài liệu)."""
    chap = 0
    appx = ord("A") - 1
    label = None
    sub = [0, 0, 0]
    fig = tab = 0
    for p in doc.element.body.iterchildren():
        if not p.tag.endswith("}p"):
            continue
        style = _para_style_id(p)
        text = _para_text(p).strip()
        low = text.lower()
        if style == "Heading1":
            if low in _SKIP_HEADINGS or low in _BIBLIO_HEADINGS:
                label = None
                continue
            sub = [0, 0, 0]
            fig = tab = 0
            if text.upper() in appendix_titles:
                appx += 1
                label = chr(appx)
                _prepend_label(p, f"Phụ lục {chr(appx)}. ")
            else:
                chap += 1
                label = str(chap)
                _prepend_label(p, f"Chương {chap}. ")
        elif label is None:
            continue
        elif style == "Heading2":
            sub[0] += 1
            sub[1] = sub[2] = 0
            _prepend_label(p, f"{label}.{sub[0]}. ")
        elif style == "Heading3":
            sub[1] += 1
            sub[2] = 0
            _prepend_label(p, f"{label}.{sub[0]}.{sub[1]}. ")
        elif style == "Heading4":
            sub[2] += 1
            _prepend_label(p, f"{label}.{sub[0]}.{sub[1]}.{sub[2]}. ")
        elif style == "ImageCaption":
            fig += 1
            _prepend_label(p, f"Hình {label}.{fig}: ")
        elif style == "TableCaption":
            tab += 1
            _prepend_label(p, f"Bảng {label}.{tab}: ")


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]
    body_docx, main_tex, out_docx = argv[0], argv[1], argv[2]

    doc = docx.Document(body_docx)
    meta = read_thesis_meta(Path(main_tex))
    ack = (HERE / "frontmatter" / "loicamon.txt").read_text(encoding="utf-8")

    strip_before_abstract(doc)
    unwrap_figures(doc)
    uppercase_chapter_titles(doc)
    split_bibliography(doc)
    apply_numbering(doc, read_appendix_titles(Path(main_tex)))

    # Dựng front matter vào một doc mới rồi ghép body vào sau.
    front = docx.Document(str(HERE / "reference.docx"))
    # reference.docx có 1 đoạn trống; xóa để bắt đầu sạch.
    for p in list(front.paragraphs):
        p._p.getparent().remove(p._p)
    ensure_caption_styles(front)
    set_heading_format(front)
    # Một trang bìa duy nhất, có giảng viên hướng dẫn. (Trước đây dựng cả bìa
    # chính lẫn bìa phụ nên trang đầu bị lặp gần như giống hệt.)
    build_cover(front, meta, with_supervisor=True)
    build_council_page(front)
    build_acknowledgement(front, ack)
    build_toc_lists(front, doc)

    # Chuyển các part ảnh của body sang front và ánh xạ lại rId (nếu không,
    # các phần tử <w:drawing> chép sang front sẽ trỏ rId không tồn tại và
    # ảnh biến mất khỏi main.docx).
    carry_images(doc, front)

    # Ghép mọi phần tử body (đã strip) vào cuối front.
    for child in list(doc.element.body):
        if child.tag.endswith("}sectPr"):
            continue
        front.element.body.append(child)

    format_data_tables(front)

    abstract = next(p for p in front.paragraphs if "tóm tắt" in p.text.lower()
                    and p.style.name.startswith("Heading"))
    set_page_numbering(front, abstract)
    set_update_fields_on_open(front)
    front.save(out_docx)
    print(f"wrote {out_docx}")


if __name__ == "__main__":
    main()
