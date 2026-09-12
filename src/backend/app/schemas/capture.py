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
    crop_proc_b64: str | None = None


class PipelinePayload(BaseModel):
    vehicle_type: str | None = None
    vehicle_box: list[float] | None = None
    vehicle_style: str | None = None
    vehicle_style_conf: float | None = None
    plates: list[PlateItem] = []
    # Thời gian từng giai đoạn suy luận (ms), chỉ có khi bật dev_mode. Khoá là
    # tên giai đoạn do pipeline đặt nên để dict mở, không ràng buộc cứng.
    timings_ms: dict[str, float] | None = None
    # Tài nguyên tiêu thụ cho đúng lượt suy luận này (RAM, số lõi dùng trung
    # bình). Cùng điều kiện dev_mode với timings_ms.
    resources: dict[str, float] | None = None


class ReadingImageOut(BaseModel):
    role: str
    image_asset_id: int
    is_primary: bool


class CaptureResponse(BaseModel):
    reading_id: int
    capture_id: str
    direction: str
    lane: str | None = None
    review_state: str
    plate_text: str | None = None
    plate_valid: bool | None = None
    vehicle_type: str | None = None
    vehicle_group: str | None = None
    color: str | None = None
    ocr_conf: float | None = None
    color_conf: float | None = None
    image_asset_id: int | None = None
    plate_crop_asset_id: int | None = None
    # Ảnh chính vẫn là image_asset_id (tương thích ngược); danh sách này thêm
    # ảnh của các camera phụ khi làn có 2-3 camera. Rỗng nếu làn chỉ có 1 camera.
    images: list[ReadingImageOut] = []
    duplicate: bool = False
    # Chỉ trả khi dev_mode bật, để màn Trạm cổng hiện thời gian từng giai đoạn
    # và tài nguyên tiêu thụ.
    timings_ms: dict[str, float] | None = None
    resources: dict[str, float] | None = None
