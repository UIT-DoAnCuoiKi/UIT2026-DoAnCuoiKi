import numpy as np
from plate_detect.data.dedup import ahash, hamming, find_duplicates

def test_ahash_identical_zero_distance():
    img = (np.random.default_rng(0).random((40, 60, 3)) * 255).astype("uint8")
    assert hamming(ahash(img), ahash(img.copy())) == 0

def test_find_duplicates_matches_near_dupes():
    img = (np.random.default_rng(1).random((40, 60, 3)) * 255).astype("uint8")
    h = ahash(img)
    train = {"t0.jpg": h}
    test = {"q0.jpg": h, "q1.jpg": h ^ 0b111111}   # q1 far (6 bits)
    dups = find_duplicates(train, test, threshold=5)
    names = [d[0] for d in dups]
    assert "q0.jpg" in names and "q1.jpg" not in names
