# Backend: Hệ thống quản lý bãi đỗ xe

FastAPI cộng SQLAlchemy 2.0 cộng Alembic cộng PostgreSQL. Nhận kết quả pipeline AI từ edge worker, quản lý phiên vào ra, khớp biển, tính phí, thống kê, và bảo mật (mã hóa tầng cột, JWT, audit, tự xóa theo hạn lưu trữ).

Spec: `docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md`. Kế hoạch 6 phase: `docs/superpowers/plans/2026-08-22-*`.

## Yêu cầu

- Python 3.11 trở lên (đã kiểm trên 3.13).
- Podman cộng provider compose (`docker-compose` hoặc `podman-compose`) nếu chạy bằng container.
- Hoặc PostgreSQL 16 nếu chạy cục bộ với Postgres. SQLite dùng được cho demo nhanh và test.

## Cách 1: Chạy bằng Podman (khuyến nghị, sát đồ án)

Từ thư mục gốc repo:

```sh
cp .env.example .env
# sinh FERNET_KEY và ghi vào .env
python3 -c "from cryptography.fernet import Fernet;import pathlib;p=pathlib.Path('.env');p.write_text(p.read_text().replace('FERNET_KEY=','FERNET_KEY='+Fernet.generate_key().decode()))"

podman compose up -d --build db backend retention
podman compose ps                 # chờ backend thành 'healthy'
curl -s localhost:8000/health     # {"status":"ok"}
```

Backend entrypoint tự chạy `alembic upgrade head` rồi seed admin (theo `ADMIN_USERNAME`/`ADMIN_PASSWORD`) rồi uvicorn. Mở tài liệu API ở `http://localhost:8000/docs`.

Dừng: `podman compose down` (giữ volume `pgdata` và `images`; thêm `-v` để xóa sạch dữ liệu).

## Cách 2: Chạy cục bộ không container

Từ thư mục `src/backend`:

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export FERNET_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
export HMAC_KEY=dev-hmac JWT_SECRET=dev-jwt ADMIN_PASSWORD=admin12345
```

Demo nhanh với SQLite (không cần Postgres):

```sh
export DATABASE_URL="sqlite:///./dev.db"
alembic upgrade head
python -m scripts.seed_admin      # tạo admin từ ADMIN_USERNAME/ADMIN_PASSWORD
uvicorn app.main:app --port 8000
```

Với PostgreSQL:

```sh
export DATABASE_URL="postgresql+psycopg2://parking:parking@localhost:5432/parking"
alembic upgrade head
python -m scripts.seed_admin
uvicorn app.main:app --port 8000
```

Lưu ý: chạy `python -m scripts.seed_admin` (dạng module) từ `src/backend` để `import app` thấy package; không chạy `python scripts/seed_admin.py`.

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | postgres localhost | chuỗi kết nối SQLAlchemy |
| `FERNET_KEY` | rỗng (bắt buộc set) | khóa mã hóa biển và ảnh; sinh bằng `Fernet.generate_key()` |
| `HMAC_KEY` | rỗng (bắt buộc set) | khóa HMAC để hash biển tra khớp |
| `JWT_SECRET` | change-me | khóa ký JWT |
| `JWT_EXPIRE_MINUTES` | 480 | hạn token |
| `IMAGE_STORAGE_DIR` | ./data/images | thư mục lưu ảnh mã hóa |
| `RETENTION_DAYS` | 30 | số ngày giữ dữ liệu sau khi xe ra |
| `EDGE_API_KEY` | edge-dev-key | khóa header `X-Edge-Key` cho `POST /captures` |
| `ADMIN_USERNAME` | admin | tài khoản admin seed |
| `ADMIN_PASSWORD` | rỗng | mật khẩu admin seed; rỗng thì bỏ qua seed |

Khóa nạp từ môi trường, không commit vào repo. `.env` bị gitignore.

## Test

Unit test (SQLite in memory, không cần server chạy), từ `src/backend`:

```sh
pytest -q            # 84 test
```

E2E API test (vào backend HTTP thật), cần stack đang chạy:

```sh
BASE_URL=http://localhost:8000 pytest tests_e2e -q
```

E2E nằm ngoài `testpaths` nên `pytest` thường không chạy nó. Nếu backend không lên, module e2e tự skip. E2E phủ luồng cổng đầy đủ, disputed, nhập tay, phân quyền, và edge key.

## Edge worker giả lập

Script đọc ảnh `*.jpg` trong một thư mục cộng file sidecar `*.json` (payload pipeline) rồi POST `POST /captures`.

Trên host (không cần container):

```sh
python scripts/simulate_edge.py --images ../../sample_images --backend http://localhost:8000 --edge-key edge-dev-key
```

Trong container:

```sh
podman compose --profile edge run --rm --build edge-worker
```

Mỗi ảnh cần một sidecar cùng tên, ví dụ `car1.jpg` cộng `car1.json`:

```json
{"vehicle_type": "car", "plates": [{"plate_text": "51F-123.45", "det_conf": 0.96, "ocr_conf": 0.9, "plate_valid": true, "color": "trắng"}]}
```

## Endpoint chính

- `GET /health`
- `POST /auth/login` trả JWT
- `POST /captures` (multipart, header `X-Edge-Key`), `GET /captures/latest`
- `WS /ws/gate` đẩy sự kiện nhận diện; fallback polling `GET /captures/latest`
- `POST /sessions/entry`, `POST /sessions/exit`, `POST /sessions/manual`
- `POST /sessions/{id}/dispute`, `POST /sessions/{id}/resolve`
- `GET /sessions` (lọc `plate`, `status`, phân trang), `GET /sessions/{id}`
- `PATCH /readings/{id}/plate` sửa biển tay (ghi audit)
- `GET /images/{id}` (chặn auth, ghi audit)
- `GET /stats`, `GET /stats/export` (CSV, chỉ admin)
- CRUD `/price-rules`, `/lanes`, `/feature-toggles`
- `GET/POST/PATCH /users` (chỉ admin)

Vai: `staff` làm nghiệp vụ cổng và tra cứu; `admin` thêm cấu hình, giá, tài khoản, doanh thu, CSV.

## OpenAPI và sinh client frontend (Orval)

Backend tự phát hành đặc tả OpenAPI. UI React sinh client TypeScript từ đây thay vì gõ tay endpoint:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Schema thô: `http://localhost:8000/openapi.json`

`create_app()` đặt `generate_unique_id_function` theo tên hàm handler, nên
operationId sạch (`login`, `confirm_entry`, `list_sessions`...) và Orval sinh
hook đọc được (`useLogin`, `useConfirmEntry`, `useListSessions`).

Xuất schema ra file. Hai đường:

```sh
# a) Offline, không cần chạy server (hợp CI và máy chưa mở service):
python scripts/export_openapi.py            # ghi ../frontend/openapi.json

# b) Từ backend đang chạy:
curl -s localhost:8000/openapi.json > ../frontend/openapi.json
```

Sinh client bằng Orval (https://orval.dev). Config sẵn ở `src/frontend/orval.config.ts`
(client `react-query`, `mode: tags-split`, mutator axios gắn JWT). Code sinh ra
nằm trong `src/frontend/src/api/generated/` (gitignore); mutator viết tay
`src/api/axios-instance.ts` giữ nguyên.

```sh
cd src/frontend
npm install
npm run gen:api            # đọc ./openapi.json đã xuất ở bước trên
# hoặc lấy trực tiếp từ backend đang chạy:
npm run gen:api:remote
```

Orval sinh hàm gọi API cộng hook React Query cộng kiểu TypeScript khớp schema.
JWT (`Authorization: Bearer <token>` từ `POST /auth/login`) gắn tự động qua
interceptor trong `axios-instance.ts`; `X-Edge-Key` cho `POST /captures` gắn tay khi gọi.

Lưu ý: `WS /ws/gate` là WebSocket, không nằm trong OpenAPI; nối tay bằng `WebSocket` của trình duyệt, dùng fallback `GET /captures/latest` (có trong schema) khi cần.

## Cấu trúc thư mục

```
app/
  config.py          cấu hình từ env
  db.py              engine, session, Base
  clock.py           now_utc, to_naive
  models/            8 bảng SQLAlchemy
  security/          crypto (Fernet), plate (HMAC), passwords (bcrypt), tokens (JWT)
  services/          audit, image_store, capture, vehicle_groups, matching, fee, stats, gate_hub, retention
  schemas/           pydantic request và response
  routers/           auth, users, captures, sessions, readings, images, stats, config, gate_ws, health
  main.py            app factory
alembic/             migration
scripts/             simulate_edge, seed_admin, run_retention
tests/               unit (SQLite)
tests_e2e/           e2e (HTTP thật)
```

## Ghi chú kỹ thuật

- Băm mật khẩu dùng thư viện `bcrypt` trực tiếp, không passlib (passlib 1.7.4 hỏng với bcrypt 5.x trên Python 3.13).
- Thời gian dùng `app/clock.py:now_utc()` (UTC naive). Cột `DateTime(timezone=True)` trả datetime aware trên Postgres nhưng naive trên SQLite; nơi trừ hoặc so sánh thời gian phải coerce bằng `to_naive` (xem `services/fee.py`, `services/stats.py`).
- Biển lưu hai dạng: bản mã hóa để hiển thị cộng cột `plate_hash` (HMAC của biển đã chuẩn hóa) để tra khớp không cần giải mã hàng loạt.
- Ảnh lưu file mã hóa trên đĩa, DB giữ đường dẫn. Job xóa (`scripts/run_retention.py`) xóa phiên cộng reading cộng file ảnh sau `RETENTION_DAYS` ngày kể từ khi xe ra, và ghi audit.
- Cấm mọi xử lý khuôn mặt tự động (ràng buộc pháp lý). Ảnh chỉ để nhân viên đối chiếu bằng mắt khi tranh chấp.
