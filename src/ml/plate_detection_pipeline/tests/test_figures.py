import os
from plate_detect.data.fixtures import make_raw_fixture
from plate_detect.data.adapters import A1Adapter
from plate_detect.figures import class_map_grid

def test_class_map_grid_writes_png(tmp_path):
    make_raw_fixture(str(tmp_path / "raw"), n_per_split=8, seed=0)
    recs = A1Adapter().read_raw(str(tmp_path / "raw"))
    out = class_map_grid(recs, {0: "bien_1hang", 1: "bien_2hang"},
                         str(tmp_path / "class_map.png"), per_class=4)
    assert os.path.exists(out) and os.path.getsize(out) > 0
