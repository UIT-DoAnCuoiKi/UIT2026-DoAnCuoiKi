# Parking edge + cloud redesign: chỉ mục kế hoạch triển khai (6 phase)

> **For agentic workers:** mỗi phase là một plan riêng trong cùng thư mục. Thực thi tuần tự theo thứ tự phụ thuộc. Dùng superpowers:subagent-driven-development (khuyến nghị) hoặc superpowers:executing-plans cho từng phase. Các bước dùng checkbox (`- [ ]`).

**Nguồn spec:** `docs/superpowers/specs/2026-08-23-parking-system-edge-cloud-architecture-design.md` và `docs/superpowers/specs/2026-08-23-frontend-snowui-design.md` (v2).

**Goal:** nâng backend single-node hiện có thành hệ thống hai tầng edge cộng cloud: mỗi bãi là một site edge chạy trọn trên Pi 5, hoạt động offline (nhận dạng biển tại chỗ, vào ra, thu tiền, sức chứa, barie, ca trực); cloud tổng hợp và quản trị nhiều bãi khi có kết nối.

**Architecture:** edge backend FastAPI cộng Postgres cục bộ cộng suy luận ML tại chỗ cộng kiosk Chromium; cloud trung tâm nhận outbox từ edge và phát cấu hình xuống. Dữ liệu vận hành chảy lên, cấu hình chảy xuống, không bảng nào ghi hai chiều.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, SQLAlchemy 2.0 (sync), Alembic, psycopg2, pydantic v2, pydantic-settings, cryptography (Fernet), bcrypt, PyJWT, pytest, httpx; ONNX Runtime cộng pipeline `alpr-pipeline`/`src/ml` cho suy luận edge; Podman.

**Phạm vi loại trừ:** code React frontend (người phụ trách tự dựng, tiêu thụ hợp đồng REST cộng WebSocket của các phase). Các plan chỉ tới endpoint và hợp đồng dữ liệu.

## Global Constraints (áp cho mọi phase, chép nguyên từ spec)

- Luật Bảo vệ dữ liệu cá nhân hiệu lực 2026-01-01: biển số và ảnh xe là dữ liệu cá nhân.
- Mã hóa tầng cột cho biển và ảnh; khóa nạp từ biến môi trường, không nằm trong repo, không hardcode. Khóa thiết bị đồng bộ cấp theo bãi.
- Hạn lưu trữ: mặc định 30 ngày sau `exit_time`, áp ở cả edge và cloud; đồng bộ không kéo dài vòng đời dữ liệu quá hạn.
- Cấm mọi xử lý khuôn mặt tự động ở mọi tầng.
- Edge tự chủ: mọi vận hành hàng ngày của một bãi phải chạy được khi mất Internet. Cloud không nằm trên đường quyết định vào ra thời gian thực.
- Một bãi bằng một site edge; tầng và khu là phân chia bên trong một bãi. Khả năng nhiều bãi nằm ở cloud.
- Dữ liệu vận hành (phiên, đọc biển, thanh toán, ca, sự cố) master ở edge, đẩy lên cloud. Cấu hình và danh mục (bảng giá, toggle, vé tháng, danh sách trắng đen, người dùng, bãi/tầng/khu) master ở cloud, phát xuống edge.
- `capture_id`: UNIQUE, khóa idempotent cho ingest capture. Mở rộng nguyên tắc idempotent cho mọi thực thể đồng bộ.
- `review_state` do backend tính, nhận một trong `confident`, `needs_review`, `disputed`, `manual`.
- Nhóm xe: `xe_may` (motorbike, bicycle), `o_to_con` (car), `xe_tai` (truck), `xe_khach` (bus).
- Phí (giữ nguyên hợp đồng hiện có, mở rộng ở phase 5): `mode = flat` một giá trọn lượt, hoặc `mode = block` bằng `ceil(thời_gian / block_minutes) * unit_price`; đọc giá lúc xe ra; lưu `fee_rule_snapshot`.
- Suy luận ML mục tiêu dưới 2 giây mỗi xe trên Pi 5 (ONNX INT8). Tắt `read_plate` thì kiosk ép nhập tay, luôn có đường lùi nhập tay.
- Kiosk phục vụ trên `http://localhost` của Pi; `getUserMedia` chạy vì localhost là secure context.
- Vai: `staff` và `admin` hiện có; phase sau thêm admin tổng, quản lý bãi, thu ngân, người xem.
- Quy tắc commit (dự án): chỉ commit khi người dùng yêu cầu rõ trong lượt đó; các bước commit trong plan là điểm mốc, gom thay đổi rồi để người dùng commit.
- Quy tắc viết: không dùng ký tự gạch ngang trong văn xuôi tài liệu.
- Nghiệm thu: mỗi phase kết thúc bằng một test acceptance kiểm chứng deliverable của cả phase; task cuối chạy test này cộng toàn bộ suite và phải PASS trước khi qua phase sau.

## Quyết định sắp xếp: định danh UUID toàn cục dời sang phase 6

Spec kiến trúc (mục 4.1) đặt việc chuyển khóa chính sang UUID là nền tảng. Về kỹ thuật, thay kiểu khóa chính trên cả 8 bảng đang có cộng mọi khóa ngoại cộng mọi test là thay đổi rủi ro cao, trong khi UUID chỉ thực sự cần khi đồng bộ lên cloud (phase 6). Các phase 1 tới 5 là một site edge một bãi, không cần UUID toàn cục.

Quyết định: giữ khóa chính số nguyên cục bộ ở edge cho phase 1 tới 5 (cộng thêm cột `lot_id` phân vùng ngay từ đầu ở các bảng vận hành mới). Việc gắn định danh toàn cục (`uuid` cộng `lot_id`) làm khóa nghiệp vụ cho đồng bộ nằm ở phase 6, như một migration riêng, giữ cho suite 84 test hiện tại xanh trong suốt các phase edge. Nếu muốn theo đúng spec (UUID ngay phase 1), báo lại để đổi thứ tự; chi phí là refactor toàn repo và cập nhật toàn bộ test ngay từ đầu.

## Danh sách phase

| Phase | Plan file | Nội dung | Phụ thuộc | Deliverable test được |
|---|---|---|---|---|
| 1 | `2026-08-23-phase-1-edge-multilot-capacity.md` | Mô hình bãi, tầng, khu; gắn `lot_id` và `zone_id` vào phiên; đếm chiếm dụng thời gian thực; chặn vào khi đầy bãi; CRUD bãi/tầng/khu (admin); endpoint sức chứa | không (dựa backend hiện có) | migration tạo bảng bãi/tầng/khu; vào xe cập nhật chiếm dụng; đầy bãi trả 409; báo cáo sức chứa đúng |
| 2 | `2026-08-23-phase-2-edge-ml-inference.md` | Endpoint nhận ảnh thô, tái dùng pipeline `alpr-pipeline`/`src/ml`, trả `CaptureResponse` và tạo lượt đọc, phát realtime; giữ đường `POST /captures` payload cho cổng tự động; toggle `read_plate` | 1 (cộng `src/ml` của Nhật) | POST ảnh trả biển/màu/loại và tạo reading; tắt toggle thì ép nhập tay |
| 3 | `2026-08-23-phase-3-payment-shift.md` | Bản ghi thanh toán (phương thức, biên lai), điều chỉnh và hoàn; ca trực mở đóng; đối soát cuối ca; báo cáo theo ca và nhân viên | 1 | xe ra ghi thanh toán; đóng ca trả bảng đối soát khớp |
| 4 | `2026-08-23-phase-4-devices-exceptions.md` | Tín hiệu barie mở đóng, mở tay kèm lý do và audit, mở khẩn cấp; nhịp sống thiết bị và cảnh báo offline; xe ra không có phiên vào (mất vé) áp phí phạt; quá hạn; nhật ký sự cố | 1, 3 | xác nhận phát sự kiện barie; mở tay ghi audit; mất vé tạo phiên phạt; sự cố lưu |
| 5 | `2026-08-23-phase-5-registry-pricing.md` | Vé tháng, chủ xe, danh sách trắng, danh sách đen; miễn phí theo danh sách; grace period; lịch giá theo thời gian và trần ngày | 1, 3 | xe có vé tháng hoặc danh sách trắng miễn phí; grace period và lịch giá tính đúng; danh sách đen cảnh báo |
| 6 | `2026-08-23-phase-6-cloud-sync.md` | Định danh toàn cục UUID cộng `lot_id`; outbox bền ở edge; Sync API cloud (upsert idempotent); config pull; central DB đa bãi; endpoint tra cứu và báo cáo liên bãi cho dashboard cloud | 1 tới 5 | outbox đẩy và cloud upsert không nhân đôi; config phát xuống edge; tra cứu liên bãi trả đúng |

## Thứ tự thực thi

1 trước, đặt nền đa bãi và sức chứa mà các phase sau gắn vào (mọi phiên có `lot_id` và `zone_id`). 2 thêm suy luận tại edge, dựa 1 cho ngữ cảnh bãi. 3 và 4 và 5 độc lập tương đối, đều dựa 1; 4 và 5 dựa thêm 3 cho phí và thanh toán. 6 cuối cùng, khi mọi dữ liệu vận hành edge đã ổn định thì thêm định danh toàn cục và đồng bộ lên cloud. Demo một bãi chạy trọn offline chốt được sau phase 5; phase 6 chứng minh mở rộng đa bãi.

Frontend do người phụ trách dựng song song theo spec v2: app kiosk edge tiêu thụ hợp đồng phase 1 tới 5; app dashboard cloud tiêu thụ hợp đồng phase 6.
