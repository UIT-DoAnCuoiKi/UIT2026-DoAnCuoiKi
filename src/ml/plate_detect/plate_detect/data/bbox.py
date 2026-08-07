from __future__ import annotations

def polygon_to_bbox(coords: list[float]):
    xs = [min(1.0, max(0.0, v)) for v in coords[0::2]]
    ys = [min(1.0, max(0.0, v)) for v in coords[1::2]]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None
    return ((x1 + x2) / 2, (y1 + y2) / 2, w, h)
