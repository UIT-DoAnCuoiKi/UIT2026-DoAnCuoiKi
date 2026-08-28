# Mảng C: Danh mục loại xe (vehicle_group) và giá/thời gian

* **Ngày:** 2026-08-28
* **Người phụ trách:** Lê Quang Hoài Đức (25410034)
* **Trạng thái:** Draft v1 (chờ review file, rồi writing-plans)
* **Thuộc:** SPEC 2 của roadmap `docs/superpowers/specs/2026-08-25-frontend-redesign-roadmap-design.md` (mảng C, làm nền, thứ tự #2 sau A).
* **Tài liệu liên quan:**
  * `docs/superpowers/specs/2026-08-25-mang-a-phan-quyen-3-tang-design.md` (mảng A, đã build, cung cấp guard 3 tầng dùng lại ở đây)

## 1. Mục tiêu

Đưa danh mục loại xe tính tiền thành dữ liệu CRUD có tên thân thiện, thay cho map cứng gạch dưới trong `app/services/vehicle_groups.py`. Operator (manager/root) đặt tên hiển thị tiếng Việt, thứ tự, bật tắt, và đặt giá theo từng nhóm ngay trên một màn. UI mọi nơi hiển thị `display_name` thay cho code kỹ thuật.

## 2. Bối cảnh và làm rõ khái niệm

DB có hai trường tách biệt, cần phân biệt rõ:

| Trường | Ý nghĩa | Nơi lưu |
|---|---|---|
| `vehicle_type` | Lớp ML detector nhận dạng: `motorbike`, `car`, `truck`, `bus`, `bicycle`. Bất biến theo model đã train. | `plate_reading.vehicle_type`, `parking_session.vehicle_type` |
| `vehicle_group` | Nhóm tính tiền: `xe_may`, `o_to_con`, `xe_tai`, `xe_khach`, `unknown`. Gắn `price_rule`, `monthly_pass`, matching. | `parking_session.vehicle_group`, `price_rule.vehicle_group`, `monthly_pass.vehicle_group` |

`group_for(vehicle_type)` trong `app/services/vehicle_groups.py` map lớp ML sang nhóm tính tiền qua `_MAP` cứng. "Loại xe" mà operator quản lý (đặt tên + giá) chính là `vehicle_group`.

**Quyết định phạm vi (chốt brainstorm):** operator chỉ quản lý nhóm tính tiền (`vehicle_group`): tên hiển thị, giá, active, thứ tự. Ánh xạ detector sang nhóm giữ seed cố định vì lớp ML bất biến. Không thêm giá theo khung giờ trong mảng này (để backlog). `grace_minutes` và `daily_cap` đã có sẵn trong `price_rule` và `fee.py` đã áp dụng, không làm lại.

## 3. Data model

### 3.1 Bảng mới `vehicle_group`

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `id` | Integer | PK |
| `code` | String(16) | unique, not null, immutable sau tạo (mã kỹ thuật, ví dụ `xe_may`) |
| `display_name` | String(64) | not null (tên thân thiện, ví dụ `Xe máy`) |
| `active` | Boolean | default true |
| `sort_order` | Integer | default 0 |
| `created_at` | DateTime(timezone=True) | server_default now() |
| `updated_at` | DateTime(timezone=True) | server_default now(), onupdate now() |

Model `app/models/vehicle_group.py` (`VehicleGroup`), đăng ký trong `app/models/__init__.py`.

### 3.2 Seed mặc định

Hằng số `DEFAULT_VEHICLE_GROUPS` trong `app/services/vehicle_groups.py` và hàm `seed_default_vehicle_groups(db)` (idempotent: bỏ qua code đã tồn tại).

| code | display_name | sort_order | active |
|---|---|---|---|
| `xe_may` | Xe máy | 1 | true |
| `o_to_con` | Ô tô con | 2 | true |
| `xe_tai` | Xe tải | 3 | true |
| `xe_khach` | Xe khách | 4 | true |
| `unknown` | Chưa xác định | 99 | true |

`unknown` là fallback khi `group_for` trả None (đã dùng trong `sessions.py` qua `group_for(...) or "unknown"`) và cho phiên nhập tay chưa rõ loại. Không bắt buộc có `price_rule`.

### 3.3 Linkage `price_rule`

Giữ `price_rule.vehicle_group` là String code, không đổi schema `price_rule`. Thêm validate on write: `create_price_rule` và `update_price_rule` kiểm code tồn tại trong `vehicle_group`, nếu không trả 422 "vehicle_group không tồn tại". Không đổi `fee.py`, `get_active_rule`, `sync`, `sessions.py`.

### 3.4 `group_for` giữ nguyên nguyên tắc

`_MAP` giữ là seed constant (lớp detector cố định theo model). `group_for` không đọc DB, giữ ingest hot path nhẹ. Mọi code trong `_MAP` (`xe_may`, `o_to_con`, `xe_tai`, `xe_khach`) đều nằm trong seed catalog. Catalog chỉ là lớp hiển thị + giá, không thay logic ánh xạ.

## 4. Backend API

Router mới `app/routers/vehicle_groups.py`, prefix `/vehicle-groups`, đăng ký trong `app/main.py`. Schemas `app/schemas/vehicle_group.py`.

### 4.1 Schemas

* `VehicleGroupIn`: `code: str`, `display_name: str`, `sort_order: int = 0`, `active: bool = True`.
* `VehicleGroupUpdate`: `display_name: str | None`, `sort_order: int | None`, `active: bool | None`. (Không có `code`: immutable.)
* `VehicleGroupOut`: `id`, `code`, `display_name`, `active`, `sort_order`, `model_config = {"from_attributes": True}`.

### 4.2 Endpoints

| Method | Path | Guard | Hành vi |
|---|---|---|---|
| GET | `/vehicle-groups` | `get_current_user` | List all, order by `sort_order`, `id`. Mọi user đăng nhập đọc được (gate/sessions/stats cần `display_name`). |
| POST | `/vehicle-groups` | `require_role("manager","root")` | Tạo nhóm. 409 nếu `code` trùng. |
| PATCH | `/vehicle-groups/{id}` | `require_role("manager","root")` | Sửa `display_name`/`sort_order`/`active`. 404 nếu không thấy. `code` không sửa. |
| DELETE | `/vehicle-groups/{id}` | `require_role("manager","root")` | 404 nếu không thấy. 409 nếu `code` referenced bởi `parking_session` hoặc `price_rule` hoặc `monthly_pass`. Else hard delete. |

Ràng buộc thiết kế nêu rõ: nhóm operator thêm mới không được `group_for` tự gán (detector map cố định), chỉ dùng cho phiên nhập tay + `monthly_pass`. Seed core groups thực tế không xóa được vì luôn referenced.

## 5. Frontend

### 5.1 Codegen

Sau khi thêm endpoint, chạy `npm run gen:api` (orval) tại `src/frontend` sinh hooks `useListVehicleGroups`, `useCreateVehicleGroup`, `useUpdateVehicleGroup`, `useDeleteVehicleGroup` và model `VehicleGroupOut` trong `src/api/generated`.

### 5.2 Tab "Loại xe"

Thay `TabsTrigger`/`TabsContent` value `price` trong `config-page.tsx` bằng tab "Loại xe" (giữ position, đổi label và nội dung). Component mới `src/features/config/vehicle-groups-tab.tsx`, DataTable một dòng mỗi nhóm:

* Cột: `display_name` (sửa qua dialog), `code` (read only), `active` (toggle), `sort_order`.
* Giá của nhóm: mode, unit_price, block_minutes, grace_minutes, daily_cap. Sửa qua dialog "Đặt giá" gọi patch (nếu nhóm đã có rule active) hoặc create `price_rule` với `vehicle_group = code`.
* Nút "Thêm nhóm" (dialog nhập code + display_name). Nút "Xóa" gọi DELETE, bắt 409 và toast "nhóm đang được sử dụng".

Component cũ `price-rules-tab.tsx` bị thay thế (nội dung giá gộp vào tab loại xe). Xóa `PriceRulesTab` khỏi `config-page.tsx`.

### 5.3 Lookup dùng chung

Hook `useVehicleGroupMap()` (ví dụ `src/lib/vehicle-groups.ts` hoặc `src/api/vehicle-groups.ts`) trả `Record<string, string>` (code sang display_name) từ `useListVehicleGroups`. Dùng ở:

* `src/features/gate/gate-page.tsx`: panel kết quả hiện `display_name` của nhóm detect.
* Sessions table + detail: cột/ô nhóm xe hiện `display_name`.
* Stats labels: nhãn breakdown theo nhóm hiện `display_name` (mảng E dùng lại).
* Monthly_pass form (nếu có UI ở mảng F): selector nhóm hiện `display_name`.

Fallback: nếu code không có trong map thì hiển thị chính code.

### 5.4 Manual entry

Selector `vehicle_group` ở luồng nhập tay (sessions) hiện `display_name` của các nhóm `active`, submit gửi `code`.

## 6. Migration + seed

* Alembic migration mới, `down_revision = "f6a7b8c9d0e1"` (head hiện tại `f6a7b8c9d0e1_add_uuid_outbox`): create table `vehicle_group` + `op.bulk_insert` 5 seed rows từ `DEFAULT_VEHICLE_GROUPS`.
* `scripts/seed_vehicle_groups.py` cho deployment hiện có (gọi `seed_default_vehicle_groups`, pattern giống `scripts/seed_admin.py`).
* Test dùng `create_all`; conftest fixture seed qua `seed_default_vehicle_groups`.

## 7. Testing

### 7.1 Backend `tests/test_vehicle_groups.py`

* 5 seed groups tồn tại sau `seed_default_vehicle_groups`.
* GET `/vehicle-groups` mọi user đăng nhập trả 200; order theo `sort_order`.
* POST/PATCH/DELETE: staff trả 403; manager và root trả 200/201.
* POST `code` trùng trả 409.
* DELETE nhóm referenced (có `parking_session` hoặc `price_rule`) trả 409; DELETE nhóm mới chưa referenced trả 200.
* create `price_rule` với `vehicle_group` không tồn tại trả 422.

### 7.2 Frontend vitest

* `vehicle-groups-tab` render `display_name`, không lộ code thô ở cột chính.
* `useVehicleGroupMap` map code sang `display_name`.

## 8. Tiêu chí chấp nhận

* Manager/root thêm, sửa, xóa nhóm loại xe với tên tiếng Việt thân thiện; đặt giá (mode, đơn giá, block_minutes, grace, cap) mỗi nhóm trên một màn.
* Gate, sessions, stats hiển thị `display_name`, không còn chuỗi gạch dưới (`xe_may`...) trên UI.
* Xóa nhóm đang được tham chiếu bị chặn (409); nhóm mới chưa dùng xóa được.
* `price_rule` gắn code không tồn tại bị chặn (422).
* Staff không sửa được danh mục (403); vẫn đọc được để nhập tay.
* Toàn bộ suite test backend + frontend pass.

## 9. Ngoài phạm vi mảng C

* Giá theo khung giờ ngày/đêm hoặc N khung tùy chỉnh (backlog).
* Sửa ánh xạ detector sang nhóm từ UI (giữ seed cố định).
* Redesign trạm cổng dùng `display_name` + thu tiền (mảng B; mảng C chỉ cung cấp lookup + hợp đồng dữ liệu).
* Màn vận hành mới (mảng F).

## 10. Hợp đồng dữ liệu bàn giao cho mảng B

Mảng B (trạm cổng) tiêu thụ từ mảng C:

* `GET /vehicle-groups` trả danh sách nhóm active kèm `display_name` để gate hiển thị và cho nhập tay.
* Hook `useVehicleGroupMap()` để render `display_name` trên panel kết quả.
* `price_rule` theo nhóm (đã validate) để `ExitResult` tính phí khi ra.
