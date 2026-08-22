from pydantic import BaseModel


class PlateItem(BaseModel):
    bbox: list[float] | None = None
    layout: str | None = None
    det_conf: float | None = None
    plate_text: str | None = None
    plate_valid: bool | None = None
    ocr_conf: float | None = None
    color: str | None = None
    color_conf: float | None = None


class PipelinePayload(BaseModel):
    vehicle_type: str | None = None
    vehicle_box: list[float] | None = None
    vehicle_style: str | None = None
    vehicle_style_conf: float | None = None
    plates: list[PlateItem] = []


class CaptureResponse(BaseModel):
    reading_id: int
    capture_id: str
    direction: str
    review_state: str
    plate_text: str | None = None
    plate_valid: bool | None = None
    vehicle_type: str | None = None
    vehicle_group: str | None = None
    color: str | None = None
    image_asset_id: int | None = None
    duplicate: bool = False
