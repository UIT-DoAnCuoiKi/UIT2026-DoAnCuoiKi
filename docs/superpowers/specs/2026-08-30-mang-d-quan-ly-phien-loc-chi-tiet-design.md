# Mảng D — Quản lý phiên: lọc mở rộng + chi tiết đầy đủ

* **Ngày:** 2026-08-30
* **Người phụ trách:** Lê Quang Hoài Đức (25410034)
* **Trạng thái:** Draft v1 (chờ duyệt)
* **Loại tài liệu:** SPEC 4 (mảng D) trong roadmap redesign frontend.
* **Tài liệu liên quan:**
  * `docs/superpowers/specs/2026-08-25-frontend-redesign-roadmap-design.md` (roadmap tổng, §3.D, §4.1)
  * `.superpowers/sdd/progress.md` (ledger mảng C + B đã xong)

## 1. Bối cảnh

Mảng A (phân quyền 3 tầng), C (danh mục loại xe + giá), B (trạm cổng redesign) đã hoàn tất, review, test xanh trên `feat/duc-dashboard-backend`. Roadmap tiếp theo là D.

Thực trạng màn phiên:
* `GET /sessions` (`app/routers/sessions.py::list_sessions`) chỉ lọc `plate` (khớp `plate_hash` tuyệt đối) và `status`; `total` tính bằng `len(list(scalars(stmt).all()))` (materialize toàn bộ rồi đếm).
* `SessionOut` cho danh sách thiếu loại xe, nhân viên, phương thức thanh toán.
* `GET /sessions/{id}` (`session_detail`) trả `SessionDetail` gồm nhóm/loại/giờ/phí/match/warning + entry_reading + exit_reading. Thiếu lịch sử thanh toán, tên nhân viên mở/đóng, tên bãi/khu, snapshot bảng giá.
* Frontend `sessions-page.tsx` chỉ có ô tra biển + dropdown status. `sessions-columns.tsx` 8 cột. `session-detail-page.tsx` không hiện payment/nhân viên/bãi.

## 2. Phạm vi đã chốt (từ brainstorm)

1. **Bỏ partial plate search khỏi mảng D.** Không hiện thực tra cứu một phần biển số, không đụng quyết định 4.1 (decrypt-and-scan vs blind index). Biển giữ khớp `plate_hash` tuyệt đối như hiện tại. Roadmap §4.1 để lại backlog cho đợt sau.
2. **Không đụng schema, không migration.** Mọi field cần đọc đã có sẵn trên model (`ParkingSession`, `Payment`, `User`, `ParkingLot`, `Zone`). Chỉ thêm query param, shape response, và join đọc.
3. **Bộ lọc thêm:** nhóm xe, khoảng giờ vào, match_flag. Không lọc theo nhân viên.
4. **Chi tiết thêm:** lịch sử thanh toán, tên nhân viên mở/đóng, nhãn bãi/khu, `fee_rule_snapshot`.
5. **Cột bảng thêm:** loại xe (`vehicle_type`), nhân viên đóng (`closed_by_name`), phương thức thanh toán (`payment_method`). Giữ 8 cột cũ.
6. **Gộp hai fix backlog** liên quan: test-gap display_name và role-guard redirect.

## 3. Backend

### 3.1 `list_sessions` — mở rộng lọc

Thêm query params (giữ `plate`, `status`, `limit`, `offset`):

| Param | Kiểu | Điều kiện |
|---|---|---|
| `vehicle_group` | `str \| None` | `where(ParkingSession.vehicle_group == vehicle_group)` |
| `entry_from` | `datetime \| None` | `where(ParkingSession.entry_time >= entry_from)` |
| `entry_to` | `datetime \| None` | `where(ParkingSession.entry_time < entry_to)` |
| `match_flag` | `str \| None` | `where(ParkingSession.match_flag == match_flag)` |

Xây `stmt` bằng chain `.where()` có điều kiện (giống style hiện tại). Sửa `total` sang đếm trên query đã lọc, không materialize: `db.scalar(select(func.count()).select_from(stmt.subquery()))`. Giữ `order_by(id.desc()).limit().offset()` cho page rows.

### 3.2 Schema danh sách giàu hơn

`SessionOut` dùng chung bởi luồng cổng (`confirm_entry`, `confirm_exit`, `manual_session`, `dispute`, `resolve`, `lost_ticket`, `overstay`). Không thêm field vào `SessionOut`. Tạo schema riêng cho danh sách trong `app/schemas/session.py`:

```python
class SessionListItem(SessionOut):
    vehicle_type: str | None = None       # đã có trên model
    closed_by_name: str | None = None     # username của closed_by
    payment_method: str | None = None     # method của payment kind="payment" gần nhất
```

`SessionListResponse.items: list[SessionListItem]`.

### 3.3 Enrichment theo lô (tránh N+1)

Trong `list_sessions`, sau khi lấy `rows` của trang hiện tại:
1. Gom tập `closed_by` không null, một truy vấn `select(User.id, User.username).where(User.id.in_(ids))` dựng map `id -> username`.
2. Gom tập `session.id`, một truy vấn lấy payment `kind == "payment"` cho các session đó, chọn bản ghi `paid_at` mới nhất mỗi session, dựng map `session_id -> method`.
3. Dựng `SessionListItem` từ `_session_out(s)` cộng ba field từ hai map.

Semantics cột phương thức: nếu phiên chưa có payment `kind="payment"` thì `payment_method = None` (UI hiện trống). Refund/adjustment không tính vào cột này.

### 3.4 `session_detail` — làm giàu

`SessionDetail` (trong `app/schemas/session.py`) thêm:

```python
class PaymentBrief(BaseModel):
    id: int
    amount: int
    method: str
    kind: str
    note: str | None = None
    staff_name: str | None = None
    paid_at: datetime

class SessionDetail(SessionOut):
    vehicle_type: str | None = None       # đã có
    entry_reading: ReadingBrief | None = None   # đã có
    exit_reading: ReadingBrief | None = None    # đã có
    created_by_name: str | None = None
    closed_by_name: str | None = None
    lot_name: str | None = None
    zone_name: str | None = None
    fee_rule_snapshot: dict | None = None
    payments: list[PaymentBrief] = []
```

Trong `session_detail`:
* Payments: `select(Payment).where(Payment.session_id == s.id).order_by(Payment.paid_at)`; join `User` trên `staff_id` cho `staff_name` (một map id→username cho các staff_id xuất hiện).
* `created_by_name`, `closed_by_name`: lookup `User.username` theo `s.created_by`, `s.closed_by`.
* `lot_name`: `ParkingLot.name` theo `s.lot_id`; `zone_name`: `Zone.name` theo `s.zone_id`.
* `fee_rule_snapshot`: đọc thẳng `s.fee_rule_snapshot`.

## 4. Frontend

Sau khi backend đổi endpoint: chạy `scripts/export_openapi.py` (venv, `src/backend`) rồi `npm run gen:api` (`src/frontend`) để regen client trước khi sửa UI.

### 4.1 `sessions-page.tsx` — thanh lọc

Thêm cạnh ô tra biển và dropdown status:
* Dropdown nhóm xe: lặp `useVehicleGroupMap()`, option value = code, label = display_name; option rỗng = tất cả.
* Hai input `type="date"`: giờ vào từ / đến, map sang `entry_from` / `entry_to` (ISO). Bỏ trống = không lọc.
* Dropdown match_flag: rỗng / `exact` / `auto_corrected` / `manual` / `lost_ticket`.

Đưa vào `ListSessionsParams` qua `useMemo`; reset `offset = 0` khi đổi bất kỳ filter nào (giống pattern plate/status hiện có).

### 4.2 `sessions-columns.tsx` — thêm 3 cột

Giữ 8 cột cũ, thêm:
* **Loại xe:** `vehicle_type` raw (lớp ML, phân biệt với nhóm tính tiền; nhất quán với detail hiện đã hiện raw). Fallback `—`.
* **Nhân viên:** `closed_by_name`. Fallback `—`.
* **Phương thức:** `payment_method`. Fallback `—`.

### 4.3 `session-detail-page.tsx` — bổ sung

* Fields mới trong `dl`: Nhân viên vào (`created_by_name`), Nhân viên ra (`closed_by_name`), Bãi (`lot_name`), Khu (`zone_name`). Fallback `—`.
* Card Thanh toán (`SurfaceCard`): bảng `payments` cột số tiền (`formatVnd`), phương thức, loại, nhân viên (`staff_name`), giờ (`formatDateTime`). Rỗng thì "Chưa có thanh toán".
* Khối `fee_rule_snapshot` gọn: hiện các key có trong snapshot (mode, unit_price, block_minutes, grace_minutes...) dạng nhãn:giá trị. Ẩn nếu null.

## 5. Backlog gộp

### 5.1 Test-gap display_name (dương tính)

`session-detail-page.test.tsx` và `gate-page.test.tsx` hiện dùng fixture `vehicle_group` là code không có display_name nên rơi fallback về code, không kiểm được nhánh dương.

Fix: đặt fixture `vehicle_group` = một code có seed display_name (ví dụ `xe_may` → hiển thị nhóm), và assert text display_name xuất hiện trong DOM. Detail: assert field "Nhóm xe" hiện display_name. Gate: assert chip nhóm xe hiện display_name.

### 5.2 role-guard redirect

`app/role-guard.tsx` hiện: `if (!role || !roles.includes(role)) return <Navigate to="/gate" replace />;`. Khi `role` null (token cũ role không hợp lệ, `getRole()` trả null), redirect `/gate`; mà `/gate` cũng bọc `RequireRole` nên lại gặp role null, lặp vô hạn màn trắng.

Fix: tách hai nhánh.
* `!role` (không có role hợp lệ, token hỏng): `clearToken()` rồi `<Navigate to="/login" replace />`.
* Role hợp lệ nhưng không thuộc `roles` (thiếu quyền chính đáng): giữ `<Navigate to="/gate" replace />`.

Thêm test nhánh role null: dựng token có role không hợp lệ, assert điều hướng `/login` và token bị xóa.

## 6. Kiểm thử

### Backend (`.venv/bin/pytest` tại `src/backend`)
* `list_sessions` lọc `vehicle_group`: chỉ trả phiên đúng nhóm.
* Lọc `entry_from`/`entry_to`: chỉ trả phiên trong khoảng.
* Lọc `match_flag`: chỉ trả phiên đúng flag.
* `total` đúng theo query đã lọc (không phải tổng toàn bảng).
* `SessionListItem` có `vehicle_type`, `closed_by_name` (khi có closed_by), `payment_method` (khi có payment kind=payment; None khi chưa thu).
* `session_detail` trả `payments` (với `staff_name`), `created_by_name`, `closed_by_name`, `lot_name`, `zone_name`, `fee_rule_snapshot`.
* Seed vehicle_group catalog trong test tạo price_rule (theo pattern C4 đã chốt) nếu test có tính phí.

### Frontend (`npm run test` + `npm run build` tại `src/frontend`)
* `sessions-page`: đổi filter reset offset; params gồm filter mới.
* `sessions-columns`: render 3 cột mới (giá trị + fallback).
* `session-detail-page`: render bảng payments; render nhân viên/bãi/khu; positive assert display_name (§5.1).
* `role-guard`: nhánh role null → `/login` + clearToken (§5.2).

## 7. Non-goals

* Partial plate search (bỏ hẳn khỏi D, backlog roadmap §4.1).
* Thay đổi schema / migration.
* Blind index n-gram.
* Lọc/enrich theo shift, occupancy, thiết bị (thuộc mảng E/F).
* Sửa `SessionOut` của luồng cổng.

## 8. Chấp nhận

* Gõ nhóm xe + khoảng giờ vào + match_flag lọc ra đúng tập phiên; `total` và phân trang đúng theo filter.
* Bảng danh sách hiện loại xe, nhân viên đóng, phương thức thanh toán.
* Trang chi tiết hiện đủ: ảnh vào/ra, review state, lịch sử thanh toán (kèm phương thức + nhân viên thu), nhân viên mở/đóng, bãi/khu, cách tính phí (snapshot), ghi chú audit ảnh (đã có).
* role không hợp lệ không còn loop màn trắng; điều hướng `/login` và xóa token.
* Test dương tính display_name pass; toàn bộ suite backend + frontend xanh; `npm run build` pass.

## 9. File dự kiến chạm

**Backend:** `app/routers/sessions.py` (list + detail), `app/schemas/session.py` (SessionListItem, PaymentBrief, SessionDetail), test `tests/` (session list/detail).
**Frontend:** `src/features/sessions/sessions-page.tsx`, `sessions-columns.tsx`, `session-detail-page.tsx`, `src/app/role-guard.tsx`; test `sessions-page.test.tsx`, `session-detail-page.test.tsx`, `features/gate/gate-page.test.tsx`, `app/role-guard.test.tsx`; regen `src/api/generated/` qua `gen:api`.
