# Phase 6: Đóng gói Podman và edge worker

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** đóng gói backend cộng PostgreSQL cộng job xóa cộng edge worker giả lập thành image, chạy full stack trên PC bằng `podman compose`, và build được image edge worker cho Pi (arm64).

**Architecture:** image backend chạy migration rồi seed admin rồi uvicorn qua entrypoint. `compose.yaml` chạy `db`, `backend`, `retention` (chạy job xóa định kỳ), thêm profile `edge` cho edge worker giả lập và profile `frontend` cho UI khi có. Khóa và mật khẩu nạp từ file `.env` ngoài repo. Volume giữ dữ liệu Postgres và thư mục ảnh mã hóa để job xóa và ảnh vẫn đúng khi rebuild.

**Tech Stack:** Podman, podman compose, Containerfile, podman build cộng manifest (multi-arch), PostgreSQL 16, python:3.11-slim, uvicorn.

## Global Constraints

Xem `2026-08-22-dashboard-mvp-plan-index.md`. Riêng phase này: khóa và mật khẩu từ env ngoài repo không bake vào image không commit; volume riêng cho Postgres và ảnh mã hóa; job xóa chạy định kỳ; commit chờ người dùng; phase khép bằng acceptance smoke.

## Ghi chú Podman

- `podman` là CLI tương thích: `podman build`, `podman run`, `podman exec`, `podman ps` thay `docker`.
- Compose: dùng `podman compose` (wrapper tích hợp của podman v4 trở lên). Nếu môi trường chưa có, cài `podman-compose` và thay `podman compose` bằng `podman-compose` trong mọi lệnh.
- Podman đọc `Containerfile` mặc định, và `.containerignore` cho ngữ cảnh build.
- Multi-arch: `podman build --platform` cộng `--manifest` thay cho `docker buildx`.

## Interfaces Phase 1 tới 5 dùng lại

- `app.main:app`, `app.config.settings`, `app.db.SessionLocal`, `app.models.User`, `app.security.passwords.hash_password`.
- `alembic upgrade head` (Phase 1), `scripts/run_retention.py` (Phase 5), `scripts/simulate_edge.py` (Phase 3).

## File Structure

- Create: `src/backend/app/routers/health.py` endpoint `/health`.
- Modify: `src/backend/app/main.py` gắn router health.
- Modify: `src/backend/app/config.py` thêm `admin_username`, `admin_password`.
- Create: `src/backend/scripts/seed_admin.py` tạo admin đầu tiên.
- Create: `src/backend/Containerfile`, `src/backend/entrypoint.sh`, `src/backend/.containerignore`.
- Create: `src/edge/Containerfile` image edge worker giả lập (multi-arch).
- Create: `compose.yaml` (repo root).
- Create: `.env.example` (repo root), `sample_images/.gitkeep`.
- Modify hoặc Create: `.gitignore` (repo root) bổ sung `.env` và dữ liệu ảnh.
- Create: `tests/test_health.py`, `tests/test_seed_admin.py`.

---

### Task 1: Endpoint health và image backend

**Files:**
- Create: `src/backend/app/routers/health.py`
- Modify: `src/backend/app/main.py`
- Create: `src/backend/tests/test_health.py`
- Create: `src/backend/Containerfile`
- Create: `src/backend/entrypoint.sh`
- Create: `src/backend/.containerignore`

**Interfaces:**
- Produces: `GET /health` trả `{"status": "ok"}`; image `parking-backend` chạy migration rồi seed admin rồi uvicorn.

- [ ] **Step 1: Viết test thất bại cho health**

`src/backend/tests/test_health.py`:

```python
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 2: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_health.py -v`
Expected: FAIL vì route `/health` chưa có.

- [ ] **Step 3: Viết routers/health.py**

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Gắn router health vào main.py**

Thêm `health` vào import và `app.include_router(health.router)` trong `create_app()`.

- [ ] **Step 5: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 6: Viết entrypoint.sh**

`src/backend/entrypoint.sh`:

```sh
#!/bin/sh
set -e
alembic upgrade head
python -m scripts.seed_admin || true
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Chạy dạng `python -m scripts.seed_admin` (không phải `python scripts/seed_admin.py`) để `/app` nằm trên `sys.path`, nếu không `import app` báo `ModuleNotFoundError`. Ngoài ra `alembic.ini` phải để `script_location = alembic` (tương đối), không để đường dẫn tuyệt đối của host, nếu không migration trong container báo path không tồn tại.

- [ ] **Step 7: Viết .containerignore**

`src/backend/.containerignore`:

```
__pycache__/
*.pyc
.pytest_cache/
tests/
data/
*.enc
.venv/
.env
```

- [ ] **Step 8: Viết Containerfile**

`src/backend/Containerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
```

- [ ] **Step 9: Build image backend để xác minh**

Run: `podman build -t parking-backend ./src/backend`
Expected: build thành công, dòng cuối in tên image `parking-backend`.

- [ ] **Step 10: Commit (điểm mốc)**

```bash
git add src/backend/app/routers/health.py src/backend/app/main.py src/backend/tests/test_health.py src/backend/Containerfile src/backend/entrypoint.sh src/backend/.containerignore
git commit -m "feat(backend): health endpoint and backend podman image"
```

---

### Task 2: Seed admin và cấu hình env

**Files:**
- Modify: `src/backend/app/config.py`
- Create: `src/backend/scripts/seed_admin.py`
- Create: `src/backend/tests/test_seed_admin.py`
- Create: `.env.example` (repo root)
- Modify hoặc Create: `.gitignore` (repo root)

**Interfaces:**
- Produces: `settings.admin_username`, `settings.admin_password`; `seed_admin.seed_admin(db) -> bool` (tạo admin nếu có `admin_password` và chưa tồn tại); `main()` chạy qua entrypoint.

- [ ] **Step 1: Thêm trường admin vào config.py**

Trong `src/backend/app/config.py`, thêm dưới `edge_api_key`:

```python
    admin_username: str = "admin"
    admin_password: str = ""
```

- [ ] **Step 2: Viết test thất bại**

`src/backend/tests/test_seed_admin.py`:

```python
from sqlalchemy import select

from app.models import User
from scripts.seed_admin import seed_admin


def test_seed_creates_admin_once(db_session, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "admin_username", "root")
    monkeypatch.setattr(settings, "admin_password", "rootpw")

    assert seed_admin(db_session) is True
    admin = db_session.scalars(select(User).where(User.username == "root")).one()
    assert admin.role == "admin"

    assert seed_admin(db_session) is False  # idempotent


def test_seed_skips_without_password(db_session, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "admin_password", "")
    assert seed_admin(db_session) is False
```

- [ ] **Step 3: Chạy để xác nhận fail**

Run: `cd src/backend && pytest tests/test_seed_admin.py -v`
Expected: FAIL vì `scripts.seed_admin` chưa có.

- [ ] **Step 4: Viết seed_admin.py**

`src/backend/scripts/seed_admin.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.security.passwords import hash_password


def seed_admin(db: Session) -> bool:
    if not settings.admin_password:
        return False
    if db.scalars(select(User).where(User.username == settings.admin_username)).first():
        return False
    db.add(User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        role="admin",
        active=True,
    ))
    db.commit()
    return True


def main() -> None:
    db = SessionLocal()
    try:
        created = seed_admin(db)
        print("đã tạo admin" if created else "bỏ qua seed admin")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Chạy để xác nhận pass**

Run: `cd src/backend && pytest tests/test_seed_admin.py -v`
Expected: PASS cả hai test.

- [ ] **Step 6: Viết .env.example**

`.env.example` (repo root):

```
POSTGRES_USER=parking
POSTGRES_PASSWORD=parking
POSTGRES_DB=parking
DATABASE_URL=postgresql+psycopg2://parking:parking@db:5432/parking
FERNET_KEY=
HMAC_KEY=change-me-hmac-key
JWT_SECRET=change-me-jwt-secret
EDGE_API_KEY=edge-dev-key
IMAGE_STORAGE_DIR=/data/images
RETENTION_DAYS=30
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin12345
```

- [ ] **Step 7: Bổ sung .gitignore (repo root)**

Bảo đảm các dòng sau có trong `.gitignore` ở repo root (thêm nếu thiếu):

```
.env
src/backend/data/
*.enc
```

- [ ] **Step 8: Commit (điểm mốc)**

```bash
git add src/backend/app/config.py src/backend/scripts/seed_admin.py src/backend/tests/test_seed_admin.py .env.example .gitignore
git commit -m "feat(backend): admin seeding and env template"
```

---

### Task 3: podman compose cho PC (db, backend, retention)

**Files:**
- Create: `compose.yaml` (repo root)

**Interfaces:**
- Produces: dịch vụ `db` (Postgres cộng volume `pgdata`), `backend` (image từ `src/backend`, volume `images`, healthcheck `/health`), `retention` (chạy `run_retention.py` mỗi ngày, dùng chung volume `images`).

- [ ] **Step 1: Viết compose.yaml**

`compose.yaml` (repo root). Khóa `dockerfile` là khóa của compose spec (podman đọc bình thường); giá trị trỏ tới `Containerfile`:

```yaml
services:
  db:
    image: postgres:16
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    build:
      context: ./src/backend
      dockerfile: Containerfile
    env_file: .env
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

  retention:
    build:
      context: ./src/backend
      dockerfile: Containerfile
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - images:/data/images
    entrypoint: ["sh", "-c", "while true; do python -m scripts.run_retention; sleep 86400; done"]

  edge-worker:
    build:
      context: .
      dockerfile: src/edge/Containerfile
    env_file: .env
    depends_on:
      - backend
    volumes:
      - ./sample_images:/images
    profiles: ["edge"]

  frontend:
    build: ./src/frontend
    depends_on:
      - backend
    ports:
      - "5173:80"
    profiles: ["frontend"]

volumes:
  pgdata:
  images:
```

- [ ] **Step 2: Chuẩn bị .env với FERNET_KEY thật**

Run: `cp .env.example .env && python -c "from cryptography.fernet import Fernet;print('FERNET_KEY='+Fernet.generate_key().decode())"`
Sửa `.env`: dán giá trị `FERNET_KEY` vừa in vào dòng `FERNET_KEY=`.
Expected: `.env` có `FERNET_KEY` là chuỗi base64 dài, không rỗng.

- [ ] **Step 3: Dựng db và backend và retention**

Run: `podman compose up -d --build db backend retention`
Expected: ba container chạy; không lỗi build.

- [ ] **Step 4: Chờ backend healthy**

Run: `podman compose ps`
Expected: `backend` cột STATUS hiện `healthy` (chờ tối đa khoảng 30 giây; entrypoint đã chạy `alembic upgrade head` và seed admin).

- [ ] **Step 5: Kiểm tra health và migration**

Run: `curl -s localhost:8000/health && podman compose exec db psql -U parking -d parking -c "\dt"`
Expected: `{"status":"ok"}` và danh sách 8 bảng cộng `alembic_version`.

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add compose.yaml
git commit -m "feat(deploy): podman compose for db, backend and retention"
```

---

### Task 4: Image edge worker giả lập

**Files:**
- Create: `src/edge/Containerfile`
- Create: `sample_images/.gitkeep`

**Interfaces:**
- Consumes: `src/backend/scripts/simulate_edge.py`.
- Produces: image edge worker (chạy simulator, đọc `/images`, POST `backend:8000/captures`), build multi-arch được cho arm64.

- [ ] **Step 1: Viết src/edge/Containerfile**

`src/edge/Containerfile` (build context là repo root):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx

COPY src/backend/scripts/simulate_edge.py ./simulate_edge.py

# MVP dùng simulator. Trên Pi với pipeline thật: cài thêm requirements src/ml,
# copy src/ml cộng worker thật, và đổi CMD sang worker đó.
CMD ["python", "simulate_edge.py", "--images", "/images", "--backend", "http://backend:8000", "--direction", "in", "--edge-key", "edge-dev-key"]
```

- [ ] **Step 2: Tạo thư mục sample_images**

Tạo `sample_images/.gitkeep` (rỗng). Đặt vài ảnh `*.jpg` cộng sidecar `*.json` cùng tên vào đây để test (ví dụ `car1.jpg` cộng `car1.json` chứa `{"vehicle_type":"car","plates":[{"plate_text":"51F-123.45","det_conf":0.95,"ocr_conf":0.9,"plate_valid":true}]}`).

- [ ] **Step 3: Bảo đảm backend đang chạy**

Run: `podman compose up -d db backend`
Expected: `backend` healthy (như Task 3).

- [ ] **Step 4: Chạy edge worker giả lập một lượt**

Run: `podman compose --profile edge run --rm --build edge-worker`
Expected: in ra mỗi file ảnh cộng status `200` cộng đoạn JSON có `review_state`.

Lưu ý macOS: Podman trên macOS chạy VM libkrun; bind mount `./sample_images:/images` qua virtiofs có thể ném `InterruptedError` (EINTR) khi scandir, làm edge container fail ở lượt liệt kê thư mục. Trên Linux và Raspberry Pi (bind mount native) không bị. Cách lùi khi demo trên macOS: chạy simulator thẳng trên host, trỏ vào backend đã publish cổng 8000:

```
python src/backend/scripts/simulate_edge.py --images sample_images --backend http://localhost:8000 --edge-key edge-dev-key
```

- [ ] **Step 5: Xác minh capture vào backend**

Run: `curl -s localhost:8000/captures/latest`
Expected: JSON có `capture_id`, `direction` là `in`, `review_state`.

- [ ] **Step 6: Build multi-arch để xác minh arm64 (không push)**

Run: `podman build --platform linux/amd64,linux/arm64 --manifest parking-edge -f src/edge/Containerfile .`
Expected: build hai kiến trúc thành công vào manifest `parking-edge` (nếu môi trường chưa cấu hình qemu cho arm64, ghi lại là bước làm trên máy có `qemu-user-static`).

- [ ] **Step 7: Commit (điểm mốc)**

```bash
git add src/edge/Containerfile sample_images/.gitkeep
git commit -m "feat(deploy): edge worker simulator image and compose profile"
```

---

### Task 5: Dịch vụ frontend theo profile

**Files:**
- Create: `src/frontend/README.md`

**Interfaces:**
- Produces: hướng dẫn kích hoạt dịch vụ `frontend` khi UI có Containerfile; dịch vụ đã khai báo sẵn trong `compose.yaml` dưới profile `frontend`.

- [ ] **Step 1: Viết src/frontend/README.md**

`src/frontend/README.md`:

```markdown
# Frontend (React)

UI do người phụ trách tự dựng. Dịch vụ `frontend` trong `compose.yaml`
nằm dưới profile `frontend` nên `podman compose up` mặc định bỏ qua.

Khi có UI:

1. Thêm `src/frontend/Containerfile` build React tĩnh và phục vụ qua nginx cổng 80.
2. Cấu hình URL backend qua biến môi trường build (ví dụ `VITE_API_BASE=http://localhost:8000`).
3. Chạy kèm stack: `podman compose --profile frontend up -d --build frontend`.

Hợp đồng API mà UI tiêu thụ: xem Phase 3 tới 5 và spec
`docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md`.
Realtime cổng: `WS /ws/gate`, fallback `GET /captures/latest`.
```

- [ ] **Step 2: Xác minh profile mặc định không kéo frontend**

Run: `podman compose config --services`
Expected: liệt kê `db`, `backend`, `retention`, `edge-worker`, `frontend`; và `podman compose up -d` mặc định chỉ chạy `db`, `backend`, `retention` (các service không profile).

- [ ] **Step 3: Commit (điểm mốc)**

```bash
git add src/frontend/README.md
git commit -m "docs(frontend): document frontend compose profile and API contract"
```

---

### Task 6: Acceptance smoke toàn stack

Kiểm chứng deliverable cả phase: `podman compose up` chạy full stack; health ok; admin seed đăng nhập được; edge worker giả lập tạo capture; xác nhận vào ra và thống kê chạy qua HTTP thật.

**Files:**
- Create: `scripts/smoke_compose.sh` (repo root)

**Interfaces:**
- Consumes: stack đang chạy; endpoint `/health`, `/auth/login`, `/captures/latest`, `/sessions/entry`, `/sessions/exit`, `/stats`.
- Produces: script smoke in kết quả từng bước.

- [ ] **Step 1: Viết scripts/smoke_compose.sh**

`scripts/smoke_compose.sh` (repo root):

```sh
#!/bin/sh
set -e
BASE=${BASE:-http://localhost:8000}
ADMIN_USER=${ADMIN_USERNAME:-admin}
ADMIN_PASS=${ADMIN_PASSWORD:-admin12345}

echo "1. health"
curl -sf "$BASE/health"; echo

echo "2. login admin"
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "token len: ${#TOKEN}"

echo "3. tạo bảng giá o_to_con"
curl -sf -X POST "$BASE/price-rules" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"vehicle_group":"o_to_con","mode":"block","unit_price":5000,"block_minutes":60}'; echo

echo "4. capture mới nhất (từ edge worker giả lập)"
curl -sf "$BASE/captures/latest"; echo

echo "smoke xong"
```

- [ ] **Step 2: Dựng full stack cộng chạy edge một lượt**

Run: `podman compose up -d --build db backend retention && podman compose --profile edge run --rm --build edge-worker`
Expected: backend healthy; edge worker POST các ảnh trong `sample_images/` với status 200.

- [ ] **Step 3: Chạy smoke**

Run: `sh scripts/smoke_compose.sh`
Expected: bước 1 in `{"status":"ok"}`; bước 2 in `token len` lớn hơn 0; bước 3 tạo bảng giá trả JSON có `id`; bước 4 in capture mới nhất có `capture_id`.

- [ ] **Step 4: Xác nhận vòng nghiệp vụ qua HTTP thật**

Run: lấy `reading_id` từ `curl -s localhost:8000/captures/latest`, rồi
`curl -s -X POST localhost:8000/sessions/entry -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"reading_id": <id>}'`
Expected: trả session `status` là `in_lot`, chứng minh backend cộng DB cộng auth chạy trong Podman.

- [ ] **Step 5: Hạ stack**

Run: `podman compose down`
Expected: các container dừng; volume `pgdata` và `images` vẫn còn (không dùng cờ `-v`).

- [ ] **Step 6: Commit (điểm mốc)**

```bash
git add scripts/smoke_compose.sh
git commit -m "test(deploy): compose smoke script for full stack"
```

---

## Self-Review (đã chạy khi soạn plan)

- **Spec coverage phase 6 (mục 12 spec Podman):** container hóa backend, db, frontend, edge worker phủ Task 1 và 3 và 4 và 5; compose PC phủ Task 3; volume Postgres và ảnh mã hóa phủ Task 3; khóa và mật khẩu từ env ngoài repo không bake image phủ Task 2 (`.env` gitignore, `.env.example` mẫu); healthcheck và chờ db phủ Task 3; job xóa chạy service scheduler phủ Task 3 (`retention`); build multi-arch cho Pi phủ Task 4; phương án lùi chạy worker thật trên Pi ghi trong `src/edge/Containerfile` và README.
- **Placeholder scan:** không có bước rỗng; mọi step có file, lệnh, hoặc expected cụ thể. `frontend` là service khai báo có chủ đích dưới profile, kèm README nêu rõ điều kiện kích hoạt, không phải placeholder.
- **Type consistency:** `seed_admin(db)` khớp giữa script, entrypoint, test; tên service và volume (`db`, `backend`, `retention`, `edge-worker`, `frontend`, `pgdata`, `images`) dùng nhất quán trong compose và các lệnh verify; `IMAGE_STORAGE_DIR=/data/images` khớp mount volume `images` ở backend và retention; `EDGE_API_KEY=edge-dev-key` khớp `--edge-key` trong edge Containerfile.
- **Ghi chú:** acceptance phase này là smoke tích hợp qua Podman (không phải pytest) vì kiểm chứng đóng gói và mạng nội bộ; các test đơn vị `/health` và `seed_admin` vẫn nằm trong suite pytest. Nếu môi trường dùng `podman-compose` thay `podman compose`, thay từ khóa lệnh tương ứng.

## Kết thúc

Sáu phase hoàn tất bao trọn spec `2026-08-21-dashboard-mvp-ai-integration-design.md` phần backend, logic, edge, Podman. Frontend React do người phụ trách dựng song song, tiêu thụ hợp đồng API từ Phase 3 tới 5 và realtime `WS /ws/gate`.
