import pytest
from plate_detect.data.class_map import infer_layout_map, verify_class_map


def test_infer_wide_is_1hang():
    objs = {0: [4.0, 3.8, 4.2], 1: [1.3, 1.2, 1.4]}   # class 0 wide, class 1 square
    m = infer_layout_map(objs)
    assert m == {0: "bien_1hang", 1: "bien_2hang"}


def test_infer_when_ids_swapped():
    objs = {0: [1.3, 1.2], 1: [4.0, 4.1]}             # class 1 is the wide one
    m = infer_layout_map(objs)
    assert m == {0: "bien_2hang", 1: "bien_1hang"}


def test_verify_agrees():
    inferred = {0: "bien_1hang", 1: "bien_2hang"}
    assert verify_class_map(inferred, {0: "bien_1hang", 1: "bien_2hang"}) == inferred


def test_verify_conflict_raises():
    inferred = {0: "bien_1hang", 1: "bien_2hang"}
    with pytest.raises(ValueError):
        verify_class_map(inferred, {0: "bien_2hang", 1: "bien_1hang"})
