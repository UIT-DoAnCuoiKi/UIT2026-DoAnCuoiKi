#!/usr/bin/env python3
"""Dựng reference.docx từ BieuMau.docx: giữ style + geometry, xóa nội dung.

pandoc dùng file này làm khung style cho body.docx. Ta lấy chính BieuMau làm
gốc để mọi đoạn body kế thừa đúng Times 13pt, giãn dòng 1,5 và lề BieuMau,
rồi ép lại các giá trị bắt buộc phòng khi BieuMau thiếu.
"""
import re
import zipfile
from pathlib import Path
import docx
from docx.shared import Pt, Cm

HERE = Path(__file__).resolve().parent
SRC = HERE / "BieuMau.docx"
OUT = HERE / "reference.docx"


def force_theme_times(path: Path) -> None:
    """Ép font Latin của theme (major + minor) về Times New Roman.

    Heading của BieuMau dùng font 'major' của theme (w:asciiTheme="majorHAnsi"),
    mà theme mặc định Office lại là Aptos Display / Aptos, nên heading render ra
    font khác Times dù body đã ép Times qua style Normal. Sửa ngay trong theme
    để CẢ tài liệu chỉ dùng một font Times New Roman. Ánh xạ <a:font script="Viet">
    không đủ vì ký tự tiếng Việt nằm trong dải Latin, Word dùng <a:latin>.
    """
    tmp = path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(path) as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            data = zin.read(item)
            if item.startswith("word/theme/theme") and item.endswith(".xml"):
                txt = data.decode("utf-8")
                # Chỉ đổi <a:latin> trong majorFont và minorFont, giữ nguyên
                # các <a:font script="..."> và phần khác của theme.
                for block in ("majorFont", "minorFont"):
                    txt = re.sub(
                        rf'(<a:{block}>.*?<a:latin[^>]*typeface=")[^"]*(")',
                        r'\1Times New Roman\2', txt, count=1, flags=re.DOTALL)
                data = txt.encode("utf-8")
            elif item == "word/styles.xml":
                # Ép mọi font Latin KHAI BÁO TƯỜNG MINH (w:ascii/w:hAnsi) về Times,
                # ví dụ style Footer của BieuMau dùng Cambria. Không chạm các thuộc
                # tính theme (w:asciiTheme/w:hAnsiTheme) nên phần kế thừa theme giữ nguyên.
                txt = data.decode("utf-8")
                txt = re.sub(r'(w:(?:ascii|hAnsi)=")[^"]*(")',
                             r'\1Times New Roman\2', txt)
                data = txt.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(path)


def main():
    d = docx.Document(str(SRC))

    # Xóa toàn bộ nội dung thân, giữ nguyên bảng style và sectPr.
    body = d.element.body
    for child in list(body):
        if child.tag.endswith("}p") or child.tag.endswith("}tbl"):
            body.remove(child)

    # Ép Normal về Times New Roman 13pt, giãn dòng 1,5.
    normal = d.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(13)
    normal.paragraph_format.line_spacing = 1.5

    # Ép lề BieuMau trên mọi section còn lại.
    for sec in d.sections:
        sec.top_margin = Cm(3)
        sec.bottom_margin = Cm(3.5)
        sec.left_margin = Cm(3.5)
        sec.right_margin = Cm(2)

    # python-docx cần ít nhất một đoạn để lưu hợp lệ.
    d.add_paragraph("")
    d.save(str(OUT))

    # Ép theme major/minor Latin về Times New Roman (heading kế thừa font major).
    force_theme_times(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
