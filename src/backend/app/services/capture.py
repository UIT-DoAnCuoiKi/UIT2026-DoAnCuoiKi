from app.schemas.capture import PlateItem

OCR_CONF_MIN = 0.7
DET_CONF_MIN = 0.5


def select_representative(plates: list[PlateItem]) -> PlateItem | None:
    if not plates:
        return None
    return max(plates, key=lambda p: p.det_conf if p.det_conf is not None else -1.0)


def compute_review_state(rep: PlateItem | None) -> str:
    if rep is None or not rep.plate_text:
        return "needs_review"
    if rep.plate_valid is False:
        return "needs_review"
    if rep.ocr_conf is not None and rep.ocr_conf < OCR_CONF_MIN:
        return "needs_review"
    if rep.det_conf is not None and rep.det_conf < DET_CONF_MIN:
        return "needs_review"
    return "confident"
