import pytest
from plate_detect.data.bbox import polygon_to_bbox

def test_axis_aligned_rectangle():
    # corners of rect [0.2,0.3]..[0.6,0.5]
    coords = [0.2, 0.3, 0.6, 0.3, 0.6, 0.5, 0.2, 0.5]
    xc, yc, w, h = polygon_to_bbox(coords)
    assert xc == pytest.approx(0.4)
    assert yc == pytest.approx(0.4)
    assert w == pytest.approx(0.4)
    assert h == pytest.approx(0.2)

def test_tilted_quad_uses_minmax():
    coords = [0.30, 0.20, 0.70, 0.30, 0.65, 0.55, 0.25, 0.45]
    xc, yc, w, h = polygon_to_bbox(coords)
    assert w == pytest.approx(0.45)   # 0.70 - 0.25
    assert h == pytest.approx(0.35)   # 0.55 - 0.20

def test_clamp_out_of_range():
    coords = [-0.1, 0.0, 1.2, 0.0, 1.2, 0.5, -0.1, 0.5]
    xc, yc, w, h = polygon_to_bbox(coords)
    assert 0.0 <= xc <= 1.0 and 0.0 <= w <= 1.0
    assert w == pytest.approx(1.0)    # clamped 0..1

def test_degenerate_returns_none():
    coords = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    assert polygon_to_bbox(coords) is None
