# Thiết kế kiến trúc hệ thống quản lý bãi giữ xe: edge tại chỗ + cloud trung tâm

* **Ngày:** 2026-08-23
* **Người phụ trách:** Lê Quang Hoài Đức (25410034)
* **Trạng thái:** Draft (chờ review)
* **Tài liệu liên quan:**
  * `docs/superpowers/specs/2026-08-21-dashboard-mvp-ai-integration-design.md` (hợp đồng dữ liệu backend hiện tại)
  * `docs/superpowers/specs/2026-08-23-frontend-snowui-design.md` (giao diện, được cập nhật v2 theo tài liệu này)
  * `src/backend` (backend single-node hiện có, ánh xạ về tầng edge)
  * `alpr-pipeline` skill, `src/ml` (pipeline nhận dạng của Nhật, tái dùng làm hàm suy luận ở edge)
* **Phạm vi:** Tài liệu kiến trúc tổng, chốt mô hình hai tầng edge và cloud, phân chia trách nhiệm, sở hữu dữ liệu, cơ chế đồng bộ, hoạt động offline, vị trí suy luận ML, danh mục use case đầy đủ (đang có và còn thiếu), các miền dữ liệu mới, và phân pha theo kế hoạch 10 tuần. Không viết code trong tài liệu này. Chi tiết miền backend và giao diện nằm ở các spec con.

## 0. Bối cảnh và lý do thiết kế lại

Backend hiện tại (`src/backend`, 6 phase, 84 test pass) là ứng dụng **một nút, một bãi xe**. Kiểm tra thực tế trên mã nguồn cho thấy ba khoảng trống lớn so với yêu cầu vận hành:

1. **Không có mô hình đa bãi.** Không có thực thể `parking_lot`, `floor`/tầng, `zone`/khu vực ở bất kỳ đâu trong `src/backend/app`. Chỉ có `Lane` phẳng (tên, `rtsp_url`, active). Toàn bộ logic (matching, thống kê, kiểm tra trùng `in_lot`) giả định một bãi duy nhất.
2. **Không có suy luận ML trong backend.** `POST /captures` nhận `payload` đã suy luận sẵn (biển, màu, loại xe) kèm ảnh; không chạy YOLO/OCR/màu. `requirements.txt` không có thư viện ML. Luồng "webcam chụp ảnh rồi backend trả biển/màu/loại" chưa tồn tại.
3. **Kiến trúc một nút, không có tầng trung tâm.** Không có đồng bộ, không có cơ sở dữ liệu trung tâm để tra cứu nhiều bãi, không có hàng đợi offline bền để chịu mất mạng giữa bãi và trung tâm.

Ngoài ba khoảng trống trên, rà soát use case (mục 6) cho thấy thiếu nhiều nghiệp vụ cốt lõi của bãi giữ xe thật: sức chứa và cảnh báo đầy bãi, ghi nhận thanh toán và đối soát ca, điều khiển barie, vé tháng và danh sách trắng đen, xử lý mất vé và quá hạn, giám sát thiết bị.

Mục tiêu tài liệu này: chốt một kiến trúc **edge trước, cloud đồng bộ** giải quyết cả ba khoảng trống và mở đường cho các use case còn thiếu, đồng thời tôn trọng ràng buộc đồ án (mục tiêu edge là Raspberry Pi 5, độ trễ dưới 2 giây mỗi xe, Luật Bảo vệ dữ liệu cá nhân hiệu lực 01/01/2026).

## 1. Kiến trúc mục tiêu: hai tầng

```
Bãi xe A (edge, tại chỗ)          Bãi xe B (edge)             Bãi xe N ...
  Pi 5 kiosk:                       Pi 5 kiosk                  ...
   - webcam, màn hình, chuột,        - ...
     bàn phím, loa
   - Chromium kiosk -> FE (React)
   - FastAPI backend (localhost)
   - ML inference (YOLO+OCR+màu)
   - Postgres cục bộ
   - HOẠT ĐỘNG OFFLINE hoàn toàn
        |  outbox đẩy lên khi có mạng        |
        |  pull config khi có mạng           |
        +-------------------+----------------+
                            v
                    CLOUD (trung tâm)
                     - central DB (toàn hệ thống)
                     - sync API (nhận outbox, phát config)
                     - dashboard đa bãi (chủ đầu tư, admin tổng)
                     - báo cáo tổng hợp, tra cứu liên bãi
```

**Nguyên tắc nền tảng: edge tự chủ.** Một bãi xe phải vận hành đầy đủ khi mất Internet: nhận dạng biển tại chỗ, cho xe vào ra, tính phí, thu tiền, in biên lai, điều khiển barie. Cloud là lớp tổng hợp và quản trị nhiều bãi, không phải đường phụ thuộc bắt buộc cho vận hành hàng ngày.

**Một bãi xe bằng một site edge.** Mỗi bãi chạy trên một thiết bị edge (Pi 5) hoặc một cụm nội bộ. Tầng và khu vực (floor, zone) là phân chia **bên trong** một bãi, do edge theo dõi để đếm sức chứa theo tầng và khu. Khả năng "một hệ thống quản lý nhiều bãi" nằm ở tầng cloud.

**Cloud là nguồn sự thật cho dữ liệu liên bãi.** Edge là nguồn sự thật cho các phiên đang sống của chính nó cộng bản sao làm việc của cấu hình.

### 1.1 Site edge chạy trọn trên một Pi 5 (kiosk)

Cấu hình vật lý một bãi: một Pi 5 (khuyến nghị RAM 8 GB trở lên) gắn màn hình HDMI, webcam USB hoặc CSI, chuột, bàn phím, loa. Pi chạy đồng thời:

* Postgres cục bộ (nhẹ).
* FastAPI backend nghe `localhost`.
* Frontend build tĩnh, phục vụ nội bộ; Chromium chế độ kiosk mở trang trên `http://localhost`.
* Hàm suy luận ML (YOLO detect biển + OCR + phân loại màu, loại xe) bằng ONNX Runtime lượng tử hóa INT8, đạt mục tiêu dưới 2 giây mỗi xe.
* Loa phát tiếng báo khi vào ra.

Vì webcam gắn trực tiếp vào Pi và trình duyệt chạy trên `http://localhost` (localhost là secure context, `getUserMedia` chạy không cần HTTPS), luồng người dùng khớp yêu cầu gốc: nhân viên bấm Check in, trình duyệt lấy khung hình webcam, POST ảnh về backend `localhost`, backend chạy pipeline và trả biển, màu, loại xe. Toàn bộ trên một máy, không cần mạng.

Có thể tách một site edge thành Pi tính toán cộng máy khác chạy dashboard trên cùng LAN; thiết kế không phụ thuộc việc dồn hết vào một Pi, chỉ yêu cầu các thành phần edge nằm cùng mạng nội bộ của bãi.

### 1.2 Tầng cloud

Dịch vụ trung tâm chạy trên máy chủ hoặc VPS, gồm:

* **Central DB:** kho tổng hợp mọi bãi (tổ chức, danh mục bãi/tầng/khu, người dùng và vai trò, bảng giá master, vé tháng, danh sách trắng đen, chủ xe, các phiên và thanh toán đã đồng bộ).
* **Sync API:** nhận batch outbox từ edge (upsert idempotent), phát cấu hình xuống edge.
* **Dashboard đa bãi:** cho chủ đầu tư và admin tổng xem sức chứa, doanh thu, lưu lượng nhiều bãi; tra cứu liên bãi (một biển từng vào bãi nào, khi nào); báo cáo tổng.

Cloud không tham gia đường quyết định vào ra thời gian thực của một xe; đó là việc của edge.

## 2. Phân chia trách nhiệm giữa tầng

| Chức năng | Edge (mỗi bãi) | Cloud (trung tâm) |
|---|---|---|
| Nhận dạng biển, màu, loại xe | Chạy tại chỗ (ML trên Pi) | Không |
| Cho xe vào, ra, tính phí | Có, offline | Không |
| Thu tiền, in biên lai, đối soát ca | Có, offline | Tổng hợp doanh thu sau đồng bộ |
| Kiểm tra vé tháng, danh sách trắng đen | Có, tra bản sao cục bộ offline | Nguồn master, phát xuống edge |
| Điều khiển barie, giám sát thiết bị bãi | Có | Nhận cảnh báo sau đồng bộ |
| Đếm sức chứa theo bãi/tầng/khu | Có, thời gian thực cục bộ | Tổng hợp đa bãi |
| Cấu hình bảng giá, toggle | Bản sao làm việc (pull) | Nguồn master |
| Người dùng và vai trò | Bản sao cache để đăng nhập offline | Nguồn master |
| Tra cứu liên bãi, báo cáo tổng | Không | Có |
| Danh mục bãi/tầng/khu | Chỉ biết bãi của mình | Nguồn master toàn hệ thống |

## 3. Sở hữu dữ liệu và hướng đồng bộ

| Nhóm dữ liệu | Nguồn master | Hướng đồng bộ |
|---|---|---|
| Phiên, lượt đọc biển, phí, ảnh bằng chứng | Edge | Edge đẩy lên cloud |
| Thanh toán, đối soát ca | Edge | Edge đẩy lên cloud |
| Sự cố, log mở barie thủ công | Edge | Edge đẩy lên cloud |
| Bảng giá, feature toggle | Cloud | Cloud phát xuống edge |
| Vé tháng, danh sách trắng, danh sách đen, chủ xe | Cloud | Cloud phát xuống edge |
| Người dùng, vai trò | Cloud | Cloud phát xuống edge |
| Danh mục bãi, tầng, khu | Cloud | Cloud phát xuống edge (edge nhận phần của mình) |
| Báo cáo tổng hợp, tra cứu liên bãi | Cloud (dẫn xuất) | Không đẩy về edge |

Quy tắc: dữ liệu vận hành sinh ở edge chảy **lên**; dữ liệu cấu hình và danh mục quản trị chảy **xuống**. Không có bảng nào ghi hai chiều đồng thời, tránh xung đột ghi.

## 4. Định danh và cơ chế đồng bộ

### 4.1 Định danh chống trùng

Backend hiện dùng khóa chính tự tăng số nguyên ở mọi bảng. Hai bãi đều sinh `session.id = 1` sẽ đụng khi đồng bộ lên cloud. Chuyển sang:

* **Khóa chính UUID** (v4 hoặc ULID để giữ thứ tự thời gian) cho mọi thực thể đồng bộ. Đây là thay đổi cấu trúc, chạm mọi bảng và khóa ngoại.
* Mỗi bản ghi mang `lot_id` (UUID của bãi) để cloud phân vùng theo bãi.
* `capture_id` đã unique, mở rộng nguyên tắc idempotent này cho mọi thực thể đồng bộ.

### 4.2 Đồng bộ edge lên cloud (outbox)

* Edge ghi mọi thay đổi cần đồng bộ vào một **outbox bền** (bảng cục bộ) song song với việc ghi nghiệp vụ, trong cùng transaction.
* Một tiến trình đồng bộ đẩy batch outbox lên `Sync API` khi có mạng; xóa mục outbox khi cloud xác nhận.
* Cloud upsert idempotent theo khóa UUID: gửi lại cùng bản ghi không tạo bản trùng. Chịu được mạng chập chờn và gửi lại.
* Ảnh bằng chứng đồng bộ như blob mã hóa, có thể trễ và theo lô để tiết kiệm băng thông; siêu dữ liệu phiên đi trước.

### 4.3 Đồng bộ cloud xuống edge (config pull)

* Edge định kỳ hoặc theo sự kiện kéo cấu hình mới: bảng giá, toggle, vé tháng, danh sách trắng đen, người dùng, danh mục tầng khu của bãi.
* Áp bản mới theo phiên bản (version hoặc updated_at), ghi đè bản sao cục bộ. Vì các nhóm này master ở cloud, không có xung đột ghi từ edge.
* Khi mất mạng, edge dùng bản sao cục bộ gần nhất; đăng nhập, kiểm vé tháng, kiểm danh sách đen vẫn chạy.

### 4.4 Bảo mật đường đồng bộ

* Xác thực edge với cloud bằng khóa thiết bị riêng mỗi site (không bake vào image, không commit), tương tự `X-Edge-Key` hiện có nhưng cấp theo bãi.
* Kênh TLS. Biển số và ảnh là dữ liệu cá nhân: mã hóa khi truyền, tuân thủ điều khoản lưu trữ và xóa (mục 8).

## 5. Suy luận ML ở edge

* **Vị trí:** hàm suy luận chạy trong tầng edge, tái dùng pipeline `alpr-pipeline`/`src/ml` của Nhật thay vì viết mới. Backend edge gọi hàm này (inline trong tiến trình backend cho MVP; có thể tách tiến trình worker cục bộ nếu cần giữ API mượt dưới tải).
* **Luồng:** Chromium `getUserMedia` lấy khung hình trên click Check in hoặc Check out, POST ảnh về endpoint suy luận của backend edge; backend chạy detect biển, OCR, phân loại màu và loại xe, trả về các trường (biển, `plate_valid`, màu, `vehicle_type`, `vehicle_group`, `review_state`) và tạo lượt đọc, phát realtime như hợp đồng `CaptureResponse` hiện có.
* **Giữ tương thích:** đường `POST /captures` nhận payload đã suy luận sẵn được giữ lại để một thiết bị cổng chuyên dụng (camera tự trigger, drive-through) vẫn có thể đẩy vào. Hai đường cùng tạo cùng loại lượt đọc. Kiosk dùng đường suy luận tại backend; cổng tự động dùng đường payload.
* **Ngân sách trễ:** ONNX INT8 trên Pi 5 CPU, mục tiêu tổng dưới 2 giây mỗi xe, khớp mục tiêu đồ án tuần 7 và 8.
* **Feature toggle:** tắt `read_plate` thì kiosk ép nhập tay, không gọi suy luận, giữ nguyên nguyên tắc luôn có đường lùi nhập tay.

## 6. Danh mục use case đầy đủ

Trạng thái: ĐANG CÓ trong backend, MỘT PHẦN, hoặc THIẾU. Ưu tiên: P1 lõi (hệ thống bãi thật hỏng nếu thiếu), P2 quan trọng, P3 mở rộng.

### 6.1 Vào ra và phiên

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Cho xe vào, ra kèm phí, nhập tay, sửa biển, tranh chấp và resolve | ĐANG CÓ | — |
| Xe ra không có phiên vào (mất vé), áp phí phạt định nghĩa sẵn | THIẾU | P1 |
| Quá hạn, xe bỏ quên nhiều ngày | THIẾU | P2 |
| Dọn phiên treo, đối soát phiên | THIẾU | P2 |

### 6.2 Sức chứa và lấp đầy (cả miền THIẾU)

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Đếm số xe trong bãi theo bãi, tầng, khu thời gian thực | THIẾU | P1 |
| Giới hạn sức chứa, chặn vào khi đầy, báo đầy bãi | THIẾU | P1 |
| Số chỗ trống, dữ liệu cho bảng đèn hiển thị | THIẾU | P2 |
| Theo dõi từng chỗ đỗ nếu quản lý mức chỗ | THIẾU | P3 |

### 6.3 Giá cước

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Giá phẳng hoặc theo block mỗi nhóm xe | ĐANG CÓ | — |
| Miễn phí X phút đầu (grace period) | THIẾU | P1 |
| Giá theo giờ trong ngày, cuối tuần, lễ; trần ngày; qua đêm; bậc lũy tiến | THIẾU | P2 |
| Xe miễn phí theo danh sách trắng (nhân viên, VIP, cư dân) | THIẾU | P2 |

### 6.4 Thanh toán (lõi, đang THIẾU)

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Phí đang được tính nhưng không ghi nhận đã thu | THIẾU | P1 |
| Bản ghi thanh toán: phương thức (tiền mặt, QR, ví), biên lai | THIẾU | P1 |
| Hoàn tiền, điều chỉnh | THIẾU | P2 |

### 6.5 Vé tháng và đăng ký xe

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Vé tháng (subscription) | THIẾU | P2 |
| Đăng ký chủ xe, liên kết biển và chủ, liên hệ | THIẾU | P2 |
| Danh sách đen: xe cấm, xe mất cắp, cảnh báo | THIẾU | P2 |

### 6.6 Ca trực và thu ngân

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Mở và đóng ca, tiền đầu ca cuối ca, bàn giao | THIẾU | P1 |
| Đối soát cuối ca: xe vào ra khớp, tiền thu so với hệ thống | THIẾU | P1 |
| Báo cáo doanh thu theo ca và theo nhân viên | THIẾU | P2 |

### 6.7 Thiết bị và phần cứng

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Cấu hình lane và rtsp | MỘT PHẦN | — |
| Tín hiệu điều khiển barie mở đóng khi xác nhận | THIẾU | P1 |
| Nhịp sống thiết bị, cảnh báo camera hoặc edge offline | THIẾU | P2 |
| Bảng đèn, máy in vé, đầu đọc QR, cảm biến vòng từ | THIẾU | P3 |
| Mở toàn bộ barie khẩn cấp (PCCC, sơ tán) | THIẾU | P1 |

### 6.8 Đa bãi (yêu cầu đã nêu)

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Mô hình bãi, tầng, khu; cấu hình theo bãi | THIẾU | P1 |
| Phân công nhân viên theo bãi | THIẾU | P2 |
| Giá theo bãi | THIẾU | P2 |
| Tra cứu và báo cáo liên bãi ở cloud | THIẾU | P2 |

### 6.9 Báo cáo

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Đang trong bãi, doanh thu, lưu lượng cơ bản, xuất CSV | ĐANG CÓ hoặc MỘT PHẦN | — |
| Báo cáo đối soát, giờ cao điểm, vòng quay, thời lượng trung bình, doanh thu theo bãi và nhân viên | THIẾU | P2 |

### 6.10 Quản trị và bảo mật

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Đăng nhập JWT, RBAC staff và admin, CRUD user, audit log, tự xóa lưu trữ | ĐANG CÓ | — |
| Vai trò chi tiết hơn: admin tổng đa bãi, quản lý bãi, thu ngân, người xem | THIẾU | P2 |
| Đặt lại mật khẩu | THIẾU | P3 |

### 6.11 Sự cố và cảnh báo

| Use case | Trạng thái | Ưu tiên |
|---|---|---|
| Nhật ký sự cố (va chạm, mất xe, hư hỏng) | THIẾU | P2 |
| Mở barie thủ công kèm lý do và audit | THIẾU | P1 |
| Cảnh báo (gần đầy, camera lỗi, phát hiện danh sách đen, doanh thu bất thường) | THIẾU | P2 |

## 7. Các miền dữ liệu mới cần thêm (edge backend)

Chi tiết mô hình và endpoint ở spec con backend. Tóm tắt miền:

* **Bãi và không gian:** `parking_lot`, `floor`, `zone`; khóa ngoại `lot_id`, `zone_id` gắn vào phiên và lượt đọc; sức chứa theo bãi/tầng/khu và đếm chiếm dụng thời gian thực.
* **Thanh toán:** `payment` (phiên, số tiền, phương thức, thời điểm, nhân viên, biên lai), điều chỉnh và hoàn.
* **Ca trực:** `shift` (nhân viên, mở, đóng, tiền đầu, tiền cuối), tổng hợp đối soát.
* **Đăng ký xe:** `monthly_pass`, `vehicle_owner`, `plate_whitelist`, `plate_blacklist`.
* **Thiết bị:** `device` hoặc mở rộng `lane` (barie, camera, bảng đèn), trạng thái nhịp sống; `barrier_event` (mở tự động, mở tay kèm lý do, mở khẩn cấp).
* **Sự cố:** `incident` (loại, mô tả, ảnh, nhân viên, thời điểm).
* **Định giá mở rộng:** bổ sung grace period, lịch giá theo thời gian, trần ngày trong `price_rule` hoặc bảng lịch giá riêng.
* **Đồng bộ:** `outbox` cục bộ ở edge; bảng phân vùng theo `lot_id` ở cloud.

## 8. Quyền riêng tư và pháp lý (Luật Bảo vệ dữ liệu cá nhân, hiệu lực 01/01/2026)

* Biển số và ảnh xe là dữ liệu cá nhân: mã hóa khi lưu và khi đồng bộ; kiểm soát truy cập theo vai và theo bãi; tự xóa sau thời hạn lưu trữ tính từ khi xe ra.
* Thời hạn lưu trữ áp ở cả hai tầng: edge xóa cục bộ theo hạn; cloud xóa bản tổng hợp theo cùng chính sách. Đồng bộ không được kéo dài vòng đời dữ liệu quá hạn.
* Mọi lần xem ảnh bằng chứng ghi audit ở tầng phát sinh. Không có xử lý khuôn mặt ở bất kỳ tầng nào.
* Khóa thiết bị và khóa mã hóa nằm ngoài repo, cấp theo bãi, không commit.

## 9. Bề mặt giao diện

Hai bề mặt tách biệt, chi tiết ở spec frontend v2:

* **Kiosk edge (tại chỗ):** trạm cổng cảm ứng cho nhân viên một bãi, khung webcam và nút Check in/Check out gọi suy luận tại backend, panel quyết định theo `review_state`, thu tiền và in biên lai, sức chứa bãi và tầng, mở barie, đối soát ca. Chạy offline.
* **Dashboard cloud (trung tâm):** cho admin tổng và chủ đầu tư, xem nhiều bãi, tra cứu liên bãi, báo cáo tổng, quản trị master (bãi/tầng/khu, bảng giá, người dùng, vé tháng, danh sách trắng đen).

## 10. Phân pha theo kế hoạch 10 tuần (edge trước, cloud sau)

Tài liệu chốt thiết kế đầy đủ hai tầng. Thứ tự hiện thực đặt edge trước để có demo một bãi chạy end-to-end, cloud thêm sau:

1. **Nền edge, đa bãi cục bộ và ID:** chuyển UUID và `lot_id`; mô hình bãi/tầng/khu; đếm sức chứa; chặn đầy bãi. Đặt nền cho mọi thứ.
2. **Suy luận ML tại edge:** endpoint nhận ảnh, tái dùng `alpr-pipeline`, trả trường và tạo lượt đọc; kiosk `getUserMedia`.
3. **Thanh toán và ca trực:** ghi nhận thu tiền, biên lai, mở đóng ca, đối soát cuối ca.
4. **Thiết bị và ngoại lệ:** tín hiệu barie, mở tay có audit, mở khẩn cấp, nhịp sống thiết bị, mất vé, quá hạn, sự cố.
5. **Đăng ký xe và giá mở rộng:** vé tháng, danh sách trắng đen, chủ xe, grace period, lịch giá.
6. **Cloud và đồng bộ:** central DB, sync API, outbox edge, config pull, dashboard đa bãi, tra cứu và báo cáo liên bãi.

Với ràng buộc đồ án (mục tiêu edge là một Pi), demo có thể chốt ở pha 5 với một bãi chạy trọn offline; pha 6 chứng minh khả năng mở rộng đa bãi và bổ sung nếu quỹ thời gian cho phép.

## 11. Ngoài phạm vi

Theo từng chỗ trống: đầu đọc QR và máy in vé vật lý (P3), theo dõi mức từng chỗ đỗ (P3), đặt lại mật khẩu thật (P3), i18n đa ngôn ngữ, thông báo đẩy trình duyệt, tùy biến theme ngoài sáng và tối. Giữ đường mở, không hiện thực trong MVP.

## 12. Giả định đã chốt (sửa được ở bước review spec)

* Topology: một Pi kiosk mỗi bãi ở edge, cloud trung tâm. Hai tầng.
* ML: inline trong backend edge, tái dùng `alpr-pipeline`/`src/ml`; trình duyệt `getUserMedia` rồi POST ảnh về backend.
* ID: khóa chính UUID thay tự tăng số nguyên, kèm `lot_id`.
* Phân pha: thiết kế đủ hai tầng; hiện thực edge trước, cloud và đồng bộ sau.
* Bốn nhóm use case gộp vào: đa bãi và sức chứa, thanh toán và ca, đăng ký (vé tháng, danh sách trắng đen), thiết bị (barie và nhịp sống).
