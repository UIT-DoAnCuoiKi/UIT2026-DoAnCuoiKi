import pytest
from plate_detect.data.split import stratified_split

def _items(n): return [f"img_{i}" for i in range(n)]

def test_deterministic():
    items = _items(100); labels = [i % 2 for i in range(100)]
    a = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    b = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
    assert a == b

def test_disjoint_and_complete():
    items = _items(100); labels = [i % 2 for i in range(100)]
    out = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=1)
    val, test = set(out["val"]), set(out["test"])
    assert val.isdisjoint(test)
    assert val | test == set(items)

def test_stratified_balance():
    # 80 of class 0, 20 of class 1
    items = _items(100); labels = [0] * 80 + [1] * 20
    out = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=7)
    c1_val = sum(1 for x in out["val"] if int(x.split("_")[1]) >= 80)
    assert c1_val == pytest.approx(10, abs=1)   # ~half of the 20 class-1 items

def test_ratios_must_sum_to_one():
    with pytest.raises(ValueError):
        stratified_split(_items(4), [0, 0, 1, 1], {"val": 0.4, "test": 0.4}, seed=0)
