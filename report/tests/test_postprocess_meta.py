from pathlib import Path
import docx
from docx.oxml.ns import qn

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import postprocess as pp

MAIN = Path(__file__).resolve().parents[1] / "main.tex"


def test_read_thesis_meta_pulls_newcommands():
    meta = pp.read_thesis_meta(MAIN)
    assert meta["student_a"] == "Nguyễn Minh Nhật"
    assert meta["student_a_id"] == "25410104"
    assert meta["student_b_id"] == "25410034"
    assert meta["supervisor"].startswith("ThS")
    assert "bãi giữ xe" in meta["title_vi"]


def test_add_field_appends_fldsimple():
    d = docx.Document()
    p = d.add_paragraph()
    pp.add_field(p, 'PAGE')
    flds = p._p.findall(qn("w:fldSimple"))
    assert len(flds) == 1
    assert flds[0].get(qn("w:instr")) == "PAGE"
