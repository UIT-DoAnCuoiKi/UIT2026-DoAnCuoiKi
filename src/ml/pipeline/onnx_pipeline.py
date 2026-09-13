"""Runner suy luận ALPR chạy model thật (ONNX + YOLO), nguồn sự thật dùng chung
cho backend (`app/services/ml_inference.py`) và edge worker (`src/edge/worker.py`).

Chạy 4 model đã huấn luyện ở src/ml trên một khung ảnh BGR:

  1. Phát hiện biển số: YOLO `.pt` qua ultralytics (`PlateDetector`).
  2. OCR biển số:       CRNN `.onnx` qua onnxruntime.
  3. Loại xe:           classifier `.onnx` qua onnxruntime (car/motorbike/truck).
  4. Kiểu dáng xe:      classifier `.onnx` qua onnxruntime (chỉ khi là "car").

Cắt vùng xe tái dùng `predict_vehicle.detect_vehicle_crop` +
`predict_vehicle.CoarseVehicleDetector` (YOLOv8n COCO, chỉ để định vị + cắt,
model này không train lại nên nhãn lớp COCO của nó chỉ giữ lại làm loại thô
cho "bus" (chưa có dữ liệu train riêng); car/motorbike/truck luôn được ghi đè
bằng model loại-xe tự huấn luyện ở bước 3, chính xác hơn hẳn trên ảnh cận cảnh
kiểu camera cổng, xem train_vehicle_type_classifier.py và
sanity_check_vehicle_type_ood.py). `CoarseVehicleDetector` có 2 backend chọn
được qua đường dẫn `coarse_weights` (đuôi `.onnx` → onnxruntime thuần, không
cần torch; mặc định `.pt` → ultralytics/torch), dùng khi triển khai thiết bị
muốn tránh phụ thuộc torch (vd Raspberry Pi). Màu biển tái dùng
`plate_color.process_plate`. Tách dòng + chuẩn hoá biển tái dùng
`pipeline.ocr.read_plate`.

`OnnxAlprPipeline.run(image_bgr)` trả **dict** trùng schema
`PipelinePayload`/`PlateItem` (bỏ khoá `file`), nên:

  - Backend: `PipelinePayload.model_validate(dict)`.
  - Edge:    `json.dumps(dict)` gửi field `payload` của `POST /captures`.

Các import nặng (torch, cv2, onnxruntime, cây src/ml) nằm trong hàm khởi tạo để
môi trường không có model vẫn import được module. Bản `.pt` cho OCR/classifier
không có trong repo (chỉ có bản `.onnx` đã export), nên runner chạy thẳng `.onnx`
thay vì `torch.load`, dùng đúng model đã train.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Cây src/ml suy từ vị trí file: .../src/ml/pipeline/onnx_pipeline.py
_ML_DIR = Path(__file__).resolve().parents[1]

_DEFAULTS = {
    "coarse_weights": _ML_DIR / "weights" / "yolov8n.pt",
    "plate_weights": _ML_DIR / "weights" / "plate-detector.pt",  # cùng file compose.yaml dùng
    "ocr_onnx": _ML_DIR / "weights" / "plate-ocr-crnn.onnx",
    "type_onnx": _ML_DIR / "weights" / "vehicle-type-resnet18.onnx",
    "type_classes": _ML_DIR / "data" / "vehicle-type-classes.json",
    # MobileNetV3-Small thay ResNet18: accuracy ngang (0,9007 so với 0,8997 trên test),
    # nhẹ hơn 7 lần. Bản ONNX khớp .pt 987/987 ảnh test
    # (experiments/style_mobilenet_onnx_parity.json).
    "style_onnx": _ML_DIR / "weights" / "vehicle-style-mobilenet_v3_small.onnx",
    "style_classes": _ML_DIR / "data" / "vehicle-style-classes.json",
}


def encode_crop_b64(crop_bgr) -> str:
    """PNG-encode a BGR crop to a base64 ascii string. Returns "" on failure."""
    import base64

    import cv2

    if crop_bgr is None:
        return ""
    ok, buf = cv2.imencode(".png", crop_bgr)
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _ensure_ml_path() -> None:
    """Đưa các gói con của src/ml lên sys.path (giống e2e_pipeline_test)."""
    for p in (
        _ML_DIR,                                # pipeline/, predict_vehicle.py
        _ML_DIR / "training",                   # ocr_model.py, classifier.py
        _ML_DIR / "plate_detection_pipeline",   # gói plate_detect
        _ML_DIR / "plate_color_pipeline",       # gói plate_color
    ):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


def _intra_op_threads() -> int:
    """Số luồng intra-op cho mỗi session ONNX + torch (YOLO coarse, torchvision
    transform) trong pipeline. Đọc từ biến môi trường `ML_INTRAOP_THREADS`,
    mặc định 1.

    Pipeline nạp đồng thời 4-5 backend nhỏ (YOLO coarse qua torch, detector biển,
    OCR, loại xe, kiểu dáng) và chạy TUẦN TỰ trên 1 ảnh, không phải theo lô. Mỗi
    `ort.InferenceSession`/torch mặc định tự phân luồng theo toàn bộ số lõi logic
    máy; 4-5 session cùng làm vậy trên 1 ảnh nhỏ khiến chi phí đồng bộ hoá luồng
    vượt xa thời gian tính toán thật, đo thực tế trên máy dev 24 lõi logic: mặc
    định pipeline tốn CPU-time ~21 GIÂY cho 1 ảnh trong ~0.9 giây đồng hồ tường.
    Ép **1** luồng/session đưa 1 ảnh từ ~900ms xuống ổn định ~145ms (~6 lần) và
    là lựa chọn AN TOÀN trên mọi máy, kể cả Raspberry Pi 4/5 lõi (mục tiêu triển
    khai Edge của đồ án), nơi việc chia luồng còn dễ phản tác dụng hơn nữa.

    Trên máy nhiều lõi (>= ~16), tăng biến này lên 4-5 còn nhanh hơn nữa (đo
    được ~70ms/ảnh với 4-5 luồng/session trên máy dev 24 lõi, so với ~145ms ở 1
    luồng) vì mỗi model nhỏ vẫn tận dụng được vài lõi thay vì hoàn toàn đơn
    luồng, nhưng con số tối ưu phụ thuộc số lõi máy chạy thật, không hard-code
    được 1 giá trị đúng cho mọi nơi, nên để mặc định an toàn (1) và cho chỉnh
    qua biến môi trường thay vì đoán.
    """
    import os

    try:
        return max(1, int(os.environ.get("ML_INTRAOP_THREADS", "1")))
    except ValueError:
        return 1


def _process_ram_mb() -> float | None:
    """RAM tiến trình đang chiếm (MB). Trả None nếu không đọc được.

    Ưu tiên /proc (Linux, không cần thư viện ngoài, đúng nơi triển khai Pi), lùi
    về psutil cho Windows lúc phát triển. Không cài thêm phụ thuộc chỉ vì việc
    hiển thị phụ này.
    """
    try:
        with open("/proc/self/status", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / 1e6, 1)
    except Exception:
        return None


def _single_threaded_session_options():
    import onnxruntime as ort

    n = _intra_op_threads()
    so = ort.SessionOptions()
    so.intra_op_num_threads = n
    so.inter_op_num_threads = 1
    return so


class _OnnxCRNNRecognizer:
    """OCR biển số 1 dòng bằng CRNN `.onnx`. Cùng interface
    `recognize(image_bgr) -> (text, confidence)` với `pipeline.ocr.CRNNRecognizer`
    nên dùng chung được `read_plate` (tách dòng biển 2 hàng, chuẩn hoá). Tái dùng
    `decode_greedy` + charset từ `training/ocr_model.py` để khớp đúng bản đã train.
    """

    def __init__(self, onnx_path: str) -> None:
        import numpy as np
        import onnxruntime as ort
        import torch

        from ocr_model import IMG_HEIGHT, IMG_WIDTH, decode_greedy

        self._np = np
        self._torch = torch
        self._decode_greedy = decode_greedy
        self._h, self._w = IMG_HEIGHT, IMG_WIDTH
        self._sess = ort.InferenceSession(
            onnx_path, sess_options=_single_threaded_session_options(), providers=["CPUExecutionProvider"]
        )
        self._input_name = self._sess.get_inputs()[0].name

    def recognize(self, image_bgr):
        import cv2

        np = self._np
        img = cv2.resize(image_bgr, (self._w, self._h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        x = gray[None, None, :, :]  # (1, 1, H, W)
        logits = self._sess.run(None, {self._input_name: x})[0]  # (1, T, C)
        e = np.exp(logits - logits.max(axis=2, keepdims=True))
        probs = e / e.sum(axis=2, keepdims=True)
        confidence = float(probs.max(axis=2).mean())
        text = self._decode_greedy(self._torch.from_numpy(logits))[0]
        return text, confidence


class OnnxAlprPipeline:
    """Nạp 4 model một lần rồi chạy `run(image_bgr) -> dict` cho từng khung ảnh.

    Đường dẫn model mặc định suy từ vị trí file (src/ml/weights, output detector);
    truyền tham số ctor để ghi đè (edge worker dùng đường này). Backend đọc biến
    môi trường rồi truyền vào đây."""

    def __init__(
        self,
        coarse_weights: str | None = None,
        plate_weights: str | None = None,
        ocr_onnx: str | None = None,
        type_onnx: str | None = None,
        type_classes_path: str | None = None,
        style_onnx: str | None = None,
        style_classes_path: str | None = None,
        device: str = "cpu",
        conf: float | None = None,
    ) -> None:
        _ensure_ml_path()

        import onnxruntime as ort
        import torch

        from classifier import build_transforms
        from plate_detect.inference.plate_detector import PlateDetector
        from predict_vehicle import CoarseVehicleDetector

        # Pipeline chạy tuần tự nhiều backend nhỏ trên 1 ảnh, không theo lô;
        # torch mặc định tự phân luồng theo toàn bộ số lõi máy cho nhánh YOLO
        # coarse + torchvision transform, cộng dồn với các session ONNX bên dưới
        # gây tranh chấp luồng nghiêm trọng, xem chi tiết đo đạc trong docstring
        # _intra_op_threads(). Cùng biến môi trường ML_INTRAOP_THREADS với các
        # session ONNX để nhất quán 1 điểm chỉnh duy nhất.
        torch.set_num_threads(_intra_op_threads())

        # Backend suy theo đuôi file, giống PlateDetector/CRNNRecognizer: ".onnx"
        # -> onnxruntime thuần (không cần torch/ultralytics), còn lại -> "pt"
        # (ultralytics, mặc định, khớp hành vi cũ). Đổi sang .onnx khi triển
        # khai muốn tránh phụ thuộc torch (vd Raspberry Pi), xem docstring
        # CoarseVehicleDetector về lý do phải letterbox, không được squash-resize.
        coarse_weights = str(coarse_weights or _DEFAULTS["coarse_weights"])
        coarse_backend = "onnx" if coarse_weights.lower().endswith(".onnx") else "pt"
        coarse_kwargs = {} if conf is None else {"conf": conf}
        if coarse_backend == "onnx":
            coarse_kwargs["sess_options"] = _single_threaded_session_options()
        self._coarse_detector = CoarseVehicleDetector(coarse_weights, backend=coarse_backend, **coarse_kwargs)

        plate_weights = str(plate_weights or _DEFAULTS["plate_weights"])
        ocr_onnx = str(ocr_onnx or _DEFAULTS["ocr_onnx"])
        type_onnx = str(type_onnx or _DEFAULTS["type_onnx"])
        type_classes_path = str(type_classes_path or _DEFAULTS["type_classes"])
        style_onnx = str(style_onnx or _DEFAULTS["style_onnx"])
        style_classes_path = str(style_classes_path or _DEFAULTS["style_classes"])

        # PlateDetector mặc định backend="pt"; suy theo đuôi file (giống
        # CRNNRecognizer) để truyền .onnx thật sự chạy qua route onnxruntime,
        # không lặng lẽ rơi về route "pt" (vẫn cần torch) chỉ vì thiếu backend=.
        plate_backend = "onnx" if plate_weights.lower().endswith(".onnx") else "pt"
        det_kwargs = {} if conf is None else {"conf": conf}
        if plate_backend == "onnx":
            det_kwargs["sess_options"] = _single_threaded_session_options()
        self._plate_detector = PlateDetector(plate_weights, backend=plate_backend, **det_kwargs)
        self._ocr = _OnnxCRNNRecognizer(ocr_onnx)

        self._type_sess = None
        self._type_input = None
        self._type_classes: list[str] = []
        if Path(type_onnx).exists() and Path(type_classes_path).exists():
            self._type_sess = ort.InferenceSession(
                type_onnx, sess_options=_single_threaded_session_options(), providers=["CPUExecutionProvider"]
            )
            self._type_input = self._type_sess.get_inputs()[0].name
            with open(type_classes_path, encoding="utf-8") as fh:
                self._type_classes = json.load(fh)

        self._style_sess = None
        self._style_input = None
        self._style_classes: list[str] = []
        if Path(style_onnx).exists() and Path(style_classes_path).exists():
            self._style_sess = ort.InferenceSession(
                style_onnx, sess_options=_single_threaded_session_options(), providers=["CPUExecutionProvider"]
            )
            self._style_input = self._style_sess.get_inputs()[0].name
            with open(style_classes_path, encoding="utf-8") as fh:
                self._style_classes = json.load(fh)
        self._style_transform = build_transforms(train=False)

    def run(
        self,
        image_bgr,
        *,
        read_plate_enabled: bool = True,
        plate_color_enabled: bool = True,
        vehicle_class_enabled: bool = True,
        collect_timings: bool = False,
    ) -> dict:
        """Chạy toàn chuỗi trên 1 khung BGR, trả dict trùng schema PipelinePayload.

        Khoá cấp trên: vehicle_type, vehicle_box, vehicle_style,
        vehicle_style_conf, plates, timings_ms. Mỗi phần tử plates: bbox, layout,
        det_conf, plate_text, plate_valid, ocr_conf, color, color_conf,
        crop_proc_b64.

        Ba cờ `*_enabled` ánh xạ thẳng từ bảng feature_toggle (read_plate,
        plate_color, vehicle_class) để tắt công tắc ở màn Cấu hình là THỰC SỰ bỏ
        bước tính, không chỉ ẩn kết quả. Trên thiết bị biên đây là đòn bẩy hiệu
        năng thật: đo trên Raspberry Pi 5, tắt vehicle_class bỏ được khoảng 260ms
        trong tổng 490ms mỗi lượt.

        `read_plate_enabled=False` vẫn PHÁT HIỆN biển (để còn ảnh crop làm bằng
        chứng cho nhân viên đối chiếu) nhưng bỏ bước OCR, đúng như mô tả của công
        tắc: tắt thì màn cổng ép nhập tay.

        `collect_timings=True` thêm khoá `timings_ms` ghi thời gian từng giai
        đoạn, dùng cho chế độ dev_mode trên portal.
        """
        import time

        import cv2
        import numpy as np
        from PIL import Image

        from plate_color import process_plate
        from pipeline.ocr import read_plate
        from predict_vehicle import detect_vehicle_crop

        timings: dict[str, float] = {}

        def _mark(name: str, t0: float) -> None:
            if collect_timings:
                timings[name] = round((time.perf_counter() - t0) * 1000, 1)

        result: dict = {
            "vehicle_type": None,
            "vehicle_box": None,
            "vehicle_style": None,
            "vehicle_style_conf": None,
            "plates": [],
            "timings_ms": None,
            "resources": None,
        }
        if image_bgr is None:
            return result

        t_all0, cpu0 = time.perf_counter(), time.process_time()

        t0 = time.perf_counter()
        img_pil = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
        _mark("doi_mau", t0)

        # --- Nhánh biển số: phát hiện -> màu -> OCR, cho từng biển ---
        # Chạy trước nhánh xe vì "có đọc được biển" là bằng chứng độc lập rằng
        # trong khung hình có xe, dùng để quyết định nhánh xe bên dưới.
        t0 = time.perf_counter()
        dets = self._plate_detector.detect(image_bgr)
        _mark("phat_hien_bien", t0)

        t_color = t_ocr = 0.0
        for det in dets:
            t0 = time.perf_counter()
            appearance = process_plate(det.crop, with_color=plate_color_enabled)
            t_color += time.perf_counter() - t0

            t0 = time.perf_counter()
            if read_plate_enabled:
                reading = read_plate(appearance.crop_for_ocr, self._ocr, layout=det.cls_name)
                text, valid, ocr_conf = reading.text_display, bool(reading.valid_format), float(reading.confidence)
            else:
                text, valid, ocr_conf = "", False, 0.0
            t_ocr += time.perf_counter() - t0

            result["plates"].append({
                "bbox": [float(v) for v in det.bbox_xyxy],
                "layout": det.cls_name,
                "det_conf": float(det.conf),
                "plate_text": text,
                "plate_valid": valid,
                "ocr_conf": ocr_conf,
                # Tắt công tắc màu thì trả None chứ không phải "unknown": None là
                # "không tính", "unknown" là "có tính nhưng không nhận ra màu".
                # Lẫn hai thứ này thì nhân viên tưởng máy đọc hụt màu.
                "color": appearance.color if plate_color_enabled else None,
                "color_conf": (
                    float(appearance.color_conf)
                    if plate_color_enabled and appearance.color_conf is not None
                    else None
                ),
                "crop_proc_b64": encode_crop_b64(appearance.crop_for_ocr),
            })
        if collect_timings:
            timings["mau_bien"] = round(t_color * 1000, 1)
            timings["doc_bien_ocr"] = round(t_ocr * 1000, 1)

        # --- Nhánh xe: loại xe (model tự huấn luyện) + (nếu car) kiểu dáng ---
        # YOLO COCO chỉ còn để ĐỊNH VỊ + cắt vùng xe cho bước kiểu dáng và để
        # trả vehicle_box, không còn quyền quyết định có phân loại hay không.
        # Trước đây "YOLO không thấy xe -> bỏ qua luôn" làm mất 85/149 ảnh
        # (57%) của chính tập test model loại xe, riêng lớp motorbike mất 68%:
        # YOLOv8n COCO không train lại nên hay trượt trên ảnh cận cảnh camera
        # cổng (ảnh greenpack_1343.png bị nó đoán thành "person" 63%), trong
        # khi model loại xe chạy thẳng trên ảnh đó cho motorbike 99,9%.
        # Bỏ luôn bước định vị khi tắt phân loại xe: nó chỉ phục vụ bước kiểu
        # dáng và trả vehicle_box, không ai dùng tới nữa nếu không phân loại.
        crop_pil, det_info = (None, None)
        if vehicle_class_enabled:
            t0 = time.perf_counter()
            crop_pil, det_info = detect_vehicle_crop(img_pil, detector=self._coarse_detector)
            _mark("dinh_vi_xe", t0)
            if det_info is not None:
                result["vehicle_box"] = [float(v) for v in det_info["box"]]

        # Chỉ phân loại khi có bằng chứng thật sự có xe trong khung hình: YOLO
        # thấy xe HOẶC phát hiện được biển số. Thiếu ràng buộc này thì khung
        # hình trống cũng bị ép về 1 trong 3 lớp với độ tin cậy cao.
        #
        # Không dùng nhãn "bus" của COCO làm phương án dự phòng cho lớp xe khách
        # (model tự huấn luyện chưa có lớp này): đo trên tập test loại xe, COCO
        # gọi "bus" 2 lần thì SAI cả 2 (đều là ô tô con), một lần ở mức tin cậy
        # 0,781 nên đặt ngưỡng cũng không lọc được. Tin nhãn đó chỉ làm hỏng 2 ca
        # vốn đã đúng. Xe khách vẫn là hạn chế đã biết (xem 05-phanloai.md mục
        # 5.5); nhân viên sửa tay ở màn Trạm cổng khi thực sự gặp.
        has_vehicle = det_info is not None or bool(result["plates"])
        if vehicle_class_enabled and has_vehicle and self._type_sess is not None:
            # Chạy trên CẢ khung hình, không phải vùng crop: dữ liệu huấn luyện
            # model này là ảnh camera cổng nguyên khung (prepare_vehicle_type_dataset.py
            # copy thẳng ảnh gốc, không cắt), nên đưa ảnh nguyên vào mới đúng
            # phân phối lúc train và đúng với con số accuracy đã báo cáo.
            t0 = time.perf_counter()
            x = self._style_transform(img_pil).unsqueeze(0).numpy()
            logits = self._type_sess.run(None, {self._type_input: x})[0][0]
            e = np.exp(logits - logits.max())
            probs = e / e.sum()
            result["vehicle_type"] = self._type_classes[int(probs.argmax())]
            _mark("phan_loai_loai_xe", t0)

        # Kiểu dáng vẫn cần vùng xe đã cắt: model đó train trên ảnh B5 cắt theo
        # bbox kèm biên 10%, đưa nguyên khung hình vào sẽ lệch phân phối.
        if (
            vehicle_class_enabled
            and result["vehicle_type"] == "car"
            and det_info is not None
            and self._style_sess is not None
        ):
            t0 = time.perf_counter()
            x = self._style_transform(crop_pil).unsqueeze(0).numpy()
            logits = self._style_sess.run(None, {self._style_input: x})[0][0]
            e = np.exp(logits - logits.max())
            probs = e / e.sum()
            idx = int(probs.argmax())
            result["vehicle_style"] = self._style_classes[idx]
            result["vehicle_style_conf"] = float(probs[idx])
            _mark("phan_loai_kieu_dang", t0)

        if collect_timings:
            timings["tong"] = round(sum(timings.values()), 1)
            result["timings_ms"] = timings

            wall = time.perf_counter() - t_all0
            cpu = time.process_time() - cpu0
            res: dict[str, float] = {
                # CPU-time chia thời gian đồng hồ = số lõi dùng trung bình. Bằng
                # ~1 là chạy gần như đơn luồng; lớn hơn số lõi thật là dấu hiệu
                # toả luồng quá mức (xem docstring _intra_op_threads).
                "so_loi_dung": round(cpu / wall, 2) if wall > 0 else 0.0,
                "cpu_time_ms": round(cpu * 1000, 1),
            }
            ram = _process_ram_mb()
            if ram is not None:
                res["ram_tien_trinh_mb"] = ram
            result["resources"] = res
        return result
