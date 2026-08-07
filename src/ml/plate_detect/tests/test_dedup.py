import numpy as np
from plate_detect.data.dedup import ahash, hamming, find_duplicates

def _img(v): return np.full((64, 64, 3), v, np.uint8)

def test_identical_hash_zero_distance():
    a = ahash(_img(120)); b = ahash(_img(120))
    assert hamming(a, b) == 0

def test_find_duplicates_flags_near():
    grad = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1))
    grad = np.stack([grad] * 3, axis=-1)
    train = {"t0": ahash(grad)}
    test = {"q0": ahash(grad.copy()), "q1": ahash(_img(10))}
    dups = find_duplicates(train, test, threshold=5)
    names = {d[0] for d in dups}
    assert "q0" in names          # duplicate of t0
    assert "q1" not in names      # flat image, different

def test_ahash_grayscale_input():
    # ahash must handle an already-gray 2D array (not just 3-channel BGR)
    g = np.full((64, 64), 120, np.uint8)
    assert isinstance(ahash(g), int)

def test_find_duplicates_empty_train():
    # empty train dict -> nothing can be a duplicate
    assert find_duplicates({}, {"q": ahash(_img(0))}) == []

