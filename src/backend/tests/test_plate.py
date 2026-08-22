from app.security import plate


def test_normalize_strips_separators_and_uppercases():
    assert plate.normalize_plate("51f-123.45") == "51F12345"
    assert plate.normalize_plate("  30A 678.90 ") == "30A67890"


def test_hash_is_deterministic_over_normalization():
    assert plate.plate_hash("51F-123.45") == plate.plate_hash("51f 123 45")


def test_hash_differs_for_different_plates():
    assert plate.plate_hash("51F-123.45") != plate.plate_hash("51F-123.46")
