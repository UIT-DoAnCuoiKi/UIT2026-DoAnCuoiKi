"""Edge worker chạy model thật trên thiết bị cổng (Raspberry Pi 5).

Vòng đời: chờ tín hiệu kích hoạt ngoài (Enter dev, hoặc GPIO trên Pi) -> đọc một
khung từ camera -> chạy `OnnxAlprPipeline.run` (detector YOLO + OCR CRNN + kiểu
dáng, tất cả tại chỗ) -> POST kết quả đã suy luận về backend qua `POST /captures`
(xác thực `X-Edge-Key`, kèm ảnh JPEG + payload JSON).

Đây là đường cổng tự động, song song với đường kiosk/PC (`POST /captures/infer`,
backend chạy model). Backend KHÔNG suy luận lại: worker gửi payload đã suy luận.

Phần cứng tách sau interface (Trigger, Camera) để test không cần camera/GPIO/model.
Import nặng (cv2 ở process, OnnxAlprPipeline ở build) tách khỏi phần logic để test
nhẹ. Mục tiêu độ trễ dưới 2 giây mỗi xe (đo, không ép trong MVP).

Chạy (dev, không cần phần cứng):
  python3 src/edge/worker.py --backend http://localhost:8000 --edge-key edge-dev-key \
      --direction in --camera 0 --trigger key
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Protocol

import cv2
import httpx

log = logging.getLogger("edge.worker")


class StopWorker(Exception):
    """Tín hiệu dừng vòng lặp worker (EOF stdin, hoặc test bắn hết lần)."""


# --------------------------------------------------------------------------- #
# Trừu tượng phần cứng
# --------------------------------------------------------------------------- #
class Trigger(Protocol):
    def wait(self) -> None:
        """Chặn tới khi có một sự kiện kích hoạt (một xe). Ném StopWorker để dừng."""


class Camera(Protocol):
    def read(self) -> tuple[bool, object]:
        """Trả (ok, frame_bgr)."""

    def release(self) -> None:
        ...


class Pipeline(Protocol):
    def run(self, image_bgr) -> dict:
        ...


class KeyTrigger:
    """Chờ Enter trên stdin (dev, không cần phần cứng). EOF (Ctrl-D) -> dừng."""

    def wait(self) -> None:
        line = sys.stdin.readline()
        if line == "":  # EOF
            raise StopWorker


class GpioTrigger:
    """Chờ cạnh lên của nút/cảm biến qua `gpiozero` (Pi). Import trong ctor và
    guard ImportError để môi trường dev (không có gpiozero) báo lỗi rõ."""

    def __init__(self, pin: int) -> None:
        try:
            from gpiozero import Button
        except ImportError as exc:
            raise RuntimeError(
                "Thiếu gpiozero: trigger GPIO chỉ chạy trên Raspberry Pi. "
                "Cài gpiozero trên Pi, hoặc dùng --trigger key ở máy dev."
            ) from exc
        self._button = Button(pin)

    def wait(self) -> None:
        self._button.wait_for_press()


class OpenCvCamera:
    """Camera qua OpenCV. `source` là index (int) hoặc đường dẫn/URL (str)."""

    def __init__(self, source) -> None:
        self._cap = cv2.VideoCapture(source)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Không mở được camera nguồn={source!r}. Kiểm tra --camera "
                "(index thiết bị, đường dẫn file, hoặc URL RTSP)."
            )

    def read(self):
        return self._cap.read()

    def release(self) -> None:
        self._cap.release()


# --------------------------------------------------------------------------- #
# Gửi kết quả về backend
# --------------------------------------------------------------------------- #
class CapturePoster:
    """POST một capture đã suy luận về `POST {backend}/captures`.

    Lỗi mạng/timeout hoặc 5xx: retry `retries` lần backoff tuyến tính rồi bỏ
    (hàng đợi offline để pha sau). 4xx: lỗi cấu hình (edge-key/direction), không
    retry. Trả True nếu backend nhận."""

    def __init__(
        self, client: httpx.Client, *, backend: str, edge_key: str, direction: str,
        lane: str | None = None, retries: int = 3, backoff: float = 0.5,
        sleep=time.sleep, device_id: int | None = None,
    ) -> None:
        self._client = client
        self._base = backend.rstrip("/")
        self._url = f"{self._base}/captures"
        self._headers = {"X-Edge-Key": edge_key}
        self._direction = direction
        self._lane = lane
        self._retries = retries
        self._backoff = backoff
        self._sleep = sleep
        self._device_id = device_id

    def post(self, capture_id: str, result: dict, jpeg: bytes) -> bool:
        data = {
            "capture_id": capture_id,
            "direction": self._direction,
            "payload": json.dumps(result),
        }
        if self._lane is not None:
            data["lane"] = self._lane
        files = {"image": (f"{capture_id}.jpg", jpeg, "image/jpeg")}

        for attempt in range(1, self._retries + 1):
            try:
                resp = self._client.post(self._url, headers=self._headers, data=data, files=files)
            except httpx.HTTPError as exc:
                log.warning("POST lỗi mạng lần %d/%d: %s", attempt, self._retries, exc)
                if attempt < self._retries:
                    self._sleep(self._backoff * attempt)
                continue

            if resp.status_code < 300:
                log.info("POST ok capture_id=%s (%d)", capture_id, resp.status_code)
                self.heartbeat()
                return True
            if 400 <= resp.status_code < 500:
                log.error(
                    "POST %d (lỗi cấu hình, không retry) capture_id=%s: %s",
                    resp.status_code, capture_id, resp.text[:200],
                )
                return False
            log.warning("POST %d lần %d/%d capture_id=%s", resp.status_code, attempt, self._retries, capture_id)
            if attempt < self._retries:
                self._sleep(self._backoff * attempt)

        log.error("POST thất bại sau %d lần, bỏ capture_id=%s", self._retries, capture_id)
        return False

    def heartbeat(self) -> None:
        """Báo thiết bị còn sống sau mỗi capture gửi thành công.

        Không cấu hình --device-id thì bỏ qua. Lỗi ở đây không được ảnh hưởng
        luồng chính: heartbeat chỉ phục vụ màn hình health, hỏng thì thiết bị vẫn
        phải tiếp tục gửi capture bình thường.
        """
        if self._device_id is None:
            return
        try:
            resp = self._client.post(
                f"{self._base}/devices/{self._device_id}/heartbeat", headers=self._headers,
            )
            if resp.status_code >= 300:
                log.warning("heartbeat %d device_id=%s", resp.status_code, self._device_id)
        except httpx.HTTPError as exc:
            log.warning("heartbeat lỗi mạng device_id=%s: %s", self._device_id, exc)


# --------------------------------------------------------------------------- #
# Vòng lặp
# --------------------------------------------------------------------------- #
def process_capture(camera: Camera, pipeline: Pipeline, poster: CapturePoster) -> None:
    """Một xe: đọc frame -> suy luận -> mã hoá -> POST. Lỗi ở bước nào cũng chỉ
    bỏ capture đó, không sập worker."""
    ok, frame = camera.read()
    if not ok or frame is None:
        log.warning("camera.read ok=False, bỏ trigger này")
        return

    capture_id = uuid.uuid4().hex
    try:
        result = pipeline.run(frame)
    except Exception:
        log.exception("pipeline.run lỗi capture_id=%s, bỏ", capture_id)
        return

    ok_enc, buf = cv2.imencode(".jpg", frame)
    if not ok_enc:
        log.error("mã hoá JPEG lỗi capture_id=%s, bỏ", capture_id)
        return

    poster.post(capture_id, result, buf.tobytes())


def run_worker(trigger: Trigger, camera: Camera, pipeline: Pipeline, poster: CapturePoster) -> None:
    """Vòng lặp: mỗi lần trigger trả về = một xe. StopWorker để dừng sạch."""
    log.info("Edge worker sẵn sàng, chờ trigger...")
    while True:
        try:
            trigger.wait()
        except StopWorker:
            log.info("Nhận tín hiệu dừng, thoát vòng lặp.")
            break
        process_capture(camera, pipeline, poster)


# --------------------------------------------------------------------------- #
# Dựng thành phần thật + CLI
# --------------------------------------------------------------------------- #
def _build_pipeline(args):
    """Nạp OnnxAlprPipeline (fail fast nếu thiếu weights/deps). Import trễ để test
    worker không kéo theo cây src/ml."""
    ml_dir = Path(__file__).resolve().parents[1] / "ml"
    if str(ml_dir) not in sys.path:
        sys.path.insert(0, str(ml_dir))
    from pipeline.onnx_pipeline import OnnxAlprPipeline

    return OnnxAlprPipeline(
        plate_weights=args.plate_weights,
        ocr_onnx=args.ocr_onnx,
        style_onnx=args.style_onnx,
        style_classes_path=args.style_classes,
        conf=args.conf,
    )


def _build_trigger(args) -> Trigger:
    if args.trigger == "gpio":
        return GpioTrigger(args.gpio_pin)
    return KeyTrigger()


def _build_camera(args) -> Camera:
    source = int(args.camera) if str(args.camera).isdigit() else args.camera
    return OpenCvCamera(source)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backend", default=os.environ.get("EDGE_BACKEND", "http://localhost:8000"),
                   help="URL backend (mặc định http://localhost:8000 hoặc EDGE_BACKEND)")
    p.add_argument("--edge-key", default=os.environ.get("EDGE_API_KEY", "edge-dev-key"),
                   help="Giá trị header X-Edge-Key (hoặc EDGE_API_KEY)")
    p.add_argument("--direction", choices=("in", "out"), default=os.environ.get("EDGE_DIRECTION", "in"),
                   help="Hướng cổng: in hoặc out")
    p.add_argument("--lane", default=os.environ.get("EDGE_LANE"), help="Mã làn (tùy chọn)")
    p.add_argument("--device-id", dest="device_id", type=int,
                   default=int(os.environ["EDGE_DEVICE_ID"]) if os.environ.get("EDGE_DEVICE_ID") else None,
                   help="Id thiết bị trong bảng device, để báo heartbeat cho màn hình health (tùy chọn)")
    p.add_argument("--camera", default=os.environ.get("EDGE_CAMERA", "0"),
                   help="Nguồn camera: index thiết bị, đường dẫn file, hoặc URL RTSP")
    p.add_argument("--trigger", choices=("key", "gpio"), default=os.environ.get("EDGE_TRIGGER", "key"),
                   help="Nguồn kích hoạt: key (Enter, dev) hoặc gpio (Pi)")
    p.add_argument("--gpio-pin", type=int, default=int(os.environ.get("EDGE_GPIO_PIN", "17")),
                   help="Chân GPIO cho nút/cảm biến khi --trigger gpio")
    p.add_argument("--conf", type=float, default=None, help="Ngưỡng confidence phát hiện biển số")
    p.add_argument("--retries", type=int, default=3, help="Số lần retry POST khi lỗi mạng")
    # Ghi đè đường dẫn model (mặc định trỏ vào repo, giải trong onnx_pipeline).
    p.add_argument("--plate-weights", dest="plate_weights", default=os.environ.get("ML_PLATE_WEIGHTS"))
    p.add_argument("--ocr-onnx", dest="ocr_onnx", default=os.environ.get("ML_OCR_ONNX"))
    p.add_argument("--style-onnx", dest="style_onnx", default=os.environ.get("ML_STYLE_ONNX"))
    p.add_argument("--style-classes", dest="style_classes", default=os.environ.get("ML_STYLE_CLASSES"))
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    args = build_parser().parse_args(argv)

    # Fail fast: dựng trigger + camera + pipeline trước khi vào vòng lặp.
    try:
        trigger = _build_trigger(args)
        camera = _build_camera(args)
        pipeline = _build_pipeline(args)
    except RuntimeError as exc:
        log.error("Khởi tạo thất bại: %s", exc)
        return 2

    client = httpx.Client(timeout=10.0)
    poster = CapturePoster(
        client, backend=args.backend, edge_key=args.edge_key,
        direction=args.direction, lane=args.lane, retries=args.retries,
        device_id=args.device_id,
    )

    try:
        run_worker(trigger, camera, pipeline, poster)
    finally:
        camera.release()
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
