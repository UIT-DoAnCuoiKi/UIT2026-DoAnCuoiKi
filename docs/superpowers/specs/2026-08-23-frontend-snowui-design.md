# Thiết kế giao diện dashboard bãi đỗ xe theo theme SnowUI

* **Ngày:** 2026-08-23
* **Người phụ trách:** Lê Quang Hoài Đức (25410034)
* **Trạng thái:** Draft v2 (cập nhật theo kiến trúc edge và cloud)
* **Tài liệu liên quan:**
  * `docs/superpowers/specs/2026-08-23-parking-system-edge-cloud-architecture-design.md` (kiến trúc tổng hai tầng, chi phối tài liệu này)
  * `docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md` (hợp đồng dữ liệu backend nền, đã hiện thực ở `src/backend`)
  * `docs/design/dashboard-mvp-brainstorm-prompt.md` (bộ câu hỏi định hướng)
  * Nguồn theme: SnowUI (ByeWind dashboard), phân tích từ 11 ảnh tham chiếu.
* **Phạm vi:** phần giao diện (frontend React). Giữ theme, design token, và component của SnowUI. Cập nhật v2 để bám kiến trúc hai tầng: một bề mặt kiosk edge tại chỗ (offline, có webcam suy luận, thu tiền, sức chứa, barie, ca trực) và một bề mặt dashboard cloud đa bãi.

> **Cập nhật v2 (2026-08-23).** Bản v1 giả định backend đóng băng, một bãi, không ML, frontend chỉ xác nhận theo `reading_id` do edge worker tạo. Kiến trúc mới (xem spec kiến trúc tổng) đổi giả định đó: (1) hệ thống hai tầng, mỗi bãi là một site edge chạy trọn trên Pi 5 kiosk và hoạt động offline, cloud là lớp tổng hợp đa bãi; (2) suy luận ML chạy tại backend edge, kiosk lấy khung hình webcam bằng `getUserMedia` rồi POST ảnh, không còn phụ thuộc edge worker đẩy payload sẵn; (3) thêm các miền đa bãi/tầng/khu, sức chứa, thanh toán, ca trực, đăng ký xe, thiết bị, sự cố. Các mục bị ảnh hưởng dưới đây có nhãn **v2**. Phần token, component nền, a11y giữ nguyên.

## 0. Bối cảnh và mục tiêu

Backend FastAPI đã hiện thực đầy đủ ở `src/backend` (6 phase, 84 test pass), hợp đồng API đóng băng. Client TypeScript sinh sẵn bằng orval (`src/frontend/src/api/generated`, hook React Query theo tag, JWT gắn tự động qua axios interceptor). Ứng dụng React chưa dựng: `package.json` mới có `@tanstack/react-query` và `axios`, chưa có React, build tool, router, UI lib.

Mục tiêu: dựng giao diện vận hành cho nhân viên cổng (staff) và quản trị (admin), bám sát theme SnowUI, chạy desktop web, riêng màn Trạm cổng thân thiện cảm ứng để chạy được kiosk. Hỗ trợ chế độ sáng và tối.

Nguyên tắc bắt buộc kế thừa từ spec sản phẩm: luôn có đường lùi nhập tay hoàn toàn khi AI lỗi; ô sửa biển luôn hiện; session nghi vấn chuyển `disputed`, không tự tính phí; frontend chỉ render theo `review_state` backend trả, không tự tính ngưỡng.

## 1. Kiến trúc và công nghệ

| Lớp | Chọn | Lý do |
|---|---|---|
| Build | Vite + React 18 + TypeScript | Nhanh, khớp orval và React Query có sẵn |
| Routing | React Router v6 | Route guard theo vai staff và admin, deep link mỗi màn |
| Data fetching | TanStack Query (đã có) + axios (đã có) | Hook orval sinh sẵn dùng thẳng |
| UI primitives | shadcn/ui + Radix + Tailwind CSS | Sở hữu code component, dựng lại token SnowUI dễ, chế độ tối bằng biến CSS |
| Bảng dữ liệu | TanStack Table | Sort, filter, phân trang phía server cho `/sessions` |
| Form | React Hook Form + Zod | Login, sửa biển, CRUD cấu hình, kiểm tra hợp lệ |
| Biểu đồ | Recharts (qua shadcn chart wrapper) | Tailwind native, đủ cho line, bar, donut |
| Icon | lucide-react | Đúng phong cách outline SnowUI, một độ dày nét |
| Realtime | WebSocket thuần + fallback polling | `WS /ws/gate` ngoài OpenAPI, nối tay; fallback `GET /captures/latest` |
| Định dạng số và ngày | Intl API, locale vi-VN | Tiền, thời lượng, timestamp |

Ứng dụng là client thuần: build tĩnh, phục vụ qua nginx. **App kiosk edge (v2)** phục vụ trên `localhost` của Pi và mở bằng Chromium chế độ kiosk; `getUserMedia` chạy vì `localhost` là secure context, không cần HTTPS; `VITE_API_BASE` trỏ backend edge cùng máy. **App dashboard cloud (v2)** build tĩnh riêng, `VITE_API_BASE` trỏ Sync API cloud, chạy qua HTTPS.

## 2. Hệ thống design token (SnowUI)

Token lưu bằng biến CSS trên `:root` (sáng) và `.dark` (tối), khai báo lại trong Tailwind theme. Component chỉ dùng token ngữ nghĩa, không hardcode hex.

### 2.1 Màu nền và chữ

| Token | Sáng | Tối |
|---|---|---|
| `--bg` | `#FFFFFF` | `#1C1C1C` |
| `--surface` (panel phụ) | `#F7F9FB` | `rgba(255,255,255,0.05)` |
| `--ink` (chữ chính) | `#1C1C1C` | `#FFFFFF` |
| `--muted` (chữ phụ) | `rgba(28,28,28,0.4)` | `rgba(255,255,255,0.4)` |
| `--faint` | `rgba(28,28,28,0.2)` | `rgba(255,255,255,0.2)` |
| `--line` | `rgba(28,28,28,0.1)` | `rgba(255,255,255,0.1)` |
| `--primary` | `#1C1C1C` | `#95A4FC` |
| `--on-primary` | `#FFFFFF` | `#1C1C1C` |

### 2.2 Màu pastel (KPI tile) và màu biểu đồ

* Tile: xanh `#E3F5FF`, tím `#E5ECF6`, mint `#DEF8EE`, periwinkle nhạt `#EDF0FF`. Ở chế độ tối, tile trung tính chuyển `rgba(255,255,255,0.05)`, tile nhấn giữ pastel.
* Chuỗi màu biểu đồ: periwinkle `#95A4FC`, tím `#C6C7F8`, mint `#A1E3CB`, cyan `#B1E3FF`, xanh bụi `#A8C5DA`, đen `#1C1C1C`.

### 2.3 Màu trạng thái, ánh xạ thẳng `review_state` và `status`

| Ý nghĩa | Token | Sáng | Tối |
|---|---|---|---|
| confident, completed | `--st-green` | `#1F9D63` | `#3FBE82` |
| manual, in_progress | `--st-purple` | `#7A7CD6` | `#95A4FC` |
| in_lot, pending | `--st-blue` | `#2E8BC0` | `#59A8D4` |
| needs_review, approved | `--st-amber` | `#B98900` | `#E6A23C` |
| disputed, rejected | `--st-red` | `#D24A3E` | `#E4695E` |
| rejected trung tính | `--st-grey` | `rgba(28,28,28,0.4)` | `rgba(255,255,255,0.4)` |

Màu không bao giờ là tín hiệu duy nhất: mỗi trạng thái luôn kèm icon và nhãn chữ (yêu cầu WCAG `color-not-only`).

### 2.4 Typography

* Font chữ: Inter (400, 500, 600, 700), `font-display: swap`.
* Thang cỡ: 12, 13, 14 (thân), 16, 20, 24 (số KPI), 30 (biển số ô cổng).
* Cột số (phí, thời gian, biển số) bật `font-variant-numeric: tabular-nums` để chống nhảy layout.
* Tiêu đề trang và tiêu đề panel dùng 14px semibold, theo SnowUI (không phóng đại).

### 2.5 Spacing, bo góc, đổ bóng

* Spacing theo bậc 4 và 8. Padding card 20px, khoảng cách card 18px, padding nội dung trang 24px tới 28px.
* Bo góc: card 16px, nút và input 8px, chip bo tròn hết, pagination pill 8px.
* Đổ bóng gần phẳng: phân tầng bằng nền (`--surface` trên `--bg`) và viền `--line`, chỉ dùng bóng rất nhẹ cho phần tử nổi như seg đang chọn và dropdown.

## 3. Thư viện component

Mỗi component có một mục đích rõ, nhận props, có đủ trạng thái. Dựng trên shadcn/ui, tùy biến theo token trên.

* **AppShell:** lưới ba cột (sidebar 212px, main, right rail 300px). Rail và sidebar tự ẩn theo breakpoint (rail ẩn dưới 1200px, sidebar gập dưới 860px).
* **Sidebar:** brand, nhóm nav (Vận hành, Quản trị, Phiên), item có icon và nhãn, item đang chọn nền `--surface` cộng thanh dọc `--ink` bên trái. Lọc theo vai.
* **Topbar:** nút gập sidebar, breadcrumb, ô Search, nút chuyển sáng và tối, chuông, panel toggle.
* **RightRail:** ba khối, ánh xạ domain: Sự kiện cổng (feed realtime, dot màu `review_state`), Nhật ký (audit log), Nhân viên trực (danh sách staff đang trực).
* **KpiTile:** nền pastel, tiêu đề, số lớn, delta cộng icon mũi tên lên hoặc xuống. Có trạng thái loading (skeleton) và empty.
* **Card:** biến thể `surface` (nền `--surface`, không viền) và `white` (nền `--bg`, viền `--line`).
* **DataTable:** header, hàng hover, chip trạng thái dạng dot, sort theo cột, phân trang server, empty state, loading skeleton. Dùng cho Quản lý phiên và bảng cấu hình.
* **StatusChip / StatusDot:** màu cộng icon cộng nhãn, bốn giá trị `review_state` và bốn `status` session.
* **PlateField:** ô sửa biển, cỡ lớn, tabular. Luôn hiện. Highlight viền `--st-amber` khi `needs_review`.
* **Button:** primary (nền `--primary`), secondary (viền), và biến thể ngữ nghĩa on-green, on-amber, on-red, on-purple cho hành động theo trạng thái cổng. Chiều cao 40px, target chạm tối thiểu 44px cho màn cổng.
* **Charts:** LineChart (lưu lượng), BarChart (doanh thu), DonutChart (cơ cấu nhóm xe), qua Recharts. Kèm legend, tooltip, và bảng số thay thế cho a11y.
* **Toast, Dialog, Tabs, Segmented, Switch, Pagination, Skeleton, EmptyState:** theo shadcn, token SnowUI.

## 4. Kiến trúc thông tin và điều hướng

Shell ba cột SnowUI. Nav trái theo vai:

Có hai ứng dụng frontend: **app kiosk edge** (routes dưới đây) và **app dashboard cloud** (mục 5.10, bố cục và token cùng bộ, nav đa bãi riêng). Nav app edge theo vai:

* staff: Trạm cổng, Quản lý phiên, Sức chứa, Ca trực, Sự cố, Thống kê (xem).
* admin: thêm Cấu hình, quyền đầy đủ ở Thống kê (xuất CSV).

Route và guard (app kiosk edge):

| Route | Màn | Quyền |
|---|---|---|
| `/login` | Đăng nhập | công khai |
| `/gate` | Trạm cổng kiosk (webcam, thu tiền) | staff, admin |
| `/sessions`, `/sessions/:id` | Quản lý phiên | staff, admin |
| `/capacity` | Sức chứa và chiếm dụng | staff, admin |
| `/shift` | Ca trực và đối soát | staff, admin |
| `/incidents` | Sự cố | staff, admin |
| `/stats` | Thống kê | staff xem, admin xuất CSV |
| `/config` | Cấu hình | admin |

App dashboard cloud có route riêng (tổng quan đa bãi, tra cứu liên bãi, báo cáo tổng, quản trị master, trạng thái đồng bộ), quyền admin tổng và người xem.

Guard đọc vai từ JWT. Vào route không đủ quyền thì chuyển về `/gate` cộng toast báo. Mọi màn có deep link. Right rail hiện trên Trạm cổng và Thống kê; ẩn trên Quản lý phiên và Cấu hình để bảng rộng hơn.

Ma trận quyền hành động (frontend ẩn hiện theo vai, backend vẫn là nơi chốt quyền):

| Hành động | staff | admin |
|---|---|---|
| Xác nhận vào và ra, sửa biển, nhập tay hoàn toàn | có | có |
| Xem danh sách và chi tiết phiên, tra cứu | có | có |
| Xem ảnh bằng chứng khi xử lý dispute (ghi audit) | có | có |
| Xử lý và resolve dispute cơ bản | có | có |
| Sửa bảng giá, CRUD tài khoản, cấu hình lane và toggle | không | có |
| Báo cáo doanh thu và xuất CSV | xem cơ bản | đầy đủ, xuất CSV |

## 5. Các màn hình

App kiosk edge gồm các màn 5.1 tới 5.9; màn 5.10 thuộc app dashboard cloud. Mỗi màn nêu: bố cục theo SnowUI, endpoint dùng, và trạng thái cần vẽ. Các màn có nhãn **v2** là bổ sung theo kiến trúc mới.

### 5.1 Đăng nhập

* Bố cục split tối kiểu SnowUI: nửa trái nền tối cộng khối gradient trang trí và logo; nửa phải thẻ kính chứa form.
* Trường `username`, `password` (có nút hiện ẩn), nút primary có trạng thái loading, link Quên mật khẩu (ngoài phạm vi MVP, để tĩnh).
* Endpoint: `POST /auth/login` trả JWT chứa vai. Lưu token, đọc vai, điều hướng theo vai. Sai thì báo lỗi rõ, focus lại trường đầu.

### 5.2 Trạm cổng kiosk (v2, màn chính edge, realtime)

Màn này chạy trên kiosk edge, thân thiện cảm ứng, hoạt động offline. Bố cục kiểu Overview SnowUI:

* Thanh ngữ cảnh trên cùng: bãi đang trực, tầng hoặc khu (nếu bãi nhiều tầng), ca hiện tại và nhân viên. Chọn bãi và tầng lấy từ danh mục đồng bộ; edge chỉ hiện bãi của mình.
* Hàng KPI pastel: Đang trong bãi, Chỗ trống (theo sức chứa bãi và tầng), Vào hôm nay, Ra hôm nay, Doanh thu ca. Khi gần đầy đổi màu cảnh báo; đầy bãi hiện chặn vào rõ ràng.
* Bộ chọn hướng Vào và Ra, cho trường hợp một webcam dùng chung phân hướng bằng nút bấm của nhân viên.
* **Khung webcam trực tiếp (v2):** dùng `getUserMedia` với bộ chọn camera (select camera). Nhân viên bấm Check in hoặc Check out, client lấy khung hình rồi POST ảnh về endpoint suy luận của backend edge; backend chạy pipeline và trả `CaptureResponse` (biển, `plate_valid`, màu `color`, loại xe `vehicle_type`, nhóm phí `vehicle_group`, `review_state`). Hiện trạng thái đang xử lý (spinner, mục tiêu dưới 2 giây). Mất webcam hoặc suy luận lỗi thì lùi nhập tay hoàn toàn.
* Hai cột: trái là khung webcam cộng meta pipeline trong `CaptureResponse`; phải là panel quyết định vẽ theo `review_state`. Các trường tin cậy chi tiết (`det_conf`, `ocr_conf`, `vehicle_style`, `layout`) không hiển thị; tín hiệu đã gói trong `review_state`.
* **Sau khi xác nhận (v2):** nếu đủ điều kiện, phát tín hiệu mở barie (backend gọi thiết bị), phát tiếng loa báo, và với hướng Ra thì mở bước thu tiền (mục 5.6). Nút mở barie thủ công kèm ô lý do, ghi audit; nút mở khẩn cấp tách riêng màu `--st-red`.
* Kiểm vé tháng và danh sách trắng đen chạy tại chỗ trên bản sao cục bộ: xe có vé tháng hoặc danh sách trắng hiện nhãn miễn phí; xe danh sách đen hiện cảnh báo nổi bật.
* Cảnh báo không chặn: `plate_valid == false` hiện cảnh báo sai định dạng nhưng vẫn cho xác nhận; `CaptureResponse.duplicate == true` (biển trùng một session đang trong bãi) hiện cảnh báo, không chặn.
* Right rail: feed Sự kiện cổng realtime, mỗi dòng có dot màu theo `review_state`.

Bốn trạng thái panel quyết định (client không tự tính ngưỡng, chỉ render theo `review_state`):

| `review_state` | Màu, icon | Hành động, endpoint (theo hợp đồng thật) |
|---|---|---|
| `confident` | xanh, dấu tích | Xác nhận VÀO `POST /sessions/entry` với `{reading_id}`; Xác nhận RA `POST /sessions/exit` với `{reading_id}`, `ExitResult.outcome` khớp thì hiện phí tạm tính rồi đóng |
| `needs_review` | hổ phách, cảnh báo | Ô biển highlight, sửa biển `PATCH /readings/{id}/plate`; gọi `POST /sessions/exit {reading_id}`, nếu `ExitResult.candidates` (danh sách `SessionBrief`) không rỗng thì hiện cho nhân viên chọn, chọn xong gọi lại `POST /sessions/exit {reading_id, session_id}` để nối và tính phí |
| `disputed` | đỏ, dấu chéo | `ExitResult.outcome` tranh chấp (không có candidate); hiện ảnh vào và ra cạnh nhau để đối chiếu (`GET /images/{id}`, ghi audit); nhập phí tay; `POST /sessions/{id}/dispute` và endpoint resolve |
| `manual` | tím, bút | Ép gõ biển cộng chọn nhóm xe; `POST /sessions/manual` với `{action, plate_text, vehicle_group, session_id?}` |

Luôn hiện: nút Nhập tay hoàn toàn (bỏ khớp AI) và ô sửa biển. Tắt `read_plate` thì màn cổng ép nhập tay. Idempotent theo `capture_id` để không nhân đôi.

### 5.3 Quản lý phiên

Bố cục kiểu Order List SnowUI:

* Thanh công cụ: thêm, filter, sort, và ô Search tra biển.
* Bảng (TanStack Table, phân trang server `GET /sessions`): biển số (tabular), nhóm xe, giờ vào, giờ ra, thời lượng, phí, chip trạng thái dạng dot (`in_lot`, `completed`, `disputed`, `pending_manual`), `match_flag`.
* Lọc theo biển (tra qua `plate_hash` chuẩn hóa) và theo `status`. Pagination pill.
* Chi tiết `GET /sessions/{id}` (`SessionDetail`): `plate_text`, `vehicle_type` và `vehicle_group`, `entry_time` và `exit_time`, `fee_amount`, `match_flag`, cờ `warning`, cùng `entry_reading` và `exit_reading` (`ReadingBrief`: `plate_text`, `review_state`, `image_asset_id`). Ảnh vào và ra qua `GET /images/{id}`, mỗi lần xem ghi audit. Xử lý dispute và resolve tại đây.
* Ghi chú hợp đồng: các trường bằng chứng chi tiết (`det_conf`, `ocr_conf`, `color_conf`, `vehicle_style`, `layout`) được backend lưu nhưng chưa expose trong response hiện tại. Muốn hiển thị trong màn chi tiết thì cần mở rộng schema `SessionDetail` hoặc `ReadingBrief` phía backend, nằm ngoài phạm vi frontend MVP.

### 5.4 Thống kê

Bố cục kiểu Overview cộng eCommerce SnowUI:

* Hàng KPI pastel: Đang trong bãi, Lưu lượng hôm nay, Doanh thu hôm nay, Tỷ lệ khớp exact.
* Line chart lưu lượng theo giờ và ngày (đường liền năm nay, đường đứt so sánh). Donut cơ cấu nhóm xe. Bar doanh thu theo ngày.
* Bộ chọn khoảng ngày. Nút Xuất CSV `GET /stats/export` (chỉ admin).
* Số liệu từ `GET /stats`. Mỗi biểu đồ có empty state, loading skeleton, và bảng số thay thế cho screen reader.

### 5.5 Cấu hình (v2, chỉ admin)

Bố cục kiểu Account SnowUI, tab ngang. Cấu hình master (bãi/tầng/khu, bảng giá, người dùng, vé tháng, danh sách trắng đen) do cloud là nguồn sự thật; kiosk edge hiển thị bản sao đồng bộ, chỉnh trực tiếp ở dashboard cloud. Ở edge cho phép chỉnh cục bộ khi mất mạng những mục edge được ủy quyền (ví dụ lane, toggle), đồng bộ lại khi có mạng.

* Bãi và không gian (v2): CRUD `parking_lot`, `floor`, `zone`; sức chứa mỗi bãi và tầng và khu.
* Bảng giá: CRUD `price_rule` (nhóm, mode flat hoặc block, đơn giá, block_minutes); mở rộng grace period và lịch giá theo thời gian.
* Tài khoản: CRUD user, vai (admin tổng, quản lý bãi, thu ngân, người xem), kích hoạt, đổi mật khẩu; phân công nhân viên theo bãi.
* Thiết bị và lane: `rtsp_url`, barie, bảng đèn, kích hoạt, trạng thái nhịp sống.
* Feature toggle: ba switch `read_plate`, `plate_color`, `vehicle_class`. Tắt `read_plate` thì cổng ép nhập tay.
* Sửa xác nhận trước khi lưu; hành động nguy hiểm tách riêng, màu `--st-red`.

### 5.6 Thu tiền và biên lai (v2, edge)

Bước sau xác nhận Ra ở trạm cổng, hoặc mở từ chi tiết phiên.

* Hiện phí tính từ `ExitResult`; chọn phương thức (tiền mặt, QR, ví); ghi nhận đã thu, tạo bản ghi `payment`. Miễn phí với vé tháng hoặc danh sách trắng, hiện rõ lý do miễn.
* In hoặc hiện biên lai (mã phiên, biển che một phần, thời lượng, phí, phương thức, thời điểm, nhân viên).
* Điều chỉnh hoặc hoàn tiền tách riêng, cần xác nhận, ghi audit.

### 5.7 Ca trực và đối soát (v2, edge)

* Mở ca: nhập tiền đầu ca; đóng ca: nhập tiền cuối ca.
* Bảng đối soát cuối ca: số xe vào và ra trong ca, tổng tiền hệ thống ghi nhận so với tiền thực đếm, chênh lệch làm nổi bật.
* Báo cáo doanh thu theo ca và theo nhân viên; bàn giao ca.

### 5.8 Sức chứa và chiếm dụng (v2, edge)

* Thẻ số lớn: đang trong bãi, chỗ trống, phần trăm lấp đầy theo bãi và theo từng tầng và khu.
* Trực quan theo tầng và khu (thanh hoặc lưới), ngưỡng gần đầy và đầy đổi màu kèm nhãn chữ.
* Nguồn số từ đếm chiếm dụng thời gian thực của edge; cập nhật qua realtime cổng.

### 5.9 Sự cố (v2, edge)

* Danh sách và tạo sự cố: loại (va chạm, mất xe, hư hỏng, khác), mô tả, ảnh đính kèm, nhân viên, thời điểm, liên kết phiên nếu có.
* Nhật ký mở barie thủ công và mở khẩn cấp kèm lý do, phục vụ đối chiếu và audit.

### 5.10 Dashboard cloud đa bãi (v2, tầng cloud, tách bề mặt)

Bề mặt riêng cho admin tổng và chủ đầu tư, không chạy ở kiosk edge:

* Tổng quan nhiều bãi: sức chứa, doanh thu, lưu lượng theo từng bãi và toàn hệ thống.
* Tra cứu liên bãi: một biển từng vào bãi nào, khi nào (tôn trọng kiểm soát truy cập và audit theo mục 10).
* Báo cáo tổng: doanh thu theo bãi, theo ca, theo nhân viên; giờ cao điểm; vòng quay; thời lượng trung bình; đối soát.
* Quản trị master: bãi/tầng/khu, bảng giá, người dùng và phân công theo bãi, vé tháng, danh sách trắng đen, chủ xe.
* Trạng thái đồng bộ và sức khỏe thiết bị mỗi bãi (bãi nào offline, camera nào lỗi, lần đồng bộ gần nhất).

## 6. Realtime cổng

* Kênh chính: `WS /ws/gate`. Client mở kết nối khi vào màn cổng, nghe sự kiện capture mới, cập nhật panel quyết định và feed right rail.
* Fallback: mất WebSocket thì chuyển polling `GET /captures/latest`, hiện banner cảnh báo chế độ dự phòng.
* Idempotency theo `capture_id` để không nhân đôi khi mạng chập chờn.
* WS nằm ngoài OpenAPI nên nối tay một hook `useGateSocket`, tách khỏi lớp orval.

## 7. Lớp dữ liệu

* Dùng hook React Query sinh sẵn theo tag: `auth`, `sessions`, `readings`, `captures`, `stats`, `config`, `images`, `users`.
* JWT gắn tự động qua `src/api/axios-instance.ts`. Hết hạn hoặc 401 thì xóa token, chuyển `/login`.
* Mọi truy vấn có ba trạng thái: loading (skeleton), error (thông báo cộng nút thử lại), empty (thông điệp cộng gợi ý). Không để màn trắng.
* Mutation có trạng thái submit và toast kết quả; hành động phá hủy có dialog xác nhận.

## 8. Biểu đồ

* Thư viện Recharts. Bảng màu lấy từ chuỗi màu biểu đồ mục 2.2, không dùng cặp đỏ và lục làm tín hiệu duy nhất.
* Line cho chuỗi thời gian (lưu lượng theo giờ và ngày), bar cho doanh thu, donut cho cơ cấu nhóm xe.
* Mỗi biểu đồ: legend gần biểu đồ, tooltip khi hover và khi focus bàn phím, bảng số thay thế, tôn trọng `prefers-reduced-motion`, định dạng số theo locale vi-VN.

## 9. Khả năng tiếp cận (accessibility)

* Tương phản chữ đạt tối thiểu 4.5:1 ở cả hai chế độ; kiểm riêng chế độ tối, không suy ra từ chế độ sáng.
* Focus ring rõ trên mọi phần tử tương tác. Thứ tự tab khớp thứ tự thị giác.
* Nút chỉ icon phải có `aria-label`. Trạng thái luôn kèm icon và chữ, không chỉ màu.
* Target chạm màn cổng tối thiểu 44px. Tôn trọng `prefers-reduced-motion`. Toast dùng `aria-live` lịch sự, không cướp focus.

## 10. Quyền riêng tư và pháp lý trên giao diện

Theo Luật Bảo vệ dữ liệu cá nhân hiệu lực 01/01/2026:

* Ảnh bằng chứng chỉ hiện khi cần đối chiếu dispute; mỗi lần xem gọi `GET /images/{id}` và backend ghi audit. Giao diện nêu rõ việc truy cập ảnh được ghi lại.
* Không có bất kỳ tính năng xử lý khuôn mặt nào trên frontend; không import thư viện nhận diện khuôn mặt.
* Biển số hiển thị từ dữ liệu backend đã giải mã theo phiên; frontend không lưu biển vào bộ nhớ ngoài vòng đời phiên làm việc.
* Màn Cấu hình và Nhật ký giúp admin thấy được truy cập dữ liệu nhạy cảm, phục vụ chứng minh tuân thủ.
* Minh bạch hạn lưu trữ: giao diện nêu rõ hạn lưu trữ (30 ngày sau khi xe ra) ở màn chi tiết phiên và mục Cấu hình, để người dùng biết dữ liệu tự xóa sau thời hạn.

## 11. Cấu trúc thư mục frontend và quy ước

```
src/frontend/src/
  api/                # orval sinh sẵn (giữ nguyên) + axios-instance.ts
  app/                # router, providers (QueryClient, theme), guard theo vai
  theme/              # biến CSS token SnowUI, cấu hình Tailwind, ThemeProvider sáng/tối
  components/         # AppShell, Sidebar, Topbar, RightRail, KpiTile, DataTable, StatusChip, PlateField, charts, ui (shadcn)
  features/
    auth/             # màn đăng nhập, lưu token, guard, cache đăng nhập offline
    gate/             # Trạm cổng kiosk, useWebcam (getUserMedia, select camera), gọi suy luận backend, useGateSocket, panel theo review_state
    payment/          # thu tiền, biên lai, hoàn và điều chỉnh (v2)
    shift/            # mở đóng ca, đối soát cuối ca (v2)
    capacity/         # sức chứa và chiếm dụng theo bãi, tầng, khu (v2)
    incidents/        # sự cố, nhật ký mở barie (v2)
    sessions/         # bảng, chi tiết, dispute
    stats/            # KPI, biểu đồ, xuất CSV
    config/           # bãi/tầng/khu, bảng giá, tài khoản, thiết bị, toggle (v2)
  # App dashboard cloud đa bãi là bundle riêng, cùng theme và component, nav đa bãi (mục 5.10)
  lib/                # định dạng số ngày, tiện ích
```

* Một component một mục đích. File phình to là dấu hiệu nên tách.
* Chữ hiển thị tiếng Việt. Chưa cần i18n cho MVP.
* Test: Vitest cộng React Testing Library cho logic then chốt (guard theo vai, render panel theo `review_state`, định dạng phí). Không phủ test toàn bộ trong MVP.

## 12. Phạm vi và phân pha

Thứ tự dựng, mỗi pha chạy được và review được:

1. Nền tảng: Vite, Tailwind, token SnowUI, ThemeProvider sáng và tối, AppShell, Sidebar, Topbar, router, guard, tích hợp orval và QueryClient.
2. Đăng nhập cộng luồng xác thực (guard theo vai, xử lý 401).
3. Trạm cổng: KPI, khung webcam `getUserMedia` cộng select camera, gọi suy luận backend edge, panel bốn `review_state`, ô sửa biển, nhập tay hoàn toàn, right rail feed (v2).
4. Realtime: `useGateSocket`, fallback polling.
5. Quản lý phiên: bảng phân trang server, lọc, chi tiết cộng ảnh cộng dispute.
6. Thu tiền và ca trực: biên lai, mở đóng ca, đối soát (v2).
7. Sức chứa và sự cố: thẻ chiếm dụng theo bãi tầng khu, nhật ký sự cố và mở barie (v2).
8. Thống kê: KPI, ba biểu đồ, xuất CSV.
9. Cấu hình: các tab CRUD gồm bãi/tầng/khu, bảng giá, tài khoản, thiết bị, toggle (chỉ admin, v2).
10. Rà a11y (mục 9), rà tương phản hai chế độ, đóng gói app kiosk edge (nginx trên Pi, Chromium kiosk) cộng biến `VITE_API_BASE`.

Thứ tự và phạm vi backend tương ứng theo spec kiến trúc tổng, mục 10 (edge trước, cloud sau). App dashboard cloud đa bãi (mục 5.10) là track riêng, dựng ở pha cloud sau khi Sync API sẵn sàng.

## 13. Ngoài phạm vi (v2)

Đưa vào phạm vi so với v1: đa bãi và đa camera, vé tháng và cư dân, thu tiền và ca trực, sức chứa, điều khiển barie. Vẫn ngoài phạm vi, giữ hướng mở rộng: i18n đa ngôn ngữ, biểu đồ nâng cao và drill down, thông báo đẩy trình duyệt, đầu đọc QR và máy in vé vật lý, theo dõi mức từng chỗ đỗ, tùy biến theme ngoài sáng và tối, màn quên mật khẩu thật.

## Bảng token tổng hợp (đầu vào khi hiện thực)

| Nhóm | Giá trị |
|---|---|
| Font | Inter 400 500 600 700; tabular-nums cho cột số |
| Bo góc | card 16px, nút và input 8px, chip tròn |
| Nền sáng | bg `#FFFFFF`, surface `#F7F9FB` |
| Nền tối | bg `#1C1C1C`, surface `rgba(255,255,255,0.05)` |
| Primary | sáng `#1C1C1C`, tối `#95A4FC` |
| Pastel tile | `#E3F5FF`, `#E5ECF6`, `#DEF8EE`, `#EDF0FF` |
| Chart | `#95A4FC`, `#C6C7F8`, `#A1E3CB`, `#B1E3FF`, `#A8C5DA`, `#1C1C1C` |
| Trạng thái | green `#1F9D63`, purple `#7A7CD6`, blue `#2E8BC0`, amber `#B98900`, red `#D24A3E` |
| Stack | Vite, React 18, TS, React Router v6, TanStack Query và Table, shadcn/ui, Tailwind, Radix, Recharts, lucide-react, RHF cộng Zod |
