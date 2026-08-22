# Dashboard MVP: chỉ mục kế hoạch triển khai (6 phase)

> **For agentic workers:** mỗi phase là một plan riêng trong cùng thư mục. Thực thi tuần tự theo thứ tự phụ thuộc. Dùng superpowers:subagent-driven-development hoặc superpowers:executing-plans cho từng phase.

**Nguồn spec:** `docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md`

**Goal:** nối AI pipeline `src/ml` với backend FastAPI, PostgreSQL, edge worker, và Podman, phục vụ dashboard mà frontend do người phụ trách tự dựng.

**Architecture:** edge worker chạy pipeline và POST multipart (ảnh cộng JSON) về backend; backend giữ toàn bộ logic nghiệp vụ và lưu trữ, đẩy sự kiện cổng qua WebSocket; PostgreSQL lưu dữ liệu mã hóa; Podman compose chạy toàn stack trên PC, image edge worker build được cho Pi.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, SQLAlchemy 2.0 (sync), Alembic, psycopg2, pydantic v2, pydantic-settings, cryptography (Fernet), passlib[bcrypt], PyJWT, pytest, httpx, Podman.

**Phạm vi loại trừ:** giao diện React (người phụ trách tự dựng). Các plan chỉ tới endpoint REST và hợp đồng WebSocket mà UI tiêu thụ.

## Global Constraints (áp cho mọi phase, chép nguyên từ spec)

- Luật Bảo vệ dữ liệu cá nhân hiệu lực 2026-01-01: biển số và ảnh xe là dữ liệu cá nhân.
- Mã hóa tầng cột (application encrypt trước khi ghi) cho biển và ảnh; khóa nạp từ biến môi trường, không nằm trong repo, không hardcode.
- Hạn lưu trữ: 30 ngày sau `exit_time`; job xóa hàng ngày xóa `session` cộng `plate_reading` liên quan cộng file ảnh cộng ghi một dòng audit.
- Cấm mọi xử lý khuôn mặt tự động: không import model nhận diện khuôn mặt; soát khi review code.
- `capture_id`: UNIQUE, khóa idempotent cho `POST /captures`.
- `review_state` do backend tính, nhận một trong `confident`, `needs_review`, `disputed`, `manual`.
- Nhóm xe: `xe_may` (motorbike, bicycle), `o_to_con` (car), `xe_tai` (truck), `xe_khach` (bus).
- Phí: `mode = flat` một giá trọn lượt, hoặc `mode = block` bằng `ceil(thời_gian / block_minutes) * unit_price`, làm tròn lên, không grace; đọc giá lúc xe ra; lưu `fee_rule_snapshot`.
- Khớp biển: chuẩn hóa rồi exact; tự nối chỉ khi duy nhất và edit distance `k <= 1`; `k == 2` hoặc nhiều ứng viên thì đưa nhân viên chọn; không ứng viên thì `disputed`.
- Ngưỡng soát: `ocr_conf < 0.7` hoặc `plate_valid == false` hoặc `det_conf` thấp thì `needs_review`, không bao giờ chặn xác nhận.
- Transport: REST cộng WebSocket `/ws/gate` với fallback polling.
- Vai: `staff` và `admin` theo ma trận trong spec.
- Quy tắc commit (dự án): chỉ commit khi người dùng yêu cầu rõ trong lượt đó; các bước commit trong plan là điểm mốc, gom thay đổi rồi để người dùng commit.
- Quy tắc viết: không dùng ký tự gạch ngang trong văn xuôi tài liệu.
- Nghiệm thu: mỗi phase, ngoài test TDD từng task, kết thúc bằng một test nghiệm thu (acceptance) kiểm chứng deliverable của cả phase; task cuối mỗi phase chạy test này cộng toàn bộ suite của phase và phải PASS trước khi qua phase sau.

## Danh sách phase

| Phase | Plan file | Nội dung | Phụ thuộc | Deliverable test được |
|---|---|---|---|---|
| 1 | `2026-08-22-phase-1-backend-foundation.md` | Scaffold backend, config env, DB engine, 8 model SQLAlchemy, Alembic migration, tiện ích mã hóa Fernet, chuẩn hóa và HMAC biển | không | migration tạo đủ bảng; mã hóa round trip và hash biển pass test |
| 2 | `2026-08-22-phase-2-auth-audit.md` | Băm mật khẩu, đăng nhập JWT, dependency phân vai staff và admin, ghi `audit_log`, CRUD user (admin) | 1 | login trả token; endpoint chặn theo vai; audit ghi đúng |
| 3 | `2026-08-22-phase-3-capture-ingestion.md` | `POST /captures` multipart idempotent, lưu `plate_reading` cộng `image_asset` mã hóa, chọn biển đại diện, tính `review_state`, script giả lập edge worker | 1, 2 | capture lưu reading với `review_state`; gửi trùng `capture_id` không nhân đôi |
| 4 | `2026-08-22-phase-4-sessions-matching-fees.md` | Xác nhận vào và ra, khớp biển (exact, k<=1 tự nối, k==2 gợi ý, disputed), nhập tay, sửa biển, resolve dispute, tính phí flat và block, snapshot giá | 1, 2, 3 | vòng đời session đầy đủ; phí đúng theo nhóm và mode |
| 5 | `2026-08-22-phase-5-query-stats-realtime-retention.md` | `GET /sessions` lọc và phân trang, `GET /sessions/{id}`, `GET /images/{id}` chặn auth cộng audit, `GET /stats`, `GET /stats/export` CSV, CRUD `lane` và `price_rule` và `feature_toggle`, `WS /ws/gate` cộng fallback polling, job xóa theo hạn lưu trữ | 1, 2, 3, 4 | tra cứu và thống kê và CSV chạy; WS đẩy sự kiện; job xóa dữ liệu quá hạn |
| 6 | `2026-08-22-phase-6-podman-edge-packaging.md` | Containerfile backend và edge worker, `compose.yaml` cho PC, volume Postgres và ảnh, env và secrets, healthcheck, build multi-arch cho Pi | 1 tới 5 | `podman compose up` chạy full stack trên PC |

## Thứ tự thực thi

1 trước, vì mọi thứ dựa trên schema và tiện ích mã hóa. 2 và 3 dựa trên 1; 3 dùng dependency auth của 2 cho endpoint có bảo vệ. 4 dựa trên 1 tới 3. 5 dựa trên 1 tới 4. 6 đóng gói sau khi backend chạy được. Frontend React do người phụ trách dựng song song, tiêu thụ hợp đồng API từ phase 3 tới 5.
