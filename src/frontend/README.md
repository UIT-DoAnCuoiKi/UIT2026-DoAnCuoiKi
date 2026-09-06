# Frontend (React)

UI do người phụ trách tự dựng. Dịch vụ `frontend` trong `compose.yaml`
nằm dưới profile `frontend` nên `podman compose up` mặc định bỏ qua.

## Yêu cầu Node

Cần Node **≥ 20.10** (Orval 7.x dùng cú pháp import JSON mà Node 20.6 và cũ hơn
không hỗ trợ, sẽ báo lỗi `ERR_IMPORT_ASSERTION_TYPE_MISSING` khi chạy `npm run
gen:api`). `npm install`/`vitest`/`vite build` vẫn chạy được trên Node cũ hơn,
chỉ riêng bước sinh client Orval là cần bản mới.

Nếu Node hệ thống cũ hơn mốc này, tải bản portable (không cần quyền admin, không
đụng Node hệ thống) và trỏ PATH riêng cho phiên làm việc:

```sh
# một lần: tải + giải nén (đổi version nếu cần bản mới hơn)
curl -o node-lts.zip https://nodejs.org/dist/v24.20.0/node-v24.20.0-win-x64.zip
# giải nén vào %LOCALAPPDATA%\node-lts\

# mỗi phiên terminal cần Node mới (build, gen:api):
export PATH="/c/Users/$USER/AppData/Local/node-lts/node-v24.20.0-win-x64:$PATH"
node --version   # xác nhận đã lên bản mới
```

Khi có UI:

1. Thêm `src/frontend/Containerfile` build React tĩnh và phục vụ qua nginx cổng 80.
2. Cấu hình URL backend qua biến môi trường build (ví dụ `VITE_API_BASE=http://localhost:8000`).
3. Chạy kèm stack: `podman compose --profile frontend up -d --build frontend`.

Hợp đồng API mà UI tiêu thụ: xem Phase 3 tới 5 và spec
`docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md`.
Realtime cổng: `WS /ws/gate`, fallback `GET /captures/latest`.

## Truy cập API

Orval không phải service chạy nền, mà là công cụ codegen: sinh client TypeScript
từ OpenAPI thay vì gõ tay. API thật để gọi là backend.

Duyệt API (backend phải chạy: `cd src/backend && .venv/bin/uvicorn app.main:app --reload`):

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Schema thô: `http://localhost:8000/openapi.json`

Sinh client Orval (https://orval.dev):

```sh
cd src/backend && python scripts/export_openapi.py   # -> frontend/openapi.json
cd ../frontend  && npm install && npm run gen:api      # -> src/api/generated/
# hoặc lấy trực tiếp từ backend đang chạy:
npm run gen:api:remote
```

Code sinh ra ở `src/api/generated/` (gitignore), chia theo tag:

```
src/api/generated/
  <tag>/<tag>.ts     # hook React Query mỗi tag: auth/, sessions/, stats/...
  model/             # kiểu TypeScript khớp schema
```

Dùng trong React (JWT gắn tự động qua interceptor ở `src/api/axios-instance.ts`):

```ts
import { useLogin } from "./api/generated/auth/auth";
import { useListSessions } from "./api/generated/sessions/sessions";

const { data } = useListSessions({ status: "in_lot" });
```

Chi tiết operationId cộng cấu hình: `src/backend/README.md` mục "OpenAPI và sinh client frontend (Orval)".
Realtime cổng `WS /ws/gate` không nằm trong OpenAPI, nối tay; fallback `GET /captures/latest` có trong schema.
