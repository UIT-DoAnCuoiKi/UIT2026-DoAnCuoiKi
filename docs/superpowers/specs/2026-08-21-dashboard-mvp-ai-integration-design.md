# Thiết kế kỹ thuật: tích hợp AI pipeline vào Dashboard MVP

- **Ngày:** 2026-08-21
- **Người phụ trách:** Lê Quang Hoài Đức (25410034)
- **Trạng thái:** Draft (chờ review)
- **Tài liệu liên quan:** `docs/design/dashboard-mvp-spec.md` (spec sản phẩm mức cao), `docs/design/dashboard-mvp-brainstorm-prompt.md` (bộ câu hỏi định hướng)
- **Phạm vi:** phần thành phần và hợp đồng dữ liệu (backend, DB, logic, API, edge). Giao diện cụ thể do người phụ trách tự dựng; tài liệu này chỉ mô tả màn hình bằng "cần endpoint nào, có trạng thái nào".

## 0. Bối cảnh và mục tiêu

Hệ thống quản lý bãi đỗ xe thông minh dùng computer vision và edge AI (đồ án tốt nghiệp UIT). AI pipeline đã chạy được ở `src/ml` (`src/ml/e2e_pipeline_test.py`). Backend, frontend, edge chưa có gì. Tài liệu này chốt cách nối pipeline với backend, DB và dashboard cho MVP một lane, chạy PC trước rồi lên Raspberry Pi 5, mục tiêu độ trễ dưới 2 giây mỗi xe.

Nguyên tắc bắt buộc từ spec sản phẩm: luôn có đường lùi nhập tay hoàn toàn khi AI lỗi; ô sửa tay biển số luôn hiện; session nghi vấn chuyển `disputed`, không tự tính phí.

## 1. Kiến trúc và thành phần

Bốn thành phần, ranh giới rõ:

- **Edge worker (Python):** chụp khung hình, chạy pipeline `src/ml`, đóng gói một `capture` gồm ảnh, dict pipeline, `capture_id`, `direction`, `lane`, rồi POST multipart về backend. Có hàng đợi cục bộ; mất mạng thì lưu tạm và gửi lại. Nén ảnh JPEG vừa phải trước khi gửi. Không giữ trạng thái nghiệp vụ.
- **Backend (FastAPI):** nhận capture, chạy logic nghiệp vụ (ngưỡng soát, khớp phiên, tính phí), lưu PostgreSQL, xác thực, cấu hình, đẩy sự kiện nhận diện qua WebSocket, phục vụ REST. Không giữ model AI.
- **PostgreSQL:** lưu trữ.
- **Frontend React:** client thuần, tiêu thụ REST và WebSocket. Giao diện do người phụ trách tự dựng.

Môi trường dev PC: một script giả lập edge worker đọc ảnh từ thư mục và POST về backend, cho phép chạy toàn luồng trước khi có Pi.

**Luồng dữ liệu:** camera đưa khung hình cho edge worker; edge worker chạy pipeline rồi gọi `POST /captures`; backend lưu `plate_reading` cộng `image_asset`, chạy khớp và tính ngưỡng, đẩy sự kiện qua WebSocket tới màn cổng; nhân viên xác nhận qua REST; backend tạo hoặc đóng session.

## 2. Hợp đồng dữ liệu: pipeline sang nghiệp vụ

- **Biển đại diện:** chọn phần tử trong `plates` có `det_conf` cao nhất. Nếu 0 biển thì tạo `plate_reading` với trạng thái chờ nhập tay.
- **Ngưỡng soát:** `ocr_conf < 0.7` hoặc `plate_valid == false` hoặc `det_conf` dưới ngưỡng thấp thì gắn cờ cần soát, highlight ô sửa tay, không chặn xác nhận. `plate_valid == false` chỉ cảnh báo, không chặn.
- **review_state:** backend tự tính một trường `review_state` cho mỗi reading, nhận một trong bốn giá trị `confident`, `needs_review`, `disputed`, `manual`. Frontend chỉ việc render theo giá trị này, không nhồi logic ngưỡng vào client.
- **Trường lưu làm bằng chứng và báo cáo:** `det_conf`, `ocr_conf`, `color`, `color_conf`, `layout`, `vehicle_type`, `vehicle_style`, `vehicle_style_conf`, `plate_text`, `plate_valid`, và bbox.
- **Map nhóm phí từ `vehicle_type`:**
  - `motorbike`, `bicycle` thành nhóm `xe_may`
  - `car` thành nhóm `o_to_con`
  - `truck` thành nhóm `xe_tai`
  - `bus` thành nhóm `xe_khach`
- `vehicle_style` (sedan, SUV) chỉ để hiển thị và thống kê, không ảnh hưởng phí.

## 3. Mô hình dữ liệu

Bảng tối thiểu:

- `users`: `id`, `username`, `password_hash`, `role` (`staff` hoặc `admin`), `active`, `created_at`.
- `price_rule`: `id`, `vehicle_group`, `mode` (`flat` hoặc `block`), `unit_price`, `block_minutes` (null khi `flat`), `active`, `updated_by`, `updated_at`.
- `session`: `id`, `plate_hash`, `plate_ciphertext`, `vehicle_group`, `vehicle_type`, `status` (`in_lot`, `pending_manual`, `completed`, `disputed`), `entry_time`, `exit_time`, `entry_reading_id`, `exit_reading_id`, `fee_amount`, `fee_rule_snapshot` (JSON), `match_flag` (`exact`, `auto_corrected`, `manual`), `created_by`, `closed_by`, `created_at`, `updated_at`.
- `plate_reading`: `id`, `capture_id` (UNIQUE, khóa idempotent), `direction` (`in` hoặc `out`), `plate_text_ciphertext`, `plate_hash`, `plate_valid`, `det_conf`, `ocr_conf`, `layout`, `color`, `color_conf`, `vehicle_type`, `vehicle_style`, `vehicle_style_conf`, `raw_pipeline_json` (tùy chọn), `image_asset_id`, `review_state`, `created_at`.
- `image_asset`: `id`, `path`, `encrypted`, `sha256`, `direction`, `created_at`, `retention_delete_after`.
- `audit_log`: `id`, `user_id`, `action`, `entity_type`, `entity_id`, `detail`, `created_at`.
- Cấu hình: `lane` (`id`, `name`, `rtsp_url`, `active`) và `feature_toggle` (`read_plate`, `plate_color`, `vehicle_class` dạng boolean).

Quy tắc lưu trữ:

- Biển lưu hai dạng: `plate_ciphertext` (mã hóa tầng cột, để hiển thị) cộng `plate_hash = HMAC(biển đã chuẩn hóa)`. Chuẩn hóa nghĩa là viết hoa và bỏ ký tự phân tách. Tra khớp dựa trên `plate_hash` nên không cần giải mã hàng loạt.
- Ảnh bằng chứng: file mã hóa trên đĩa; DB giữ đường dẫn cộng khóa tham chiếu. Không lưu ảnh dạng bytea trong Postgres.
- Trạng thái session dùng đủ bốn giá trị, có `pending_manual` tách khỏi `in_lot` để phân biệt xe đã vào nhưng chưa đủ dữ liệu biển.
- Hạn lưu trữ: 30 ngày sau `exit_time`.

## 4. Logic in/out và khớp phiên

- **Xe vào:** nhân viên xác nhận thì tạo session `in_lot` ngay. Nếu biển trùng một session đang trong bãi thì cảnh báo nhưng không chặn, vì biển đọc nhầm là trường hợp thật.
- **Xe ra, khớp biển:**
  1. Chuẩn hóa biển vừa đọc.
  2. Khớp `plate_hash` chính xác trong tập session `in_lot`. Trúng thì nối, `match_flag = exact`.
  3. Trượt thì tính edit distance trên biển chuẩn hóa với các ứng viên `in_lot`, lọc theo cùng `vehicle_group`. `color` chỉ dùng tham khảo vì có thể sai.
  4. Nếu đúng một ứng viên và `k <= 1` thì tự nối, `match_flag = auto_corrected`.
  5. Nếu ứng viên ở `k == 2` hoặc có nhiều ứng viên thì đưa danh sách ứng viên cho nhân viên chọn (`review_state = needs_review`). Chọn xong thì nối, `match_flag = manual`.
  6. Nếu không ứng viên nào thì chuyển `disputed`, không tự tính phí; nhân viên đối chiếu ảnh vào và ra bằng mắt.
- **Nhập tay hoàn toàn (AI lỗi):** đi qua cùng endpoint xác nhận nhưng bỏ bước khớp AI. Nhân viên gõ biển và chọn nhóm xe; session tạo hoặc đóng thủ công, `match_flag = manual`.

## 5. Tính phí

- Tính theo `price_rule` của `vehicle_group` của session, đọc bảng giá tại thời điểm xe ra.
  - `mode = flat`: một giá trọn lượt.
  - `mode = block`: `ceil(thời_gian_gửi / block_minutes) * unit_price`, làm tròn lên, không grace period.
- Mặc định MVP: nhóm `xe_may` dùng `flat`; nhóm `o_to_con`, `xe_tai`, `xe_khach` dùng `block` 60 phút. Admin sửa được trong màn Cấu hình.
- Màu biển không ảnh hưởng giá trong MVP (ghi vào hướng mở rộng).
- Session `disputed`: nhân viên nhập phí tay.
- Lưu `fee_rule_snapshot` vào session để ghi rõ giá đã áp, tránh tranh cãi khi bảng giá đổi.

## 6. Thiết kế API (FastAPI)

- `POST /captures`: multipart gồm ảnh, dict pipeline (JSON), `capture_id`, `direction`, `lane`. Idempotent theo `capture_id`. Trả reading vừa tạo cộng gợi ý khớp và `review_state`. Đẩy sự kiện qua WebSocket.
- `POST /sessions/entry`: xác nhận xe vào (từ `reading_id` hoặc payload nhập tay), tạo `in_lot`.
- `POST /sessions/exit`: xác nhận xe ra kèm session được chọn nối, tính phí, chuyển `completed`.
- `POST /sessions/manual`: nhập tay hoàn toàn cho luồng AI lỗi.
- `PATCH /readings/{id}/plate`: sửa biển tay (ghi audit).
- `POST /sessions/{id}/dispute` và endpoint resolve dispute.
- `GET /sessions`: danh sách, lọc theo `plate_hash` và `status`, phân trang phía server.
- `GET /sessions/{id}`: chi tiết cộng ảnh vào và ra.
- `GET /images/{id}`: chặn xác thực, ghi audit mỗi lần truy cập.
- `GET /stats`: số xe trong bãi, lưu lượng theo giờ và ngày, doanh thu theo khoảng. Truy vấn thẳng DB.
- `GET /stats/export`: xuất CSV theo khoảng thời gian (doanh thu và lưu lượng), chỉ admin. Phục vụ buổi bảo vệ.
- CRUD `/price-rules`, `/users`, `/lanes`, `/feature-toggles`.
- `POST /auth/login`: trả JWT chứa vai.
- `WS /ws/gate`: đẩy sự kiện nhận diện mới tới màn cổng. Fallback `GET /captures/latest` khi WebSocket rườm rà.

Chọn transport: WebSocket cộng fallback polling. Idempotency dựa trên `capture_id` để chống nhân đôi khi mạng chập chờn.

## 7. Ghép dữ liệu vào 5 màn hình (hợp đồng, không bố cục)

- **Trạm kiểm soát (cổng):** nghe `WS /ws/gate`, gọi các endpoint xác nhận và sửa biển. Bốn trạng thái vẽ riêng (chắc chắn, cần soát, tranh chấp, AI lỗi) lấy thẳng từ `review_state` backend trả, frontend không tự tính ngưỡng.
- **Quản lý và tra cứu:** `GET /sessions` (lọc, phân trang), `GET /sessions/{id}`, `GET /images/{id}`. Tra theo biển dùng cột `plate_hash` đã chuẩn hóa.
- **Báo cáo thống kê:** `GET /stats` cho các con số, `GET /stats/export` cho CSV. Realtime truy vấn thẳng DB, tối ưu sau nếu chậm.
- **Xác thực và phân quyền:** `POST /auth/login`, vai nằm trong JWT.
- **Cấu hình:** các endpoint CRUD, chỉ admin.

## 8. Cấu hình và feature toggle

- Ba toggle `read_plate`, `plate_color`, `vehicle_class` lưu ở backend.
- Edge worker đọc cấu hình lúc khởi động và làm mới định kỳ. Tắt feature nào thì edge bỏ chạy bước đó để tiết kiệm tài nguyên Pi.
- Tắt `read_plate` thì màn cổng chuyển sang bắt buộc nhập tay biển.
- URL RTSP theo lane lưu ở backend, đẩy xuống edge worker.
- Đổi cấu hình áp ở lần capture kế tiếp, không cần restart edge worker.

## 9. Xác thực và phân quyền

- **staff:** xác nhận vào và ra, sửa biển, nhập tay, xem session, xử lý dispute cơ bản, xem ảnh khi xử lý dispute (ghi audit).
- **admin:** thêm quyền sửa bảng giá, tạo và khóa và đổi mật khẩu tài khoản, cấu hình RTSP và toggle, xem báo cáo doanh thu đầy đủ, xuất CSV.
- Ghi `audit_log` mọi lần xem ảnh, sửa biển, xóa dữ liệu, và đăng nhập.

## 10. Bảo mật và quyền riêng tư (Luật hiệu lực 01/01/2026)

- Mã hóa tầng cột cho biển và ảnh trước khi ghi (application encrypt), không tin vào mã hóa đĩa.
- Khóa mã hóa nạp từ biến môi trường, không nằm trong repo, không hardcode trong code.
- Job tự xóa chạy hàng ngày: sau 30 ngày kể từ `exit_time`, xóa session, các `plate_reading` liên quan, và file ảnh; ghi audit việc xóa.
- Cấm tuyệt đối mọi xử lý khuôn mặt tự động. Không import model nhận diện khuôn mặt. Ghi thành quy tắc trong tài liệu và soát khi review code. Ảnh chỉ để nhân viên đối chiếu bằng mắt khi có tranh chấp.
- Truy cập ảnh bằng chứng yêu cầu đăng nhập và bị ghi audit.

## 11. Tích hợp edge (Raspberry Pi 5)

- Edge worker có hàng đợi cục bộ. Mất kết nối backend thì lưu tạm capture và gửi lại sau. Màn cổng vẫn cho nhập tay hoàn toàn để không nghẽn.
- Ảnh nén vừa phải trước khi gửi để tiết kiệm băng thông và dung lượng lưu.
- MVP chạy PC trước bằng script giả lập edge worker đọc ảnh thư mục và POST về backend. Lên Pi mới bàn ONNX và lượng tử hóa; pipeline hiện dùng plate detector bản `.pt`, chưa export `.onnx`.
- Đo latency từng bước (detect, OCR, color, gửi mạng) để tìm nút cổ chai, mục tiêu dưới 2 giây mỗi xe.

## 12. Triển khai bằng Podman

Mục tiêu: đóng gói mỗi thành phần thành image, chạy PC bằng `podman compose`, và build được image edge worker cho Pi (arm64).

**Container hóa từng thành phần:**

- `backend`: image Python cộng FastAPI (uvicorn). Đọc cấu hình DB và khóa mã hóa từ biến môi trường.
- `db`: image PostgreSQL chính thức, gắn volume lưu bền dữ liệu.
- `frontend`: build React tĩnh, phục vụ qua nginx. Khi phát triển có thể chạy dev server thay thế.
- `edge-worker`: image chứa pipeline `src/ml`. Trên PC đóng vai script giả lập đọc thư mục ảnh; trên Pi chạy thật với camera. Build multi-arch: amd64 cho PC, arm64 cho Pi.

**Compose cho PC:** một file `podman-compose.yml` chạy `backend`, `db`, `frontend`, và `edge-worker` giả lập trên cùng một network nội bộ. `edge-worker` nhận URL backend qua biến môi trường.

**Volume và dữ liệu bền:**

- Volume riêng cho dữ liệu PostgreSQL.
- Volume riêng cho thư mục ảnh mã hóa, tách khỏi container để ảnh và job xóa theo hạn lưu trữ vẫn đúng khi rebuild.

**Khóa và bí mật:** khóa mã hóa và mật khẩu DB nạp qua biến môi trường hoặc file `.env` nằm ngoài version control, không bake vào image, không commit. Có thể dùng podman secrets.

**Cấu hình theo môi trường:** biến môi trường phân biệt PC và Pi (URL backend, đường dẫn model, chọn camera thật hay thư mục ảnh). Image edge worker trên Pi cần map thiết bị camera và model; MVP dùng bản `.pt`, bản ONNX lượng tử hóa thêm sau.

**Khởi động và healthcheck:** backend chờ `db` sẵn sàng (healthcheck hoặc `depends_on` cộng retry kết nối). Job xóa theo hạn lưu trữ chạy trong tiến trình backend hoặc một service scheduler riêng trong compose.

**Lưu ý Pi:** ultralytics và Torch trên arm64 nặng. Nếu container quá nặng thì chạy edge worker trực tiếp trên Pi (không container) là phương án lùi chấp nhận được cho MVP; backend và db vẫn chạy container.

## 13. Ngoài phạm vi MVP

Nằm ngoài MVP, giữ cho hướng mở rộng: vé tháng và cư dân, đối soát theo ca hoặc nhân viên, đa lane đa camera, điều khiển barrier vật lý, giá theo màu biển, nhận diện khuôn mặt (cấm theo luật). MVP tập trung một lane, luồng vào ra, khớp biển, phí, năm màn hình, bảo mật cơ bản, và xuất CSV cho buổi bảo vệ.

## Bảng quyết định đã chốt

| # | Quyết định | Chốt |
|---|---|---|
| 1 | Số lane, số camera, nơi chạy AI | 1 lane; camera vào và ra riêng, thiếu thiết bị thì 1 camera dùng chung phân hướng bằng nút bấm; edge worker chạy pipeline POST JSON cộng ảnh về backend; backend không giữ model; PC trước rồi Pi |
| 2 | Biển đại diện; ngưỡng soát | `det_conf` cao nhất; `ocr_conf < 0.7` hoặc `plate_valid == false` thì cần soát nhưng không chặn; backend trả `review_state` |
| 3 | Lưu và tra biển; nơi lưu ảnh | `plate_ciphertext` cộng `plate_hash` HMAC; ảnh file mã hóa trên đĩa, DB giữ đường dẫn; thêm trạng thái `pending_manual` |
| 4 | Edit distance k; tín hiệu phụ | exact trước; tự nối chỉ khi duy nhất và `k <= 1`; `k == 2` hoặc nhiều ứng viên thì gợi ý cho nhân viên; lọc theo `vehicle_group`, `color` tham khảo |
| 5 | Đơn vị phí; yếu tố giá; thời điểm áp giá | cấu hình mỗi nhóm: `xe_may` flat trọn lượt, `o_to_con` và `xe_tai` và `xe_khach` block 60 phút; áp giá lúc xe ra; lưu `fee_rule_snapshot` |
| 6 | REST cộng WebSocket; cách edge đẩy | REST cho nghiệp vụ; edge POST multipart mỗi capture với `capture_id` idempotent; màn cổng dùng WebSocket cộng fallback polling |
| 7 | Bố cục cổng; thống kê | frontend tự dựng UI; bốn trạng thái từ `review_state`; thống kê realtime truy vấn thẳng; thêm xuất CSV |
| 8 | Toggle tác động ở đâu; áp cấu hình | toggle lưu backend, edge đọc và làm mới định kỳ, tắt thì bỏ bước; tắt OCR thì cổng ép nhập tay; áp ở capture kế, không restart |
| 9 | Ma trận quyền; audit log | staff nghiệp vụ cổng và tra cứu; admin thêm cấu hình, giá, tài khoản, doanh thu, CSV; audit mọi lần xem ảnh và sửa biển |
| 10 | Mã hóa; khóa; job xóa; hạn lưu trữ | mã hóa tầng cột; khóa từ biến môi trường; job xóa hàng ngày cộng ghi audit; hạn lưu trữ 30 ngày; cấm xử lý khuôn mặt |
| 11 | Mất mạng ở cổng; latency; ONNX hay pt | hàng đợi cục bộ gửi lại, cổng vẫn nhập tay; nén ảnh; PC trước bằng script giả lập; ONNX để sau; đo latency từng bước |
| 12 | Phạm vi ngoài MVP | vé tháng, đối soát ca, đa lane, barrier, giá theo màu, nhận diện khuôn mặt nằm ngoài |

## Gợi ý phân pha triển khai

Không phải phần bắt buộc của spec, để tham khảo khi viết plan: (1) schema DB cộng migration cộng lớp mã hóa; (2) API captures cộng logic khớp cộng tính phí với script giả lập edge; (3) auth cộng phân quyền cộng audit; (4) endpoint thống kê cộng CSV; (5) hợp đồng WebSocket cho cổng; (6) job xóa theo hạn lưu trữ; (7) đóng gói `podman compose` cho PC cộng build image edge worker; (8) đưa lên Pi và đo latency.
