# Thiết kế: Đóng gói full stack lên Podman với detect service thật (gộp backend)

- **Ngày:** 01/09/2026
- **Người phụ trách:** Lê Quang Hoài Đức (database, in/out logic, dashboard, edge deployment)
- **Tham chiếu:**
  - `docs/superpowers/specs/2026-08-31-edge-worker-real-model-design.md` (đường kiosk: FE webcam → `POST /captures/infer` → backend chạy model)
  - `src/ml/notebooks/e2e-pipeline-test.ipynb` (pipeline e2e tham chiếu)
  - `src/backend/app/services/ml_inference.py`, `src/ml/pipeline/onnx_pipeline.py` (detect service sẵn có)

## Bối cảnh và vấn đề

Cốt lõi đồ án là model đã huấn luyện (`src/ml`) chạy trong luồng thật. Backend đã có sẵn detect service in process (`ml_inference.py` bọc `OnnxAlprPipeline`, cùng logic notebook e2e). Nhưng bản deploy podman hiện tại KHÔNG chạy được AI:

1. Image backend build từ context `./src/backend`, chỉ cài `requirements.txt` → thiếu `ultralytics/onnxruntime/torch`.
2. `src/ml` (code + weights) không nằm trong image.
3. Hệ quả: `.env` đặt `INFERENCE_ENGINE=ml` nhưng `POST /captures/infer` trả **500** (kiểm chứng bằng ảnh thật).

Ngoài ra, để teammate chạy được y hệt (build from source), có blocker reproducibility: weights detector `.pt` bị `.gitignore` chặn (`git ls-files '**/*.pt'` rỗng), teammate clone về thiếu sạch detector.

Tài liệu này chốt cách đóng gói full stack lên podman sao cho: (a) backend chạy detect thật, (b) teammate `clone → compose up --build` là chạy giống nhau.

## Mục tiêu

- Một lệnh dựng cả stack chạy AI thật: `podman compose --profile frontend up --build -d` → db + backend(ML) + retention + frontend.
- `POST /captures/infer` trả biển thật (200), không còn 500 hay biển giả `51F12345`.
- Teammate clone repo là có đủ weights + cấu hình để build và chạy, không phụ thuộc tải thủ công.
- Suite test backend vẫn chạy engine `fake` (không cần torch), xanh như cũ.

## Non-goals (ngoài phạm vi)

- Không tách ML thành microservice riêng. Gộp in process trong backend cho đơn giản (quyết định đã chốt).
- Không quantize hay export ONNX cho detector biển số (thuộc tuần 7, `edge-deploy`).
- Không tối ưu tốc độ Pi, không benchmark.
- Không đưa các `.pt` training lớn (checkpoint) vào git. Chỉ 2 file inference nhỏ.
- Không dựng edge trên máy dev (macOS libkrun không có camera). Edge giữ profile riêng cho Pi.

## Kiến trúc mục tiêu

```
Trình duyệt (host, webcam getUserMedia)
  → POST /captures/infer (JPEG)
  → backend: get_inference_engine() [INFERENCE_ENGINE=ml]
  → MlInferenceEngine → OnnxAlprPipeline.run(bgr)
      detector .pt (ultralytics) + OCR .onnx + style .onnx (onnxruntime)
  → PipelinePayload → quyết định VÀO/RA
```

Camera do trình duyệt (host) truy cập, container chỉ nhận bytes ảnh → không cần thiết bị camera trong VM. Toàn bộ chạy trong podman trên cả Mac và Linux.

Đường edge/Pi (`POST /captures` payload, `X-Edge-Key`) không đổi, vẫn dùng chung `OnnxAlprPipeline`.

## Thành phần và thay đổi

### 1. Containerfile backend (gộp ML)

Đổi để image chứa cả backend lẫn `src/ml`, giữ nguyên layout repo trong image để path resolve đúng.

Ràng buộc path: `ml_inference.py` tính `_ML_DIR = Path(__file__).resolve().parents[3] / "ml"`. Vậy trong image, `ml_inference.py` phải nằm ở `/app/src/backend/app/services/` để `parents[3]/"ml"` ra `/app/src/ml`. Tức COPY giữ cây `src/backend` và `src/ml` cạnh nhau dưới `/app/src/`.

Nội dung mới (context = repo root):
- `FROM python:3.11-slim`
- cài libGL + glib (opencv runtime): `libgl1 libglib2.0-0`
- COPY `src/backend/requirements.txt` + `src/backend/requirements-ml.txt`, `pip install` cả hai
- COPY `src/backend` → `/app/src/backend`, COPY `src/ml` → `/app/src/ml`
- `WORKDIR /app/src/backend` (entrypoint, alembic, uvicorn chạy từ đây như cũ)
- `ENTRYPOINT ["./entrypoint.sh"]`

### 2. compose.yaml

- `backend` và `retention`: đổi `build.context` sang `.` (repo root), `build.dockerfile: src/backend/Containerfile`.
- Thêm env cho backend: `ML_PLATE_WEIGHTS`, `ML_OCR_ONNX`, `ML_STYLE_ONNX`, `ML_STYLE_CLASSES` trỏ path cố định trong image (mục 3).
- Retention dùng chung image (có torch nhưng không gọi ML) cho đơn giản. Chấp nhận image nặng cho retention.

### 3. Weights (reproducible)

Pin đúng 2 file inference về path ổn định, whitelist trong `.gitignore`:
- `src/ml/weights/yolov8n.pt` (xe thô, `detect_vehicle_crop`) — giữ nguyên vị trí.
- `src/ml/weights/plate-detector.pt` — copy từ detector chuẩn (yolov8n_s0, mAP50 0.9892, đúng `_DEFAULTS['plate_weights']` của `onnx_pipeline.py`) về path phẳng này.

`.gitignore`: thêm whitelist `!src/ml/weights/yolov8n.pt` và `!src/ml/weights/plate-detector.pt`. Các `.pt` khác (training/checkpoint) vẫn ignore. OCR/style `.onnx` và `src/ml/data/vehicle-style-classes.json` đã trong git.

Env tất định (đặt trong `.env.example` + compose):
- `ML_PLATE_WEIGHTS=/app/src/ml/weights/plate-detector.pt`
- `ML_OCR_ONNX=/app/src/ml/weights/plate-ocr-crnn.onnx`
- `ML_STYLE_ONNX=/app/src/ml/weights/vehicle-style-resnet18.onnx`
- `ML_STYLE_CLASSES=/app/src/ml/data/vehicle-style-classes.json`

`detect_vehicle_crop` nạp `yolov8n.pt` theo path nội bộ của `predict_vehicle`; xác nhận nó trỏ `src/ml/weights/yolov8n.pt` (nếu không, thêm env hoặc chỉnh cho tất định). Đây là điểm cần kiểm khi viết plan.

### 4. Secrets / .env

`.env.example` mang giá trị dev chạy được ngay (chỉ dev/demo, không phải production): `POSTGRES_*`, `FERNET_KEY`, `HMAC_KEY`, `JWT_SECRET`, `EDGE_API_KEY`, `ADMIN_USERNAME/PASSWORD`, `INFERENCE_ENGINE=ml`, và 4 biến `ML_*` ở mục 3. Teammate: `cp .env.example .env` là chạy.

Thêm `src/backend/scripts/gen_secrets.py`: in ra `FERNET_KEY`/`HMAC_KEY`/`JWT_SECRET` mới cho ai muốn tự sinh. Không bắt buộc cho dev.

### 5. Quy trình teammate và tài nguyên

`README` (root hoặc `src/backend/README.md`) mục "Quick start":
1. `git clone` (weights .pt đã kèm).
2. `podman machine init/start`; với macOS bump tài nguyên cho torch: `podman machine set --memory 4096 --cpus 4` (và nới disk nếu thiếu).
3. `cp .env.example .env`.
4. `podman compose --profile frontend up --build -d`.
5. Mở `http://localhost:5173`, đăng nhập, vào Trạm cổng, chụp webcam → thấy biển thật.

Ghi chú vận hành: nếu build treo (overlay rot máy chạy lâu) → `podman machine stop && start`; nếu OOM khi cài torch → tăng memory. Không pipe lệnh compose khi cần exit code thật.

### 6. Edge (Pi)

Giữ nguyên service `edge-worker` profile `edge`. Tài liệu riêng cho Pi: camera `/dev/video0` (`--device`), `EDGE_TRIGGER=gpio`, build arm64 tại chỗ. Không dựng trên máy dev. Kiosk path là đường demo AI chung cho mọi máy dev.

## Xử lý lỗi

- Thiếu weights lúc khởi tạo pipeline → `OnnxAlprPipeline` báo lỗi rõ (file not found), backend log lỗi ở lần gọi `/captures/infer` đầu; health vẫn xanh (ML nạp lazy).
- Ảnh giải mã lỗi (`cv2.imdecode` None) → trả `PipelinePayload(vehicle_type=None, plates=[])` (đã có).
- Torch OOM/hết disk khi build → tài liệu bump machine; không phải lỗi code.

## Kiểm thử và nghiệm thu

- **Acceptance:** sau `up --build`, `POST /captures/infer` với ảnh mẫu thật (`testimage/` hoặc `docs/research/assets/dataset-samples/`) trả 200 và ít nhất một biển đọc được, khác hằng số `51F12345`.
- **Regression:** `pytest` backend vẫn chạy engine `fake` (không torch), xanh như cũ (không đổi default `inference_engine`).
- **Smoke ML (opt in, mark `slow`):** test nạp `OnnxAlprPipeline` chạy trên một ảnh mẫu, assert dict đúng cấu trúc, ít nhất một biển hợp lệ. Cần weights, không chạy trong CI mặc định.

## Rủi ro

- Image backend nặng thêm ~2GB (torch). Build lâu (5 tới 15 phút) và có thể OOM/hết disk trên VM libkrun mặc định. Giảm thiểu bằng tài liệu bump machine; không phải blocker cứng trên máy đủ RAM/disk.
- Retention nặng theo (dùng chung image). Chấp nhận cho đơn giản; có thể tách image nhẹ sau nếu cần.
- Repo tăng ~12MB do commit 2 file `.pt`. Chấp nhận được.

## Điểm cần kiểm khi viết plan

- `predict_vehicle` nạp `yolov8n.pt` từ path nào (để tất định trong container).
- Vị trí file detector chuẩn `yolov8n_s0` best.pt trên disk để copy sang `plate-detector.pt`.
- `src/ml/data/vehicle-style-classes.json` đã commit chưa.
- `entrypoint.sh` chạy đúng từ `WORKDIR /app/src/backend` sau khi đổi layout.
