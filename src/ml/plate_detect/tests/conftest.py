import pytest
from plate_detect.data.fixtures import make_raw_fixture

@pytest.fixture
def raw_fixture(tmp_path):
    root = tmp_path / "raw"
    make_raw_fixture(str(root), n_per_split=10, seed=0)
    return root
