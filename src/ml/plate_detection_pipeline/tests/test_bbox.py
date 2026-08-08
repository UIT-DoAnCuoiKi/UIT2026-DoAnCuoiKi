from plate_detect.data.bbox import polygon_to_bbox

def test_square_polygon_to_center_wh():
    xc, yc, w, h = polygon_to_bbox([0.2, 0.2, 0.6, 0.2, 0.6, 0.8, 0.2, 0.8])
    assert abs(xc - 0.4) < 1e-9 and abs(yc - 0.5) < 1e-9
    assert abs(w - 0.4) < 1e-9 and abs(h - 0.6) < 1e-9

def test_clamps_out_of_range():
    xc, yc, w, h = polygon_to_bbox([-0.1, 0.0, 1.2, 0.0, 1.2, 0.5, -0.1, 0.5])
    assert 0.0 <= xc <= 1.0 and w <= 1.0

def test_degenerate_returns_none():
    assert polygon_to_bbox([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]) is None
