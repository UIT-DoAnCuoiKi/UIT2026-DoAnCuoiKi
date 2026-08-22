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

Sinh client TypeScript từ OpenAPI thay vì gõ tay: backend phát hành `http://localhost:8000/openapi.json`
(Swagger UI ở `/docs`). Dùng Orval (https://orval.dev) để sinh hàm gọi API cộng hook React Query cộng kiểu.
Xem hướng dẫn cộng ví dụ `orval.config.ts` ở `src/backend/README.md` mục "OpenAPI và sinh client frontend (Orval)".
