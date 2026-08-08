from plate_detect.data.adapters import A1Adapter
from plate_detect.data.fixtures import make_raw_fixture  # created in T7

def test_reads_polygon_records(tmp_path):
    make_raw_fixture(str(tmp_path), n_per_split=4, seed=0)
    recs = A1Adapter().read_raw(str(tmp_path))
    assert len(recs) == 8                       # 4 train + 4 val
    r = recs[0]
    assert set(r) == {"split", "image_path", "objects"}
    cls, coords = r["objects"][0]
    assert isinstance(cls, int) and len(coords) == 8
