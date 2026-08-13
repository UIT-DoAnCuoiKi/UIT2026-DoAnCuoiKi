import pytest
from plate_detect.data.class_map import infer_layout_map, verify_class_map

def test_widest_class_is_1row():
    # class 0 mean aspect ~4 (long/1-row), class 1 ~1.3 (square/2-row)
    m = infer_layout_map({0: [4.0, 3.8, 4.2], 1: [1.3, 1.2, 1.4]})
    assert m == {0: "bien_1hang", 1: "bien_2hang"}

def test_verify_accepts_matching_bsd_bsv():
    inferred = {0: "bien_1hang", 1: "bien_2hang"}
    assert verify_class_map(inferred, {0: "BSD", 1: "BSV"}) == inferred

def test_verify_raises_on_conflict():
    inferred = {0: "bien_2hang", 1: "bien_1hang"}   # inverted vs yaml
    with pytest.raises(ValueError):
        verify_class_map(inferred, {0: "BSD", 1: "BSV"})
