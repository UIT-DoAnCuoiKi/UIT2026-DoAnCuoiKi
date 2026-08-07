from pathlib import Path
from plate_detect.data.fixtures import make_raw_fixture

def test_make_raw_fixture_layout(tmp_path):
    make_raw_fixture(str(tmp_path), n_per_split=4, seed=0)
    for split in ("train", "val"):
        imgs = list((tmp_path / "images" / split).glob("*.jpg"))
        lbls = list((tmp_path / "labels" / split).glob("*.txt"))
        assert len(imgs) == 4
        assert len(lbls) == 4
    # every label line: class in {0,1} + 8 normalized coords in [0,1]
    line = (tmp_path / "labels" / "train").glob("*.txt").__next__().read_text().splitlines()[0]
    parts = line.split()
    assert parts[0] in {"0", "1"}
    coords = list(map(float, parts[1:]))
    assert len(coords) == 8
    assert all(0.0 <= v <= 1.0 for v in coords)

def test_make_raw_fixture_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    make_raw_fixture(str(a), n_per_split=3, seed=42)
    make_raw_fixture(str(b), n_per_split=3, seed=42)
    la = sorted(p.name for p in (a / "labels" / "train").glob("*.txt"))
    lb = sorted(p.name for p in (b / "labels" / "train").glob("*.txt"))
    assert la == lb
