from app.schemas.capture import PlateItem
from app.services.capture import compute_review_state, select_representative
from app.services.vehicle_groups import group_for


def test_select_highest_det_conf():
    plates = [PlateItem(plate_text="A", det_conf=0.6), PlateItem(plate_text="B", det_conf=0.9)]
    assert select_representative(plates).plate_text == "B"


def test_select_none_when_empty():
    assert select_representative([]) is None


def test_review_confident():
    rep = PlateItem(plate_text="51F12345", det_conf=0.95, ocr_conf=0.9, plate_valid=True)
    assert compute_review_state(rep) == "confident"


def test_review_needs_low_ocr():
    rep = PlateItem(plate_text="51F12345", det_conf=0.95, ocr_conf=0.5, plate_valid=True)
    assert compute_review_state(rep) == "needs_review"


def test_review_needs_invalid():
    rep = PlateItem(plate_text="???", det_conf=0.95, ocr_conf=0.9, plate_valid=False)
    assert compute_review_state(rep) == "needs_review"


def test_review_needs_no_plate():
    assert compute_review_state(None) == "needs_review"


def test_group_mapping():
    assert group_for("car") == "o_to_con"
    assert group_for("motorbike") == "xe_may"
    assert group_for("bicycle") == "xe_may"
    assert group_for("truck") == "xe_tai"
    assert group_for("bus") == "xe_khach"
    assert group_for(None) is None
    assert group_for("unknown") is None
