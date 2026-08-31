# Thiết kế: Edge worker chạy model thật (camera + trigger ngoài)

- **Ngày:** 2026-08-31
- **Người phụ trách:** Lê Quang Hoài Đức (edge deployment)
- **Tài liệu liên quan:**
  - `docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md` (mục 10-12: edge worker chứa `src/ml`, chạy thật trên Pi)
  - `docs/superpowers/specs/2026-08-23-parking-system-edge-cloud-architecture-design.md` (vị trí suy luận ML ở edge)
  - `src/ml/e2e_pipeline_test.py` (pipeline nhận dạng tham chiếu)

## 0. Bối cảnh và mục tiêu

Cốt lõi đồ án: model đã huấn luyện (`src/ml`) chạy trong luồng thật. Hiện cả hai cửa ngõ nhận diện đều là stub:

- Backend `POST /captures/infer`: mặc định `FakeInferenceEngine` trả biển cứng `51F12345` (đã sửa sang ONNX thật ở session 2026-08-30, xem `src/backend/app/services/ml_inference.py`).
- Edge worker `src/backend/scripts/simulate_edge.py`: đọc file `.json` cạnh ảnh và replay, KHÔNG chạy model. Trái spec 08-21 mục 147.

Tài liệu này chốt việc **viết lại edge worker để chạy model thật** trên thiết bị cổng (Raspberry Pi 5): đọc frame camera khi có tín hiệu kích hoạt ngoài, chạy pipeline nhận dạng đầy đủ, POST kết quả đã suy luận về backend qua `POST /captures` (đường payload, xác thực `X-Edge-Key`).

Hai đường suy luận song song, đúng spec 08-21 mục 140:

- **Kiosk/demo PC:** frontend chụp webcam → `POST /captures/infer` → backend chạy model. Đã hoạt động.
- **Cổng tự động/Pi:** edge worker chạy model tại chỗ → `POST /captures` payload. Tài liệu này.

Mục tiêu độ trễ: dưới 2 giây mỗi xe (đo, không ép trong MVP).

## 1. Non-goals (ngoài phạm vi)

- Hàng đợi offline bền vững khi mất mạng (spec 08-21 mục 133). MVP chỉ retry backoff rồi bỏ + log; hàng đợi để pha sau.
- Lượng tử hóa ONNX INT8, tối ưu tốc độ Pi (thuộc tuần 7, `edge-deploy`).
- Đấu nối phần cứng GPIO chi tiết (sơ đồ chân, cảm biến vòng từ vật lý). Chỉ định nghĩa interface trigger + hiện thực `gpiozero.Button`.
- Đa camera trên một worker. Một worker phục vụ một hướng (một camera).
- Điều khiển barie sau khi nhận diện (thuộc router `devices`/`barrier`, đã có ở backend).

## 2. Kiến trúc

Tách logic suy luận ONNX thành một runner dùng chung trong `src/ml`, để cả backend và edge worker dùng chung mà **edge không phụ thuộc `app/` của backend**.

```
                 ┌─────────────────────────────┐
                 │ src/ml/pipeline/onnx_pipeline│  (MỚI, nguồn sự thật)
                 │ OnnxAlprPipeline.run(bgr)->dict
                 └───────────┬─────────────────┘
             dùng chung      │
        ┌───────────────────┴───────────────────┐
        │                                        │
┌───────▼──────────┐                   ┌─────────▼─────────────┐
│ backend           │                   │ edge worker            │
│ ml_inference.py   │                   │ src/edge/worker.py     │
│ dict->PipelinePayload                 │ camera+trigger, dict->  │
│ (POST /captures/infer)                │ JSON POST /captures    │
└──────────────────┘                   └───────────────────────┘
```

`OnnxAlprPipeline.run` trả **dict** trùng schema `PipelinePayload`/`PlateItem` (chính là dict của `e2e_pipeline_test.run_pipeline_on_image` bỏ khóa `file`), nên:

- Backend: `PipelinePayload.model_validate(dict)` (hàm `result_to_payload` sẵn có).
- Edge: `json.dumps(dict)` gửi field `payload` của `POST /captures`; backend `model_validate_json` nhận.

## 3. Interface dùng lại từ src/ml (đã xác minh 2026-08-30)

| Hàm/lớp | Chữ ký | Trả về |
|---|---|---|
| `plate_detect.inference.plate_detector.PlateDetector(weights, backend="pt", conf, iou)` | `.detect(image_bgr)` | `list[PlateDetection(bbox_xyxy, cls_id, cls_name, conf, crop)]`, lazy-load YOLO |
| `plate_color.process_plate` | `(crop_bgr)` | `PlateAppearance(color, color_conf, color_features, lighting, crop_for_ocr)` |
| `pipeline.ocr.read_plate` | `(crop_bgr, recognizer, layout)` | `PlateReading(text_raw, text_normalized, text_display, valid_format, confidence)` |
| `predict_vehicle.detect_vehicle_crop` | `(img_pil)` | `(crop_pil, det_info | None)`; `det_info = {box, yolo_class, yolo_conf}`; dùng `weights/yolov8n.pt` |
| `training.ocr_model.decode_greedy` | `(logits: torch (B,T,C))` | `list[str]`; CHARSET 36 ký tự + blank(0); ảnh 48x128 |
| `training.classifier.build_transforms` | `(train=False)` | `transforms.Compose` cho classifier (input onnx `[1,3,224,224]`) |

Model file:

- Detector `.pt`: `src/ml/plate_detection_pipeline/output/plate_det_results_20260812_2212/runs/yolov8n_s0_640/weights/best.pt` (mAP50 0.9892).
- OCR `.onnx`: `src/ml/weights/plate-ocr-crnn.onnx` (`[1,1,48,128]->[1,32,37]`).
- Style `.onnx`: `src/ml/weights/vehicle-style-resnet18.onnx` (`[1,3,224,224]->[1,3]`).
- Style classes: `src/ml/data/vehicle-style-classes.json` (`["GamCao","Sedan","XeTai"]`).
- `yolov8n.pt` (loại thô COCO): `src/ml/weights/yolov8n.pt`.

Ghi chú: bản `.pt` cho OCR/style KHÔNG có trong repo, chỉ có `.onnx` đã export; runner chạy thẳng `.onnx` qua onnxruntime (không `torch.load`), OCR/detector tái dùng `decode_greedy`/ultralytics.

## 4. Thành phần

### 4.1 `src/ml/pipeline/onnx_pipeline.py` (MỚI)

`class OnnxAlprPipeline`:

- `__init__(plate_weights, ocr_onnx, style_onnx, style_classes_path, device="cpu")`: nạp `PlateDetector(plate_weights)`, `ort.InferenceSession(ocr_onnx)`, `ort.InferenceSession(style_onnx)` (nếu có), `build_transforms(False)`, đọc classes json. Tự chèn các gói con `src/ml` lên `sys.path` (giống `e2e_pipeline_test`).
- `run(image_bgr) -> dict`: nhánh xe (`detect_vehicle_crop` + style onnx khi `car`) + nhánh biển (`detect` → `process_plate` → `read_plate` với `_OnnxCrnnRecognizer`). Trả dict `{vehicle_type, vehicle_box, vehicle_style, vehicle_style_conf, plates:[{bbox, layout, det_conf, plate_text, plate_valid, ocr_conf, color, color_conf}]}`.
- Đường dẫn model mặc định suy từ vị trí file (`src/ml/weights`, output detector), ghi đè bằng tham số ctor.

`class _OnnxCrnnRecognizer`: `recognize(image_bgr) -> (text, conf)` cùng interface `CRNNRecognizer`; resize 128x48, gray, /255, `session.run` → softmax lấy conf → `decode_greedy(torch.from_numpy(logits))`.

Logic này bê nguyên từ `ml_inference.py` hiện tại (đã chạy thật), chỉ đổi chỗ ở và trả dict thay vì `PipelinePayload`.

### 4.2 `src/backend/app/services/ml_inference.py` (REFACTOR)

Bọc `OnnxAlprPipeline`: `get_ml_engine()` khởi tạo pipeline một lần; `MlInferenceEngine.infer(bytes)` = `cv2.imdecode` → `pipeline.run` → `result_to_payload(dict)`. Giữ nguyên `INFERENCE_ENGINE=ml`, biến env override, `result_to_payload`, và hành vi đã verify. Xoá phần onnx trùng (đã dời vào `onnx_pipeline`).

### 4.3 `src/edge/worker.py` (MỚI)

Vòng đời:

1. Khởi tạo (fail fast): mở camera `cv2.VideoCapture(--camera)`; nạp `OnnxAlprPipeline`; đọc cấu hình POST. Lỗi mở camera hoặc nạp model → thoát, báo rõ.
2. Vòng lặp: chờ `trigger.wait()`. Mỗi lần trả về = một xe.
3. Xử lý: `ok, frame = camera.read()`; grab lỗi → log, bỏ trigger đó. Chạy `pipeline.run(frame)`. Mã hóa `frame` JPEG.
4. Gửi: `POST {backend}/captures` header `X-Edge-Key`, form `capture_id=uuid4`, `direction`, `lane`, `payload=json(result)`, `image=jpeg`. POST cả khi `plates` rỗng (xe có mặt, nhân viên soát tay). Lỗi mạng → retry N lần backoff → log + bỏ.

Trừu tượng phần cứng:

- `Trigger` protocol: `wait() -> None` (chặn tới khi có sự kiện).
  - `KeyTrigger`: chờ Enter trên stdin (dev, không cần phần cứng).
  - `GpioTrigger(pin)`: `gpiozero.Button(pin).wait_for_press()` (Pi). Import `gpiozero` trong ctor, guard `ImportError` báo cần chạy trên Pi.
- `Camera` protocol: `read() -> (ok, frame_bgr)`, `release()`. Hiện thực `OpenCvCamera(source)`.

CLI/env: `--backend`, `--edge-key`, `--direction {in,out}`, `--lane`, `--camera` (index/đường dẫn), `--trigger {key,gpio}`, `--gpio-pin`, `--conf`, override đường dẫn model. Đặt default an toàn cho dev.

### 4.4 `src/edge/Containerfile` (CẬP NHẬT)

Build context `.` (repo root, compose đã đặt). Copy `src/ml` + `src/edge/worker.py`, cài `src/backend/requirements-ml.txt` (ultralytics, onnxruntime, scikit-learn, pandas). CMD chạy `worker.py`. Ghi chú lùi: Pi arm64 nặng, nếu container quá tải thì chạy worker trực tiếp trên host Pi (spec 08-21 mục 162); backend/db vẫn container.

### 4.5 `src/backend/scripts/simulate_edge.py` (GIỮ)

Không đổi. Vẫn là công cụ load-test backend không cần model/camera (replay JSON). Không còn là đường edge thật.

## 5. Luồng dữ liệu

```
trigger ngoài → camera.read() 1 frame → OnnxAlprPipeline.run(frame) → dict
  → POST /captures (X-Edge-Key, image jpeg + payload json)
  → backend require_edge_key → PipelinePayload.model_validate_json
  → ingest_reading (KHÔNG suy luận lại) → select_representative → phiên/phí/WS
```

Backend không đổi: `POST /captures` (captures.py) đã nhận payload đã suy luận. Edge chỉ thay nội dung payload từ giả sang thật.

## 6. Xử lý lỗi

| Tình huống | Hành vi |
|---|---|
| Mở camera lỗi | thoát lúc start, mã lỗi + gợi ý `--camera` |
| Nạp model lỗi (thiếu weights/deps) | thoát lúc start, chỉ file thiếu |
| `camera.read()` trả `ok=False` | log cảnh báo, bỏ trigger, chờ trigger kế |
| `pipeline.run` ngoại lệ | log lỗi kèm capture_id, bỏ, không sập worker |
| POST lỗi mạng/timeout | retry N lần (mặc định 3) backoff; hết thì log + bỏ (queue để sau) |
| POST trả 4xx (edge-key sai, direction sai) | log lỗi rõ, không retry (lỗi cấu hình) |
| `gpiozero` thiếu khi `--trigger gpio` | thoát, báo cần chạy trên Pi hoặc dùng `--trigger key` |

## 7. Kiểm thử

Tách phần cứng sau interface để test không cần camera/GPIO/model:

- `src/ml`: `test_onnx_pipeline_smoke` — `OnnxAlprPipeline.run` trên một ảnh mẫu thật (`docs/research/assets/dataset-samples/*`); assert dict đúng cấu trúc, ít nhất một biển đọc được định dạng hợp lệ. Mark `slow` (cần weights).
- `src/edge`: `test_worker_posts_inferred_payload` — inject `FakeTrigger` (bắn một lần rồi dừng), `FakeCamera` (trả frame cố định), `FakePipeline` (trả dict cố định), `httpx` mock; assert đúng URL `/captures`, header `X-Edge-Key`, form có `capture_id/direction/lane`, `payload` json khớp dict, có `image`.
- `src/edge`: `test_worker_retries_then_drops` — httpx mock ném lỗi; assert retry đúng số lần rồi không sập.
- `src/edge`: `test_gpio_trigger_missing_dep` — `--trigger gpio` khi `gpiozero` vắng → thoát báo rõ.

## 8. Khả thi (đã kiểm 2026-08-30/31)

- Toàn pipeline đã chạy end-to-end thật qua `ml_inference` ONNX: ra biển thật (`71B1-586.09`, `81AA-048.92`), `vehicle_type=car`, `style=GamCao`, infer ~0.3s sau warm. `run` chỉ là bê logic đó sang `src/ml` + trả dict.
- `cv2.VideoCapture` có trong môi trường (opencv 5.0). `X-Edge-Key` + form `/captures` xác nhận (deps.py:38, captures.py:16). `gpiozero` vắng ở dev → guard import.
- Không có phụ thuộc ngược edge→backend: runner ở `src/ml`, trả dict thuần.
