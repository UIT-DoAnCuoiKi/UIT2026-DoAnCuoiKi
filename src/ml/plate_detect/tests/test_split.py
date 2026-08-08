import pytest
from plate_detect.data.split import stratified_split

def test_deterministic_and_disjoint():
    items = [f"img_{i}" for i in range(20)]
    labels = [i % 2 for i in range(20)]
    a = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    b = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    assert a == b                                  # deterministic
    assert set(a["val"]) | set(a["test"]) == set(items)
    assert set(a["val"]) & set(a["test"]) == set()  # disjoint

def test_stratifies_each_label():
    items = [f"img_{i}" for i in range(20)]
    labels = [i % 2 for i in range(20)]           # 10 of each label
    out = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=1)
    # each label split ~50/50 → 5 of each label per bucket
    for bucket in ("val", "test"):
        got = [int(n.split("_")[1]) % 2 for n in out[bucket]]
        assert got.count(0) == 5 and got.count(1) == 5

def test_bad_ratios_raise():
    with pytest.raises(ValueError):
        stratified_split(["a"], [0], {"val": 0.4, "test": 0.4}, seed=0)
