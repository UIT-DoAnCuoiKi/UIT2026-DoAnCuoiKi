# Podman Full Stack ML Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng gói full stack lên podman sao cho backend chạy detect thật (`src/ml`) và teammate `clone → compose up --build` là chạy giống nhau.

**Architecture:** Gộp ML in process vào backend (không tách microservice). Image backend build từ context repo root, giữ layout `src/backend` + `src/ml` cạnh nhau để path resolve đúng, cài `requirements.txt` + `requirements-ml.txt`. Weights detector `.pt` commit vào git (whitelist). `.dockerignore` ở repo root để context không nuốt node_modules/.git/output (tránh OOM đọc context trên VM libkrun).

**Tech Stack:** Podman + compose, Python 3.11, FastAPI, ultralytics/torch + onnxruntime, PostgreSQL 16.

## Global Constraints

- Detect service KHÔNG xây mới. Tái dùng `src/backend/app/services/ml_inference.py` → `src/ml/pipeline/onnx_pipeline.py` (`OnnxAlprPipeline`).
- Giữ default `settings.inference_engine` là `fake` (suite test backend chạy không torch). Chỉ deploy đặt `INFERENCE_ENGINE=ml` qua env.
- Layout image bắt buộc: `ml_inference.py` ở `/app/src/backend/app/services/` để `_ML_DIR = parents[3]/"ml"` ra `/app/src/ml`. `predict_vehicle.py` cần `REPO_ROOT=/app` để `WEIGHTS_DIR=/app/src/ml/weights`.
- Chỉ commit 2 file `.pt` inference nhỏ (`yolov8n.pt`, `plate-detector.pt`). KHÔNG commit `.pt` training/checkpoint lớn.
- Văn bản UI/tài liệu tiếng Việt, không dùng ký tự gạch ngang (`-`, `–`, `—`) làm dấu câu; giữ mã/đường dẫn/biển số nguyên trạng.
- Env ML tất định trong image: `ML_PLATE_WEIGHTS=/app/src/ml/weights/plate-detector.pt`, `ML_OCR_ONNX=/app/src/ml/weights/plate-ocr-crnn.onnx`, `ML_STYLE_ONNX=/app/src/ml/weights/vehicle-style-resnet18.onnx`, `ML_STYLE_CLASSES=/app/src/ml/data/vehicle-style-classes.json`.
- Không auto commit khi thực thi (rule dự án): các bước "Commit" = stage rồi để người dùng tự commit, trừ khi được yêu cầu rõ.

---

## File Structure

- `.gitignore` (modify) — whitelist 2 file `.pt` inference.
- `src/ml/weights/plate-detector.pt` (create, binary copy) — detector chuẩn yolov8n_s0 (mAP50 0.9892).
- `src/ml/weights/yolov8n.pt` (track) — xe thô, đã có trên disk, đang bị ignore.
- `.dockerignore` (create, repo root) — loại node_modules/.git/output/datasets khỏi build context.
- `src/backend/Containerfile` (rewrite) — gộp backend + src/ml + requirements-ml.
- `compose.yaml` (modify) — backend + retention context `.`, thêm env ML_*.
- `.env.example` (modify) — FERNET dev chạy được + 4 biến ML_*.
- `src/backend/scripts/gen_secrets.py` (create) — sinh FERNET/HMAC/JWT.
- `src/backend/tests/test_ml_pipeline_smoke.py` (create) — smoke `OnnxAlprPipeline`, mark `slow`.
- `README.md` (modify hoặc create mục) — quick start teammate.

---

## Task 1: Commit weights detector (whitelist)

**Files:**
- Create: `src/ml/weights/plate-detector.pt` (copy nhị phân)
- Modify: `.gitignore`

**Interfaces:**
- Produces: 2 file weights trong git tại `src/ml/weights/yolov8n.pt` và `src/ml/weights/plate-detector.pt`; `ML_PLATE_WEIGHTS` sẽ trỏ file thứ hai.

- [ ] **Step 1: Copy detector chuẩn ra path phẳng**

```bash
cp "src/ml/plate_detection_pipeline/output/plate_det_results_20260812_2212/runs/yolov8n_s0_640/weights/best.pt" \
   src/ml/weights/plate-detector.pt
ls -l src/ml/weights/plate-detector.pt src/ml/weights/yolov8n.pt
```
Expected: cả hai file tồn tại, mỗi file vài MB.

- [ ] **Step 2: Whitelist 2 file trong .gitignore**

Thêm ngay SAU dòng `src/ml/weights/*.pt` trong `.gitignore`:

```gitignore
src/ml/weights/*.pt
# whitelist đúng 2 file inference nhỏ để teammate clone là có (build from source)
!src/ml/weights/yolov8n.pt
!src/ml/weights/plate-detector.pt
```

- [ ] **Step 3: Xác nhận git không còn ignore 2 file**

Run:
```bash
git check-ignore src/ml/weights/yolov8n.pt src/ml/weights/plate-detector.pt; echo "rc=$?"
```
Expected: không in path nào, `rc=1` (nghĩa là KHÔNG bị ignore).

- [ ] **Step 4: Stage + commit**

```bash
git add .gitignore src/ml/weights/yolov8n.pt src/ml/weights/plate-detector.pt
git commit -m "chore(ml): commit inference detector weights (yolov8n + plate-detector)"
```

---

## Task 2: ML backend Containerfile + dockerignore + compose

**Files:**
- Create: `.dockerignore` (repo root)
- Rewrite: `src/backend/Containerfile`
- Modify: `compose.yaml`

**Interfaces:**
- Consumes: weights committed từ Task 1; `requirements-ml.txt` (đã có ở `src/backend/`).
- Produces: image backend chứa `ultralytics/onnxruntime/torch` + `/app/src/ml`; compose dựng backend/retention từ context repo root với env ML_*.

- [ ] **Step 1: Tạo .dockerignore ở repo root**

Tạo `.dockerignore` (áp cho cả build backend lẫn edge, đều context `.`; chỉ loại thứ KHÔNG service nào cần):

```dockerignore
.git
.venv
**/__pycache__
**/*.pyc
**/node_modules
src/frontend
docs
report
*.md
src/ml/notebooks
src/ml/plate_detection_pipeline/output
src/ml/plate_detection_pipeline/notebooks
src/ml/checkpoints
src/ml/data/raw
data
testimage
```

Note: loại `src/ml/plate_detection_pipeline/output` nên default deep path của detector không vào image; đó là lý do Task 1 copy ra `weights/plate-detector.pt` và ta set `ML_PLATE_WEIGHTS` trỏ file phẳng.

- [ ] **Step 2: Rewrite src/backend/Containerfile (gộp ML)**

Thay toàn bộ nội dung `src/backend/Containerfile`:

```dockerfile
# Build context = repo root (compose đặt context: .), giữ layout src/backend + src/ml
# cạnh nhau trong image để path resolve đúng (xem Global Constraints).
FROM python:3.11-slim

WORKDIR /app

# libpq5: psycopg2 runtime. libgl1 + glib: opencv (ultralytics kéo theo) runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Cài deps backend + ML (torch/ultralytics/onnxruntime/scikit-learn/pandas).
COPY src/backend/requirements.txt src/backend/requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt

# Giữ layout repo trong image.
COPY src/backend ./src/backend
COPY src/ml ./src/ml

WORKDIR /app/src/backend
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
```

- [ ] **Step 3: Cập nhật compose.yaml (backend + retention)**

Trong `compose.yaml`, đổi khối `backend`:
- `build.context` từ `./src/backend` sang `.`
- thêm `build.dockerfile: src/backend/Containerfile`
- thêm 4 biến ML_* vào `environment` (bổ sung cạnh `env_file`)

```yaml
  backend:
    build:
      context: .
      dockerfile: src/backend/Containerfile
    env_file: .env
    environment:
      ML_PLATE_WEIGHTS: /app/src/ml/weights/plate-detector.pt
      ML_OCR_ONNX: /app/src/ml/weights/plate-ocr-crnn.onnx
      ML_STYLE_ONNX: /app/src/ml/weights/vehicle-style-resnet18.onnx
      ML_STYLE_CLASSES: /app/src/ml/data/vehicle-style-classes.json
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - images:/data/images
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Và khối `retention` đổi `build`:

```yaml
  retention:
    build:
      context: .
      dockerfile: src/backend/Containerfile
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - images:/data/images
    entrypoint: ["sh", "-c", "while true; do python -m scripts.run_retention; sleep 86400; done"]
```

- [ ] **Step 4: Bump tài nguyên máy libkrun (torch nặng) trước khi build**

Run:
```bash
podman machine set --memory 4096 --cpus 4
podman machine stop && podman machine start
```
Expected: máy khởi động lại thành công (reset overlay + đủ RAM cho pip torch).

- [ ] **Step 5: Build thử image backend (native buildah, không pipe)**

Run:
```bash
podman build -t uit-backend-ml-check:latest -f src/backend/Containerfile . ; echo "EXIT=$?"
```
Expected: `EXIT=0`, log có `Successfully tagged`. Nếu OOM/hết disk: tăng `--memory`/nới disk rồi build lại.

- [ ] **Step 6: Xác nhận ML deps + src/ml trong image**

Run:
```bash
podman run --rm --entrypoint sh uit-backend-ml-check:latest -c \
  'python -c "import ultralytics, onnxruntime; print(\"ML OK\")" && ls /app/src/ml/weights/plate-detector.pt'
```
Expected: in `ML OK` và path `/app/src/ml/weights/plate-detector.pt`.

- [ ] **Step 7: Stage + commit**

```bash
git add .dockerignore src/backend/Containerfile compose.yaml
git commit -m "feat(deploy): ML-capable backend image (context root, src/ml, requirements-ml)"
```

---

## Task 3: .env.example chạy được + gen_secrets

**Files:**
- Modify: `.env.example`
- Create: `src/backend/scripts/gen_secrets.py`

**Interfaces:**
- Produces: `.env.example` sao chép ra `.env` là backend boot được (FERNET hợp lệ) và ML tất định; script in 3 khóa.

- [ ] **Step 1: Tạo scripts/gen_secrets.py**

Tạo `src/backend/scripts/gen_secrets.py`:

```python
"""Sinh khóa bí mật cho .env (FERNET/HMAC/JWT). Dùng cho ai muốn khóa riêng;
giá trị dev mặc định đã có sẵn trong .env.example để chạy demo ngay."""
import secrets

from cryptography.fernet import Fernet


def main() -> None:
    print("FERNET_KEY=" + Fernet.generate_key().decode())
    print("HMAC_KEY=" + secrets.token_urlsafe(32))
    print("JWT_SECRET=" + secrets.token_urlsafe(32))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sinh FERNET dev hợp lệ cho .env.example**

Run:
```bash
cd src/backend && python -m scripts.gen_secrets ; cd ../..
```
Expected: in 3 dòng. Lấy giá trị `FERNET_KEY=...` cho bước sau.

- [ ] **Step 3: Cập nhật .env.example**

Trong `.env.example`: điền `FERNET_KEY` bằng giá trị vừa sinh (bỏ trống sẽ làm backend crash), và thêm 4 biến ML_* ở cuối. Kết quả các dòng liên quan:

```dotenv
FERNET_KEY=<dán giá trị Fernet vừa sinh ở Step 2>
HMAC_KEY=dev-hmac-key-doi-khi-len-that
JWT_SECRET=dev-jwt-secret-doi-khi-len-that
...
INFERENCE_ENGINE=ml
# Đường dẫn model trong image backend (khớp COPY src/ml -> /app/src/ml)
ML_PLATE_WEIGHTS=/app/src/ml/weights/plate-detector.pt
ML_OCR_ONNX=/app/src/ml/weights/plate-ocr-crnn.onnx
ML_STYLE_ONNX=/app/src/ml/weights/vehicle-style-resnet18.onnx
ML_STYLE_CLASSES=/app/src/ml/data/vehicle-style-classes.json
```

- [ ] **Step 4: Xác nhận FERNET_KEY hợp lệ**

Run:
```bash
python -c "from cryptography.fernet import Fernet; import os; \
v=[l.split('=',1)[1].strip() for l in open('.env.example') if l.startswith('FERNET_KEY=')][0]; \
Fernet(v.encode()); print('FERNET OK')"
```
Expected: in `FERNET OK` (không ném exception).

- [ ] **Step 5: Stage + commit**

```bash
git add .env.example src/backend/scripts/gen_secrets.py
git commit -m "chore(deploy): dev-working .env.example (valid FERNET + ML paths) and gen_secrets"
```

---

## Task 4: Deploy stack + nghiệm thu detect thật

**Files:**
- Create: `src/backend/tests/test_ml_pipeline_smoke.py`

**Interfaces:**
- Consumes: image từ Task 2, env từ Task 3, weights từ Task 1.
- Produces: bằng chứng `/captures/infer` trả biển thật; test smoke `slow` cho `OnnxAlprPipeline`.

- [ ] **Step 1: Chuẩn bị .env và dựng stack**

Run:
```bash
cp .env.example .env
podman compose --profile frontend up --build -d ; echo "EXIT=$?"
```
Expected: `EXIT=0`, các container backend/db/retention/frontend Started.

- [ ] **Step 2: Chờ backend healthy**

Run:
```bash
for i in $(seq 1 40); do c=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health); \
[ "$c" = "200" ] && { echo "healthy@${i}s"; break; }; sleep 1; done
```
Expected: in `healthy@Ns`.

- [ ] **Step 3: Nghiệm thu /captures/infer trả biển thật (KHÔNG 500, KHÔNG 51F12345)**

Run:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin12345"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
IMG=$(ls testimage/*.jpg testimage/*.png sample_images/*.jpg 2>/dev/null | head -1)
echo "img=$IMG"
curl -s -X POST http://localhost:8000/captures/infer -H "Authorization: Bearer $TOKEN" \
  -F "direction=in" -F "file=@$IMG" | python3 -m json.tool
```
Expected: HTTP JSON có `plates` với `plate_text` là biển thật đọc từ ảnh (ví dụ dạng `51A-...`), KHÁC hằng số `51F12345`. Nếu 500: xem `podman logs uit2026-doancuoiki-backend-1` (thường thiếu weight path hoặc import).

- [ ] **Step 4: Viết test smoke OnnxAlprPipeline (mark slow)**

Tạo `src/backend/tests/test_ml_pipeline_smoke.py`:

```python
"""Smoke test pipeline ONNX thật. Cần weights + torch/onnxruntime nên đánh dấu
`slow`, KHÔNG chạy trong suite mặc định. Chạy: pytest -m slow."""
import sys
from pathlib import Path

import pytest

_ML_DIR = Path(__file__).resolve().parents[2] / "ml"


@pytest.mark.slow
def test_onnx_pipeline_reads_a_plate():
    cv2 = pytest.importorskip("cv2")
    pytest.importorskip("ultralytics")
    if str(_ML_DIR) not in sys.path:
        sys.path.insert(0, str(_ML_DIR))
    from pipeline.onnx_pipeline import OnnxAlprPipeline

    samples = sorted((Path(__file__).resolve().parents[3] / "testimage").glob("*"))
    samples = [p for p in samples if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    assert samples, "cần ít nhất một ảnh mẫu trong testimage/"

    pipeline = OnnxAlprPipeline()
    result = pipeline.run(cv2.imread(str(samples[0])))
    assert isinstance(result, dict)
    assert "plates" in result
```

- [ ] **Step 5: Đăng ký marker `slow` (nếu chưa có) và chạy thử**

Kiểm `src/backend/pyproject.toml` hoặc `pytest.ini` có marker `slow`; nếu chưa, thêm vào `[tool.pytest.ini_options]` (hoặc file ini) dòng:

```toml
markers = ["slow: test cần model/torch, không chạy mặc định"]
```

Run (chỉ smoke, cần weights + torch trong venv host; nếu host không có torch thì SKIP qua importorskip):
```bash
cd src/backend && .venv/bin/pytest -m slow tests/test_ml_pipeline_smoke.py -v ; cd ../..
```
Expected: PASS nếu host có torch/weights, hoặc SKIP nếu thiếu (importorskip). Không FAIL.

- [ ] **Step 6: Regression suite mặc định vẫn xanh (engine fake, không slow)**

Run:
```bash
cd src/backend && .venv/bin/pytest -q -m "not slow" ; cd ../..
```
Expected: PASS toàn bộ (không đổi so với trước).

- [ ] **Step 7: Stage + commit**

```bash
git add src/backend/tests/test_ml_pipeline_smoke.py src/backend/pyproject.toml
git commit -m "test(ml): slow smoke for OnnxAlprPipeline; deploy verified real infer"
```

---

## Task 5: README quick start cho teammate

**Files:**
- Modify: `README.md` (root; nếu chưa có mục, thêm)

**Interfaces:**
- Produces: hướng dẫn để teammate dựng stack chạy AI giống hệt.

- [ ] **Step 1: Thêm mục "Chạy full stack (podman)" vào README.md**

Thêm mục (tiếng Việt, không gạch ngang làm dấu câu):

```markdown
## Chạy full stack trên Podman (có AI thật)

Yêu cầu: podman + podman compose. macOS chạy VM libkrun nên cần cấp đủ RAM cho torch.

1. Clone repo (weights inference đã kèm sẵn trong git).
2. macOS cấp tài nguyên cho VM:
   `podman machine set --memory 4096 --cpus 4 && podman machine stop && podman machine start`
3. Tạo cấu hình: `cp .env.example .env` (giá trị dev đã chạy được ngay).
4. Dựng: `podman compose --profile frontend up --build -d`
   Lần đầu build torch lâu (5 tới 15 phút).
5. Mở `http://localhost:5173`, đăng nhập `admin` / `admin12345`, vào Trạm cổng,
   bấm Chụp từ webcam để thấy biển số nhận dạng thật.

Sự cố thường gặp:
- Build treo không tiến triển: máy libkrun chạy lâu bị hỏng overlay.
  `podman machine stop && podman machine start` rồi build lại.
- Cài torch bị kill (OOM): tăng `--memory` (6144) và nới disk cho máy.
- Đừng pipe lệnh compose qua `tail` khi cần exit code thật.

Đường edge (Raspberry Pi) tách riêng, dùng profile `edge` và camera GPIO trên Pi,
không dựng trên máy dev.
```

- [ ] **Step 2: Stage + commit**

```bash
git add README.md
git commit -m "docs: podman full stack quick start for teammates"
```

---

## Self-Review Notes

- **Spec coverage:** Mục 1 Containerfile → Task 2. Mục 2 compose → Task 2. Mục 3 weights → Task 1 (+ env ở Task 2/3). Mục 4 .env/secrets → Task 3. Mục 5 quy trình teammate → Task 5 (+ bump máy Task 2). Mục 6 edge → giữ nguyên, tài liệu ở Task 5. Acceptance → Task 4.
- **Path consistency:** `ML_PLATE_WEIGHTS=/app/src/ml/weights/plate-detector.pt` khớp Task 1 (tạo file), Task 2 (COPY src/ml + env compose), Task 3 (.env.example). `_ML_DIR` layout khớp Containerfile `COPY src/backend ./src/backend` + `COPY src/ml ./src/ml`.
- **Placeholder:** FERNET_KEY của .env.example sinh runtime ở Task 3 Step 2 rồi dán (bí mật không hardcode được); mọi bước khác có lệnh/code cụ thể.
- **Rủi ro đã tính:** context repo root → `.dockerignore` (Task 2 Step 1) tránh OOM đọc context; torch nặng → bump máy (Task 2 Step 4).
- **Điểm cần kiểm đã xử:** `predict_vehicle` nạp `yolov8n.pt` từ `WEIGHTS_DIR=/app/src/ml/weights` (verified); style classes json đã commit (verified); entrypoint chạy từ `WORKDIR /app/src/backend` (Task 2 Step 2).
