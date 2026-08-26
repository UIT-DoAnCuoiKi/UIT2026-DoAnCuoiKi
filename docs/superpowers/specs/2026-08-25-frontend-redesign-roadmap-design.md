# Roadmap redesign giao diện và bổ sung tính năng bãi giữ xe

* **Ngày:** 2026-08-25
* **Người phụ trách:** Lê Quang Hoài Đức (25410034)
* **Trạng thái:** Draft v1 (roadmap tổng, chờ duyệt)
* **Loại tài liệu:** SPEC 0 — decomposition + sắp thứ tự. Không trực tiếp hiện thực; mỗi mảng có spec riêng (SPEC 1..N) brainstorm sâu lần lượt.
* **Tài liệu liên quan:**
  * `docs/superpowers/specs/2026-08-23-frontend-snowui-design.md` (thiết kế giao diện SnowUI v2, nền)
  * `docs/superpowers/specs/2026-08-23-parking-system-edge-cloud-architecture-design.md` (kiến trúc hai tầng)
  * `docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md` (hợp đồng backend nền)

## 1. Bối cảnh

Backend FastAPI đã hiện thực 17 router (`src/backend/app/routers`): health, auth, users, captures, sessions, readings, images, stats, config, spaces, shifts, payments, devices, incidents, registry, sync, gate_ws. Frontend React chỉ hiện thực 5 feature: `auth`, `gate`, `sessions`, `stats`, `config`. Sidebar 4 mục. Phần lớn năng lực backend chưa có giao diện, và các màn đã dựng còn sơ sài so với một bãi giữ xe vận hành thật.

Tài liệu này decompose công việc thành 7 mảng độc lập, xác định backend gap từng mảng, và sắp thứ tự theo phụ thuộc để tránh sót như đợt planning trước.

### 1.1 Phạm vi đã chốt (từ brainstorm)

* **Phân quyền 3 tầng:** `root` (CRUD nhân viên + toàn quyền), `manager` (cấu hình + thống kê, không quản nhân viên), `staff` (ra/vào + tra cứu). Hiện DB chỉ có `staff`/`admin`.
* **Phạm vi build:** toàn bộ app edge một bãi. Bao gồm surface mọi màn backend đã có (ca trực, thu tiền, sức chứa, sự cố, thiết bị, vé tháng/whitelist). **Ngoài phạm vi:** dashboard cloud đa bãi (làm sau khi Sync API ổn định).

### 1.2 Nguyên tắc dẫn dắt

1. **Hardcode chỉ cái bất biến.** Enum hướng (in/out), tập `review_state`, trạng thái session là bất biến → giữ hardcode. Mọi thứ đổi được theo vận hành (loại xe, giá, thời gian, lane, bãi/tầng/khu, vé tháng, whitelist/blacklist, thiết bị) → dữ liệu CRUD trên màn phù hợp.
2. **Trạm cổng zero thống kê.** Màn trạm cổng đặt nơi người ra/vào có thể nhìn thấy, nên không hiển thị KPI, doanh thu, lưu lượng. Màn cổng tối ưu hoàn toàn cho thao tác ra/vào + tra cứu. Thống kê chỉ bật cho `manager`/`root`.
3. **Tên thân thiện ở UI.** Mã kỹ thuật (`xe_may`, `o_to_con`…) chỉ tồn tại dưới DB. Thêm `display_name` do người dùng đặt; UI luôn hiển thị `display_name`.
4. **Backend là nơi chốt quyền.** Frontend ẩn/hiện theo role; guard backend vẫn kiểm mọi request.
5. **Luôn có đường lùi nhập tay** khi AI lỗi (kế thừa spec sản phẩm): ô sửa biển luôn hiện, nút nhập tay hoàn toàn luôn có.

## 2. Gap analysis (thực trạng code)

| Vùng | Thực trạng | Khoảng thiếu |
|---|---|---|
| Phân quyền | `deps.require_role`, `_ROLES=("staff","admin")` trong `users.py`. `stats` cho cả staff xem. Màn cổng hiện `GateKpis`. | Thêm role `manager`; siết `stats` khỏi staff; bỏ KPI khỏi màn cổng; guard 3 tầng frontend. |
| Loại xe | Hardcode `services/vehicle_groups.py`: `{"motorbike":"xe_may", ...}`. Tên gạch dưới. Không CRUD, không display_name. | Bảng `vehicle_type` (code, display_name, active); gắn `price_rule` theo loại; màn cấu hình CRUD. |
| Giá | `price_rule`: mode flat/block, unit_price, block_minutes. | Thêm `grace_minutes`; cân nhắc giá theo khung giờ; UI set giá + thời gian theo loại xe. |
| Trạm cổng | `gate-page.tsx`: nhận capture qua `useGateSocket`, một hướng in/out bằng nút, có `GateKpis`. Backend có `POST /captures/infer` (ảnh→pipeline→CaptureResponse). | Camera lớn; layout chia đôi vào‖ra hoặc chỉ-vào/chỉ-ra; `getUserMedia` + nút Chụp có phím tắt; thu tiền khi ra; bỏ KPI. |
| Tra cứu | `list_sessions`: chỉ `plate_hash == plate_hash(plate)` (khớp tuyệt đối). Biển mã hóa (`plate_ciphertext`) + hash → không LIKE được trên ciphertext. | Partial search cần quyết định thiết kế index (xem 4.1). Bộ lọc phiên nghèo. |
| Thống kê | `services/stats.py`: summary 4 số (in_lot, entries, exits, revenue) + daily_rows cho CSV. | Breakdown theo loại xe, giờ cao điểm, doanh thu theo phương thức/ca/nhân viên, vòng quay, thời lượng TB; granularity tháng/quý/năm/tùy chọn; UI tabbed. |
| Màn vận hành | Backend có shifts, payments, devices, incidents, spaces, registry. | Frontend chưa có màn nào cho các domain này. |

## 3. Bảy mảng công việc

Mỗi mảng là một sub-project: có spec riêng, plan riêng, build và review được độc lập.

### Mảng A — Phân quyền 3 tầng (nền)
* **Backend:** thêm role `manager`; cập nhật `_ROLES`; đảm bảo JWT mang role; `require_role` cho các route (`stats`→`manager`,`root`; `config`,`users`→theo bảng quyền; `users` CRUD→`root`). Di trú dữ liệu: role `admin` hiện tại map sang `root`.
* **Frontend:** guard router theo 3 role; sidebar lọc theo role; **bỏ `GateKpis` khỏi màn cổng**; ẩn mục Thống kê khỏi `staff`.
* **Chấp nhận:** staff đăng nhập không thấy Thống kê/Cấu hình; manager thấy Thống kê + Cấu hình nhưng không thấy quản lý nhân viên; root thấy tất cả; màn cổng không còn KPI.

### Mảng B — Trạm cổng redesign (giá trị vận hành cao nhất)
* **Backend:** dùng `POST /captures/infer` sẵn có; có thể thêm tham số lane/hướng; xác nhận luồng thu tiền khi ra nối `payments`.
* **Frontend:**
  * Camera view lớn. Layout chọn được: **chia đôi (vào ‖ ra song song)**, **chỉ vào**, hoặc **chỉ ra**. Mỗi panel có bộ chọn camera riêng (`getUserMedia`, hỗ trợ 2 webcam cho chế độ song song).
  * Nút Chụp gửi khung hình lên `/captures/infer`; **phím tắt** cho thao tác nhanh (đề xuất: `Space`/`Enter` chụp, phím xác nhận, phím nhập tay, phím chuyển hướng). Bảng phím tắt hiển thị được.
  * Panel quyết định theo `review_state` (confident/needs_review/disputed/manual); ô sửa biển luôn hiện; nút nhập tay hoàn toàn.
  * **Thu tiền khi ra** ngay tại màn cổng (nối mảng F-payment): hiện phí từ `ExitResult`, chọn phương thức, ghi `payment`, biên lai.
* **Chấp nhận:** một nhân viên vận hành được cả vào và ra song song bằng bàn phím, không cần chuột; không lộ thống kê.

### Mảng C — Danh mục loại xe + giá/thời gian (nền)
* **Backend:** bảng `vehicle_type` (`code`, `display_name`, `active`, sort order); thay `group_for` đọc từ DB thay vì map cứng (giữ seed mặc định cho dữ liệu bất biến ban đầu); `price_rule` gắn theo loại xe; thêm `grace_minutes`; (tùy chọn, chốt sau) giá theo khung giờ.
* **Frontend:** màn Cấu hình loại xe — CRUD với `display_name` thân thiện; đặt giá (flat/block, đơn giá, block_minutes, grace); bật/tắt loại.
* **Chấp nhận:** admin thêm/sửa/xóa loại xe với tên tiếng Việt thân thiện; đặt giá + thời gian mỗi loại; gate và fee dùng `display_name`; không còn chuỗi gạch dưới trên UI.

### Mảng D — Quản lý phiên + tra cứu partial
* **Backend:** hỗ trợ partial plate search (xem quyết định 4.1); mở rộng bộ lọc (theo loại xe, khoảng thời gian, match_flag, trạng thái); trả thêm trường hữu ích cho danh sách/chi tiết.
* **Frontend:** ô tra cứu cho phép partial; bộ lọc đa tiêu chí; bảng thêm cột; chi tiết phiên đầy đủ (ảnh vào/ra, reading, phí, phương thức thanh toán, audit truy cập ảnh).
* **Chấp nhận:** gõ một phần biển ra được danh sách khớp; phiên hiển thị đủ thông tin vận hành cần.

### Mảng E — Thống kê tabbed
* **Backend:** mở rộng `services/stats.py`: breakdown theo loại xe, theo giờ (giờ cao điểm), doanh thu theo phương thức/ca/nhân viên, vòng quay chỗ, thời lượng trung bình, tỷ lệ khớp; tham số granularity (ngày/tháng/quý/năm/tùy chọn).
* **Frontend:** trang Thống kê chia tabs theo nhóm thông tin; default theo ngày; quick-select tháng/quý/năm/tùy chọn; mỗi tab đủ biểu đồ + bảng số; xuất CSV (root/manager).
* **Chấp nhận:** phủ được mọi domain dữ liệu trong DB; không còn "sơ sài".

### Mảng F — Màn vận hành backend đã có
Surface API sẵn có thành giao diện:
* Ca trực + đối soát cuối ca (`shifts`).
* Thu tiền + biên lai + hoàn/điều chỉnh (`payments`) — dùng chung với B.
* Sức chứa/chiếm dụng theo bãi/tầng/khu (`spaces`, occupancy).
* Sự cố + nhật ký mở barie (`incidents`, `devices` barrier events).
* Thiết bị + health/heartbeat (`devices`).
* Vé tháng + whitelist/blacklist + chủ xe (`registry`).
* **Chấp nhận:** mỗi domain backend có ít nhất một màn CRUD/xem tương ứng.

### Mảng G — Research tính năng bãi xe chuẩn (song song)
* Dispatch `research-agent` khảo sát tính năng chuẩn của hệ thống ALPR parking thật; đối chiếu backlog.
* Backend đã phủ: lost-ticket, overstay, blacklist/whitelist, retention (xóa sau 30 ngày), occupancy, audit.
* Ứng viên còn thiếu ngoài đời (đưa vào backlog, ưu tiên sau): đặt chỗ/booking; giá theo khung giờ + grace period; QR/ví điện tử + in biên lai vật lý; theo dõi mức từng chỗ đỗ.

## 4. Quyết định flag (chốt trong spec sâu từng mảng)

### 4.1 Partial search trên biển mã hóa (mảng D)
Biển lưu `plate_ciphertext` + `plate_hash`, không LIKE được trên ciphertext.
* **Đề xuất demo:** `decrypt-and-scan` — tải phiên ứng viên trong khoảng lọc, giải mã trong bộ nhớ, lọc substring. Đơn giản, không đổi schema. Đủ ở quy mô thesis.
* **Phương án production:** blind index n-gram — lưu hash các n-gram của biển chuẩn hóa ở bảng phụ; truy vấn hash n-gram của chuỗi con rồi khớp. Giữ mã hóa at-rest. Nhiều việc + di trú.
* Chốt phương án khi brainstorm mảng D, cân nhắc Luật Bảo vệ dữ liệu cá nhân.

### 4.2 Giá theo khung giờ + grace period (mảng C)
`price_rule` hiện chỉ flat/block. Đề xuất thêm `grace_minutes` (nên có). Giá ngày/đêm hoặc theo khung giờ là tùy chọn, chốt khi brainstorm mảng C.

### 4.3 Phương thức thanh toán (mảng B/F)
Xác nhận enum phương thức (tiền mặt/QR/ví) và mẫu biên lai khi brainstorm mảng thu tiền.

## 5. Thứ tự và phụ thuộc

```
A (quyền) ──► B (trạm cổng) ──► D (phiên/tra cứu) ──► E (thống kê) ──► F (vận hành)
C (loại xe/giá) ─┘         └──────────────────────────┘
G (research) ── song song, sớm ── feed backlog vào các mảng
```

Thứ tự thực thi: **A → C → B → D → E → F**, với **G** chạy song song sớm.
Lý do: A và C là nền (quyền + dữ liệu loại xe/giá) unblock B (gate hiện `display_name` + thu tiền theo giá) và E (breakdown theo loại xe). B đứng ngay sau nền vì giá trị vận hành hàng ngày cao nhất và là trọng tâm bạn nêu.

## 6. Ánh xạ timeline thesis

Hôm nay 2026-08-25, tuần 6 (tích hợp hệ thống), tuần 7-8 là chuẩn bị và triển khai edge. Redesign này phục vụ "dashboard/edge prep" và demo cuối.
* A + C: sớm, nhỏ, làm nền.
* B: trọng tâm demo vận hành.
* D + E: bổ sung chiều sâu cho báo cáo (số liệu, tra cứu).
* F: mở rộng độ hoàn chỉnh; phần nào không kịp có thể giảm phạm vi mà không vỡ nền.

## 7. Ngoài phạm vi (đợt này)

Dashboard cloud đa bãi và tra cứu liên bãi; i18n đa ngôn ngữ; đầu đọc QR và máy in vé vật lý (chỉ mô phỏng biên lai); theo dõi mức từng chỗ đỗ; đặt chỗ/booking (backlog G, ưu tiên sau).

## 8. Bước kế tiếp

1. Duyệt roadmap này.
2. Brainstorm sâu **mảng A** (spec riêng) → writing-plans → build.
3. Lặp lại cho C, B, D, E, F. G dispatch song song khi bắt đầu.
