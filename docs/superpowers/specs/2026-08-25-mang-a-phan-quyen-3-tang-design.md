# Mảng A — Phân quyền 3 tầng (root / manager / staff)

* **Ngày:** 2026-08-25
* **Người phụ trách:** Lê Quang Hoài Đức (25410034)
* **Trạng thái:** Draft v1 (chờ review file, rồi writing-plans)
* **Thuộc:** SPEC 1 của roadmap `docs/superpowers/specs/2026-08-25-frontend-redesign-roadmap-design.md` (mảng A, làm nền, thứ tự #1).

## 1. Mục tiêu

Chuyển mô hình quyền từ 2 tầng `staff`/`admin` sang 3 tầng `root`/`manager`/`staff`. Siết thống kê khỏi staff, đưa CRUD nhân viên về root, tách cấu hình cho manager, và bỏ mọi thông tin thống kê khỏi màn Trạm cổng (yêu cầu bảo mật: màn cổng đặt nơi người ra/vào nhìn thấy).

## 2. Định nghĩa vai

| Vai | Ý nghĩa | Được làm |
|---|---|---|
| `root` | Chủ hệ thống, tầng cao nhất | Toàn quyền: CRUD nhân viên (username, password, role, active), đồng bộ, cấu hình, thống kê, mọi thao tác vận hành |
| `manager` | Quản lý bãi | Cấu hình (giá, loại xe, lane, toggle, bãi/tầng/khu, vé tháng, whitelist/blacklist, thiết bị) + thống kê. KHÔNG quản nhân viên |
| `staff` | Nhân viên trực cổng | Thao tác vận hành: ra/vào, thu tiền, ca trực, sự cố, tra cứu phiên. KHÔNG thấy thống kê, KHÔNG cấu hình, KHÔNG quản nhân viên |

Quyết định đã chốt (brainstorm): rename `admin` → `root` (không giữ nhãn admin). staff giữ các màn vận hành gồm ca trực, sự cố, thu tiền.

## 3. Ma trận quyền theo route

| Route | Guard hiện tại | Guard mục tiêu |
|---|---|---|
| `users` (CRUD nhân viên) | `require_role("admin")` | `require_role("root")` |
| `sync` (central admin) | `require_role("admin")` | `require_role("root")` |
| `stats` GET | `get_current_user` | `require_role("manager","root")` |
| `stats` export | `require_role("admin")` | `require_role("manager","root")` |
| `config` writes (price-rules, lanes, feature-toggles POST/PATCH) | `require_role("admin")` | `require_role("manager","root")` |
| `registry` writes | `require_role("admin")` | `require_role("manager","root")` |
| `devices` writes | `require_role("admin")` | `require_role("manager","root")` |
| `spaces` writes | `require_role("admin")` | `require_role("manager","root")` |
| `config`/`spaces`/`registry`/`devices` READS (GET) | `get_current_user` | giữ nguyên (mọi user đã đăng nhập) — gate cần đọc feature-toggle, zone |
| `sessions`, `captures/infer`, `readings`, `images`, `payments`, `shifts`, `incidents`, `occupancy`, `overstay` | `get_current_user` | giữ nguyên (staff + manager + root) |
| `captures` ingest (edge key), `gate_ws`, `health`, `auth` | không đổi | không đổi |

Quy tắc rút gọn:
* **root:** CRUD nhân viên + đồng bộ.
* **manager + root:** cấu hình (ghi) + thống kê.
* **staff + manager + root:** mọi thao tác vận hành + đọc cấu hình cần cho cổng.

## 4. Thay đổi backend

### 4.1 Roles và guard
* `app/routers/users.py`: `_ROLES = ("staff", "manager", "root")`; `admin_only = require_role("root")`.
* Đổi các `require_role("admin")` sang `require_role("root")` (users, sync) hoặc `require_role("manager", "root")` (stats export, config, registry, devices, spaces) theo ma trận mục 3.
* `app/routers/stats.py`: `get_stats` đổi dependency `get_current_user` → `require_role("manager", "root")`.
* `app/deps.py`: `require_role(*roles)` đã variadic — không sửa.

### 4.2 Seed và migration
* `scripts/seed_admin.py`: seed `role="root"`. Giữ tên biến môi trường `admin_username`/`admin_password` (tránh vỡ deploy hiện tại); chỉ đổi giá trị role được seed.
* Migration data (schema không đổi vì `role` là `String(16)`): script/one-off `UPDATE users SET role='root' WHERE role='admin'`. Thêm vào `scripts/` một hàm nhỏ hoặc chạy tay khi triển khai. Ở test/sqlite dùng `create_all`, không cần migration.

### 4.3 Không đổi
* JWT đã mang claim `role` (`security/tokens.py`) và login trả `role` (`auth.py`) — không đổi cơ chế token.
* Model `User.role` là `String(16)` — không đổi schema.

## 5. Thay đổi frontend

* `src/lib/auth.ts`: `export type Role = "root" | "manager" | "staff"`; `getRole` chấp nhận ba giá trị (bỏ ràng buộc chỉ `staff`/`admin`).
* `src/app/router.tsx`: route `stats` bọc `RequireRole roles={["manager","root"]}`; route `config` bọc `["manager","root"]`.
* `src/components/sidebar.tsx`: cập nhật mảng `roles` mỗi item:
  * Trạm cổng, Quản lý phiên: `["staff","manager","root"]`.
  * Thống kê: `["manager","root"]`.
  * Cấu hình: `["manager","root"]`.
* `src/features/gate/gate-page.tsx`: **bỏ `GateKpis`** khỏi render (zero thống kê ở trạm cổng). Xóa import và khối JSX; các file `gate-kpis.tsx` giữ lại (sẽ tái dùng ở màn thống kê/admin, hoặc dọn sau).
* `src/features/config/config-page.tsx`: tab **Nhân viên (UsersTab) chỉ render khi `getRole() === "root"`**; manager thấy Cấu hình nhưng không thấy tab Nhân viên.
* `RequireRole` (`role-guard.tsx`): logic giữ nguyên (đã nhận mảng roles); redirect route không đủ quyền về `/gate`.

## 6. Ảnh hưởng test (phải sửa)

* `tests/test_seed_admin.py`: assert `admin.role == "root"`.
* `tests/test_rbac_users.py`: user CRUD login bằng `role="root"`; giữ case staff 403; **thêm** case `manager` KHÔNG vào được `/users` (403).
* Mọi test login `role="admin"` để chạm `stats`/`config`/`registry`/`devices`/`spaces` → đổi `role="root"` hoặc `role="manager"`. Plan sẽ `grep -rn 'role="admin"\|role=.admin.' tests` liệt kê đầy đủ và sửa từng file (gồm các `test_phase*_acceptance`, `test_config`, `test_registry_api`, `test_devices_*`, `test_spaces_*`, `test_stats`, `test_sync_api`…).
* **Thêm** test: staff gọi `GET /stats` trả 403; manager gọi `GET /stats` trả 200.

## 7. Tiêu chí chấp nhận

* **staff** đăng nhập: sidebar chỉ Trạm cổng + Quản lý phiên; vào `/stats` hoặc `/config` bị redirect `/gate`; API `GET /stats` trả 403.
* **manager**: sidebar thêm Thống kê + Cấu hình; trong Cấu hình KHÔNG có tab Nhân viên; API `GET /users` trả 403; `GET /stats` trả 200.
* **root**: thấy tất cả, gồm tab Nhân viên; CRUD nhân viên hoạt động.
* Màn **Trạm cổng không còn KPI/thống kê** nào.
* Toàn bộ suite test backend pass sau khi cập nhật role.

## 8. Ngoài phạm vi mảng A

* Màn Cấu hình đầy đủ (loại xe CRUD, giá theo loại) — mảng C.
* Redesign Trạm cổng (camera lớn, split, phím tắt) — mảng B; mảng A chỉ bỏ KPI.
* Màn vận hành mới (ca trực, thu tiền, sự cố UI) — mảng F; mảng A chỉ mở quyền route cho staff.
* Phân công nhân viên theo bãi, đổi mật khẩu tự phục vụ.
