# Brainstorm prompt: tích hợp AI pipeline vào Dashboard MVP

Tài liệu này là bộ câu hỏi định hướng (brainstorm prompt) để lên kế hoạch kỹ thuật cho
`docs/design/dashboard-mvp-spec.md`, nối phần AI pipeline đã phát triển với backend và dashboard.

## Cách dùng

Trả lời tuần tự từng bước (Bước 1 tới Bước 12). Câu sau dựa trên quyết định của câu trước,
nên đừng nhảy bước. Mỗi bước có:

- **Mục tiêu:** chốt cái gì.
- **Câu hỏi cần trả lời:** đánh số, trả lời trực tiếp.
- **Mặc định đề xuất:** phương án hợp lý nhất nếu bạn muốn đi nhanh; sửa nếu không đồng ý.
- **Ảnh hưởng tới:** phần nào của hệ thống phụ thuộc câu trả lời này.

Có thể tự điền, hoặc dán nguyên **Phần 0 (Bối cảnh)** cộng với từng bước cho một AI để nó
đặt câu hỏi tiếp và soạn spec. Khi đã trả lời hết, tập hợp lại thành design spec kỹ thuật.

---

## Phần 0. Bối cảnh (dán kèm khi hỏi AI)

**Dự án:** hệ thống quản lý bãi đỗ xe thông minh dùng computer vision và edge AI, đồ án tốt
nghiệp UIT. Mục tiêu edge: Raspberry Pi 5, độ trễ đầu cuối mục tiêu dưới 2 giây mỗi xe.

**Phân công:** Đức làm plate color, database, logic in/out, phí, dashboard, edge deploy.
Nhật làm detection, OCR, phân loại xe, tối ưu model.

**AI pipeline đã có (hợp đồng dữ liệu đầu ra).** Mỗi ảnh, hàm pipeline trả về một dict:

- `vehicle_type`: class YOLO của xe (car, motorbike, truck, bus, bicycle...), hoặc null.
- `vehicle_box`: bbox xe.
- `vehicle_style`, `vehicle_style_conf`: chỉ có khi `vehicle_type == "car"` (sedan, SUV...),
  kèm độ tin cậy. Không có với xe máy.
- `plates`: danh sách biển phát hiện được, mỗi phần tử gồm:
  - `bbox`: vị trí biển.
  - `layout`: `1 hàng` hoặc `2 hàng`.
  - `det_conf`: độ tin cậy phát hiện biển.
  - `plate_text`: chuỗi biển OCR đọc được (đã format hiển thị).
  - `plate_valid`: true nếu khớp định dạng biển Việt Nam.
  - `ocr_conf`: độ tin cậy OCR.
  - `color`, `color_conf`: màu nền biển (trắng, vàng, xanh...) kèm độ tin cậy.

**Chất lượng đo được:** plate detector mAP50 khoảng 0,9892. OCR đúng khoảng 58,9% tới 87,5%
tùy điều kiện ảnh, nên sai vài ký tự là bình thường. Màu biển có module riêng.

**Trạng thái code:** `src/ml` đã có pipeline chạy được (`src/ml/e2e_pipeline_test.py`).
`src/backend`, `src/frontend`, `src/edge` chưa có gì. Dashboard mới có spec sản phẩm mức cao
(`docs/design/dashboard-mvp-spec.md`): 5 màn hình, quy trình nghiệp vụ, bảo mật, hướng mở rộng.

**Ràng buộc pháp lý:** Luật Bảo vệ dữ liệu cá nhân hiệu lực 01/01/2026. Biển số và ảnh xe là
dữ liệu cá nhân: mã hóa khi lưu, kiểm soát truy cập, tự xóa sau hạn lưu trữ cam kết trong đề cương.

**Nguyên tắc thiết kế bắt buộc từ spec:** luôn có đường lùi nhập tay hoàn toàn khi AI lỗi;
ô sửa tay biển số luôn hiện; session nghi vấn chuyển `disputed`, không tự tính phí.

---

## Bước 1. Phạm vi MVP và nơi chạy AI

**Mục tiêu:** chốt biên giới hệ thống và kiến trúc tổng thể trước mọi thứ khác.

**Câu hỏi:**

1. MVP chạy 1 lane (1 cổng vào ra chung) hay tách cổng vào và cổng ra riêng? Bao nhiêu camera?
2. AI chạy ở đâu: (a) worker trên edge (Pi) chạy pipeline rồi POST kết quả JSON cộng ảnh về
   backend, backend không giữ model; hay (b) backend giữ model và tự chạy inference; hay
   (c) chạy ngay trong tiến trình dashboard?
3. Với MVP demo đồ án, mục tiêu chính là chạy đúng nghiệp vụ trên PC trước, rồi mới lên Pi,
   đúng không? Điều này quyết định có cần tách edge worker ngay từ đầu hay không.

**Mặc định đề xuất:** 1 lane, camera vào và camera ra riêng (nếu thiếu thiết bị thì 1 camera
dùng chung, phân biệt hướng bằng nút bấm của nhân viên). Phương án (a): edge worker chạy
pipeline, POST JSON cộng ảnh về backend qua HTTP. Backend chỉ nhận kết quả, không giữ model.
Lý do: khớp mục tiêu edge deploy của đồ án, backend gọn, dễ test PC trước bằng cách cho một
script đóng vai edge worker.

**Ảnh hưởng tới:** toàn bộ API (Bước 6), tích hợp edge (Bước 11), độ trễ.

---

## Bước 2. Hợp đồng dữ liệu: pipeline sang ứng dụng

**Mục tiêu:** biến dict pipeline thành khái niệm nghiệp vụ mà backend lưu và xử lý.

**Câu hỏi:**

1. Một ảnh có thể ra 0, 1 hoặc nhiều biển trong `plates`. Chọn biển đại diện cho xe thế nào?
   Theo `det_conf` cao nhất? Theo diện tích bbox lớn nhất? Nếu 0 biển thì xử lý ra sao?
2. Ngưỡng tin cậy nào coi là "chắc chắn" so với "cần nhân viên soát"? Ví dụ đặt ngưỡng
   `ocr_conf` và `det_conf`. Dưới ngưỡng thì highlight ô sửa tay nhưng vẫn cho xác nhận.
3. `plate_valid == false` (không khớp định dạng biển Việt Nam) thì chặn xác nhận hay chỉ cảnh báo?
4. Lưu lại những trường nào của pipeline vào DB làm bằng chứng và phục vụ báo cáo? Cụ thể có
   lưu `det_conf`, `ocr_conf`, `color_conf`, `layout` không, hay chỉ lưu kết quả cuối?
5. `vehicle_type` (car, motorbike, truck...) map sang nhóm tính phí thế nào? `vehicle_style`
   (sedan, SUV) có ý nghĩa tính phí không, hay chỉ để hiển thị và thống kê?

**Mặc định đề xuất:** chọn biển có `det_conf` cao nhất làm biển đại diện; 0 biển thì tạo bản
ghi ở trạng thái chờ nhập tay. Ngưỡng soát: `ocr_conf` dưới 0,7 hoặc `plate_valid == false`
thì highlight ô sửa, không tự chặn. Lưu đủ `det_conf`, `ocr_conf`, `color`, `color_conf`,
`layout` vào bản ghi lần đọc để phục vụ báo cáo đánh giá và đối chiếu tranh chấp. Phí tính
theo `vehicle_type` gộp thành nhóm (xe máy, ô tô con, xe lớn); `vehicle_style` chỉ hiển thị.

**Ảnh hưởng tới:** schema (Bước 3), logic khớp (Bước 4), tính phí (Bước 5), màn hình cổng (Bước 7).

---

## Bước 3. Mô hình dữ liệu (database schema)

**Mục tiêu:** chốt bảng, trạng thái, mã hóa, hạn lưu trữ.

**Câu hỏi:**

1. Các thực thể tối thiểu: `session` (một lượt gửi xe), `plate_reading` (mỗi lần AI đọc, vào
   và ra), `image_asset` (ảnh bằng chứng), `price_rule` (bảng giá), `user`, `audit_log`.
   Có thiếu thực thể nào cho MVP không?
2. Trạng thái session: `in_lot`, `completed`, `disputed` như spec. Có cần thêm trạng thái
   `pending_manual` (đang chờ nhập tay) hay gộp vào `in_lot` là đủ?
3. Biển số lưu mã hóa nhưng lúc xe ra phải tra để khớp. Dùng cách nào: lưu bản mã hóa để hiển
   thị cộng thêm một cột hash chuẩn hóa (ví dụ HMAC của biển đã bỏ ký tự phân tách, viết hoa)
   để tra khớp mà không cần giải mã hàng loạt?
4. Ảnh bằng chứng lưu ở đâu: cột bytea trong Postgres, hay file trên đĩa cộng đường dẫn trong
   DB? Ảnh có mã hóa khi lưu không, hay chỉ kiểm soát truy cập?
5. Hạn lưu trữ tự xóa: đề cương cam kết bao nhiêu ngày sau khi xe ra? Cần con số cụ thể để đặt job xóa.

**Mặc định đề xuất:** đủ 6 thực thể ở câu 1, thêm trạng thái `pending_manual`. Biển lưu hai
dạng: giá trị mã hóa để hiển thị, cộng cột `plate_hash` (HMAC của biển đã chuẩn hóa) để tra
khớp. Ảnh lưu thành file mã hóa trên đĩa, DB giữ đường dẫn cộng khóa tham chiếu. Hạn lưu trữ:
điền theo đề cương (ví dụ 30 ngày sau khi xe ra), job xóa chạy định kỳ.

**Ảnh hưởng tới:** logic khớp (Bước 4), bảo mật (Bước 10), tra cứu (Bước 7).

---

## Bước 4. Logic in/out và khớp phiên (state machine)

**Mục tiêu:** chốt cách nối xe ra với đúng session đang đỗ, chịu được OCR sai vài ký tự.

**Câu hỏi:**

1. Xe vào: tạo session `in_lot` ngay sau khi nhân viên xác nhận, đúng chứ? Có cho hai xe cùng
   biển (đọc trùng) cùng ở `in_lot` không, hay chặn?
2. Xe ra khớp biển thế nào: chuẩn hóa rồi so khớp chính xác trước; nếu trượt thì tìm trong tập
   session `in_lot` theo edit distance nhỏ hơn hoặc bằng k. Đặt k bằng mấy (1 hay 2)?
3. Dùng thêm tín hiệu phụ để phân định khi có nhiều ứng viên: `vehicle_type` và `color` phải
   trùng thì mới coi là cùng xe? Điều này giúp lọc bớt nhầm.
4. Nếu đúng một ứng viên trong ngưỡng: tự nối và đánh dấu "đã sửa tự động" cho nhân viên biết,
   hay luôn bắt nhân viên bấm xác nhận?
5. Nếu không có ứng viên nào hoặc có nhiều ứng viên như nhau: chuyển `disputed`, không tự tính
   phí, đúng theo spec chứ? Nhân viên đối chiếu ảnh vào và ra bằng mắt.
6. Nút nhập tay hoàn toàn (AI lỗi) tạo và đóng session không qua khớp AI: luồng dữ liệu ra sao?

**Mặc định đề xuất:** vào tạo `in_lot` ngay; cảnh báo nếu trùng biển đang trong bãi nhưng không
chặn (biển đọc nhầm là thật). Ra: exact match trước, trượt thì edit distance k bằng 2, thu hẹp
bằng cùng `vehicle_type`; `color` chỉ dùng tham khảo vì có thể sai. Đúng một ứng viên thì tự
nối cộng cờ "đã sửa tự động"; không có hoặc nhiều ứng viên thì `disputed`. Nhập tay hoàn toàn
đi qua cùng endpoint xác nhận nhưng bỏ qua bước khớp AI.

**Ảnh hưởng tới:** tính phí (Bước 5), màn hình cổng và tra cứu (Bước 7), API (Bước 6).

---

## Bước 5. Tính phí

**Mục tiêu:** chốt bảng giá và cách tính, kể cả ca bất thường.

**Câu hỏi:**

1. Phí theo nhóm `vehicle_type` (xe máy, ô tô con, xe lớn) nhân với thời gian gửi. Đơn vị thời
   gian tính phí: theo giờ, theo block (ví dụ mỗi 60 phút), hay giá trọn gói theo lượt?
2. Làm tròn thời gian thế nào: lên block gần nhất? Có thời gian miễn phí đầu (grace period) không?
3. Màu biển (trắng cá nhân, vàng kinh doanh, xanh cơ quan...) có ảnh hưởng giá không, hay MVP bỏ qua?
4. Session `disputed` xử lý tay: nhân viên nhập phí thủ công, hay có giá mặc định khi mất vé /
   không khớp?
5. Bảng giá do admin sửa được trong màn Cấu hình. Khi đổi giá, session đang `in_lot` áp giá lúc
   vào hay lúc ra? Cần chốt để tránh tranh cãi.

**Mặc định đề xuất:** phí theo nhóm `vehicle_type` nhân số block 60 phút, làm tròn lên, không
grace period cho MVP. Màu biển không ảnh hưởng giá (ghi vào hướng mở rộng). `disputed` cho
nhập phí tay. Áp giá theo thời điểm xe ra (bảng giá hiện hành), ghi rõ trong hóa đơn.

**Ảnh hưởng tới:** schema `price_rule` (Bước 3), báo cáo doanh thu (Bước 7), cấu hình (Bước 8).

---

## Bước 6. Thiết kế API (FastAPI)

**Mục tiêu:** chốt endpoint và cách backend nhận kết quả AI.

**Câu hỏi:**

1. Endpoint tối thiểu: nhận capture từ edge (ảnh cộng dict pipeline), xác nhận vào, xác nhận ra,
   sửa biển tay, nhập tay hoàn toàn, danh sách session, chi tiết session cộng ảnh, xử lý dispute,
   thống kê, CRUD cấu hình, đăng nhập. Thiếu gì cho MVP không?
2. Kết quả AI đẩy về theo mô hình nào: edge POST một lần mỗi lần chụp (đồng bộ), hay backend mở
   kênh nhận liên tục? Nhân viên cần thấy kết quả gần như tức thời trên màn cổng.
3. Màn cổng cập nhật kết quả nhận diện: dùng WebSocket đẩy, hay polling ngắn cho đơn giản?
4. Ảnh gửi kèm JSON trong một request (multipart), hay upload ảnh riêng rồi tham chiếu id?
5. Có versioning hoặc khóa idempotent cho capture để tránh nhân đôi khi mạng chập chờn không?

**Mặc định đề xuất:** REST cho toàn bộ nghiệp vụ; edge POST multipart (ảnh cộng JSON) mỗi lần
chụp; màn cổng dùng WebSocket nhận sự kiện nhận diện mới, fallback polling nếu WebSocket rườm rà.
Mỗi capture kèm một `capture_id` idempotent để chống nhân đôi. Đây là quyết định lớn, cân nhắc kỹ.

**Ảnh hưởng tới:** mọi màn hình (Bước 7), tích hợp edge (Bước 11).

---

## Bước 7. Ghép dữ liệu vào 5 màn hình

**Mục tiêu:** với mỗi màn trong spec, chốt lấy dữ liệu từ endpoint nào và có những trạng thái nào.

**Câu hỏi (làm cho từng màn):**

1. **Trạm kiểm soát (cổng):** hiển thị luồng camera, kết quả nhận diện (biển, loại xe, màu),
   ô sửa biển, nút xác nhận vào và ra, nút nhập tay, cảnh báo tranh chấp. Bốn trạng thái cần vẽ
   riêng: chắc chắn, cần soát (tin cậy thấp hoặc sai định dạng), tranh chấp, AI lỗi (nhập tay).
   Bạn muốn bố cục ra sao cho nhân viên thao tác nhanh nhất?
2. **Quản lý và tra cứu:** danh sách `in_lot` và lịch sử, lọc theo biển và trạng thái, xem ảnh
   vào ra, xử lý `disputed`. Tra theo biển dùng cột hash đã chuẩn hóa. Cần phân trang chứ?
3. **Báo cáo thống kê:** số xe trong bãi, lưu lượng theo giờ và ngày, doanh thu theo khoảng. Các
   con số này tính realtime từ DB hay tổng hợp định kỳ? MVP realtime truy vấn thẳng có đủ nhanh không?
4. **Xác thực và phân quyền:** chỉ đăng nhập cộng phân vai staff và admin, chưa cần gì thêm chứ?
5. **Cấu hình:** bảng giá, tài khoản nhân viên, URL RTSP theo lane, bật tắt từng AI feature.

**Mặc định đề xuất:** cổng ưu tiên một khung lớn cho biển cộng nút xác nhận to, ô sửa ngay dưới,
cảnh báo tranh chấp nổi bật. Tra cứu có phân trang, lọc phía server. Thống kê MVP truy vấn thẳng
DB, tối ưu sau nếu chậm. Auth chỉ staff và admin.

**Ảnh hưởng tới:** API (Bước 6), phân quyền (Bước 9).

---

## Bước 8. Cấu hình và feature toggle

**Mục tiêu:** chốt cách bật tắt từng AI feature và cấu hình lane.

**Câu hỏi:**

1. Ba toggle theo spec: đọc biển số, phân loại màu biển, phân loại xe. Toggle tác động ở đâu:
   edge worker bỏ chạy bước đó, hay backend chỉ ẩn hiển thị? Tắt ở edge thì tiết kiệm tài nguyên Pi.
2. Tắt OCR thì màn cổng chuyển sang bắt buộc nhập tay biển, đúng logic chứ?
3. URL RTSP theo lane lưu ở đâu và ai đọc: backend đẩy xuống edge worker, hay cấu hình thẳng trên edge?
4. Đổi cấu hình có cần khởi động lại edge worker không, hay áp nóng?

**Mặc định đề xuất:** toggle lưu ở backend, edge worker đọc cấu hình khi khởi động và định kỳ
làm mới; tắt feature nào thì edge bỏ chạy bước đó để tiết kiệm Pi. Tắt OCR thì cổng ép nhập tay.
RTSP lưu ở backend, đẩy xuống edge. Cấu hình áp ở lần capture kế tiếp, không cần restart.

**Ảnh hưởng tới:** edge (Bước 11), màn cổng (Bước 7).

---

## Bước 9. Xác thực và phân quyền

**Mục tiêu:** chốt ma trận quyền staff so với admin.

**Câu hỏi:**

1. Staff làm được gì: xác nhận vào ra, sửa biển, nhập tay, xem session, xử lý dispute cơ bản?
2. Chỉ admin làm được gì: sửa bảng giá, tạo khóa đổi mật khẩu tài khoản, cấu hình RTSP và toggle,
   xem toàn bộ báo cáo doanh thu?
3. Truy cập ảnh bằng chứng: cả staff và admin, hay giới hạn? Luật yêu cầu kiểm soát truy cập.
4. Có ghi audit log ai xem hoặc sửa dữ liệu nhạy cảm (biển, ảnh) không? Nên có để chứng minh tuân thủ.

**Mặc định đề xuất:** staff làm nghiệp vụ cổng và tra cứu, xem ảnh khi xử lý dispute. Admin thêm
quyền cấu hình, giá, tài khoản, báo cáo doanh thu đầy đủ. Ghi audit log mọi lần truy cập ảnh và
sửa biển. Đây là bằng chứng tuân thủ luật, nên giữ trong MVP.

**Ảnh hưởng tới:** bảo mật (Bước 10), API (Bước 6).

---

## Bước 10. Bảo mật và quyền riêng tư (Luật hiệu lực 01/01/2026)

**Mục tiêu:** chốt cụ thể cách đáp ứng ràng buộc pháp lý, không nói chung chung.

**Câu hỏi:**

1. Mã hóa biển và ảnh khi lưu: mã hóa ở tầng cột (application encrypt trước khi ghi) hay tin vào
   mã hóa đĩa? Tầng cột chứng minh tuân thủ rõ hơn.
2. Quản lý khóa mã hóa để đâu: biến môi trường, file khóa ngoài repo, hay dịch vụ quản lý khóa?
   MVP tối thiểu nhưng phải không hardcode trong code.
3. Job tự xóa: chạy theo lịch nào (mỗi ngày?), xóa cả bản ghi session và file ảnh sau hạn, ghi
   audit lại việc xóa chứ?
4. Ảnh có thể lọt khuôn mặt: spec nói chỉ để nhân viên đối chiếu bằng mắt, không chạy nhận diện
   khuôn mặt tự động. Cần ghi rõ ràng buộc này thành quy tắc code (không import model face) không?
5. Có cần trang chính sách hoặc mục ghi hạn lưu trữ cho người dùng biết không (minh bạch)?

**Mặc định đề xuất:** mã hóa tầng cột cho biển và ảnh trước khi ghi; khóa nạp từ biến môi trường,
không nằm trong repo; job xóa chạy hàng ngày, xóa bản ghi cộng file cộng ghi audit; cấm tuyệt đối
mọi xử lý khuôn mặt tự động, ghi thành quy tắc trong tài liệu và review code. Đây là phần bắt buộc,
đọc kỹ trước khi chốt.

**Ảnh hưởng tới:** schema (Bước 3), phân quyền (Bước 9), toàn bộ xử lý ảnh.

---

## Bước 11. Tích hợp edge (Raspberry Pi 5)

**Mục tiêu:** chốt cách edge worker nối với backend và chịu được mạng chập chờn.

**Câu hỏi:**

1. Edge worker chụp, chạy pipeline, POST về backend. Nếu backend mất kết nối lúc xe tới cổng thì
   sao: xếp hàng chờ gửi lại, hay cho nhân viên thao tác offline rồi đồng bộ sau?
2. Ngân sách độ trễ dưới 2 giây mỗi xe chia cho các bước (detect, OCR, color, gửi mạng) thế nào?
   Cần đo để biết bước nào là nút cổ chai.
3. Ảnh gửi lên full resolution hay nén trước để tiết kiệm băng thông và dung lượng lưu?
4. Model trên Pi dùng ONNX cộng lượng tử hóa (theo phân công tối ưu) hay bản .pt gốc cho MVP?
   Lưu ý pipeline hiện dùng plate detector bản .pt, chưa export .onnx.
5. Trên PC lúc phát triển, dùng một script giả lập edge worker (đọc ảnh thư mục, POST về backend)
   để test toàn luồng trước khi có Pi, đúng hướng chứ?

**Mặc định đề xuất:** edge worker có hàng đợi cục bộ, mất mạng thì lưu tạm và gửi lại; đồng thời
màn cổng vẫn cho nhập tay hoàn toàn để không nghẽn. Ảnh nén vừa phải trước khi gửi. MVP trên PC
chạy trước bằng script giả lập edge; lên Pi mới bàn ONNX và lượng tử hóa. Đo latency từng bước.

**Ảnh hưởng tới:** API (Bước 6), độ trễ mục tiêu, cấu hình (Bước 8).

---

## Bước 12. Ngoài phạm vi MVP và hướng mở rộng

**Mục tiêu:** xác nhận cái gì chưa làm để không phình MVP.

**Câu hỏi:**

1. Xác nhận các mục sau nằm ngoài MVP (đúng như mục Định hướng phát triển của spec): vé tháng và
   cư dân, đối soát theo ca hoặc nhân viên, đa lane đa camera, điều khiển barrier vật lý.
2. Có mục nào ở trên bạn muốn kéo vào MVP không? Nếu có, quay lại bổ sung ở bước liên quan.
3. Có nhu cầu nào chưa nằm trong spec mà bạn thấy cần cho buổi bảo vệ đồ án không (ví dụ xuất báo
   cáo, biểu đồ trực quan)?

**Mặc định đề xuất:** giữ nguyên bốn mục trên là ngoài phạm vi. MVP tập trung một lane, luồng vào
ra, khớp biển, phí, năm màn hình, bảo mật cơ bản.

---

## Bảng tổng hợp quyết định cần chốt

Điền cột "Chốt" sau khi trả lời xong. Đây là đầu vào để viết design spec kỹ thuật.

| # | Quyết định | Chốt |
|---|---|---|
| 1 | Số lane, số camera, nơi chạy AI (edge worker so với backend) | |
| 2 | Cách chọn biển đại diện; ngưỡng tin cậy cần soát | |
| 3 | Cách lưu và tra biển mã hóa (hash chuẩn hóa); nơi lưu ảnh | |
| 4 | Ngưỡng edit distance k khi khớp biển; tín hiệu phụ dùng để phân định | |
| 5 | Đơn vị tính phí; yếu tố quyết định giá; áp giá lúc vào hay lúc ra | |
| 6 | REST cộng WebSocket hay polling; cách edge đẩy kết quả | |
| 7 | Bố cục màn cổng; thống kê realtime hay tổng hợp | |
| 8 | Toggle tác động ở edge hay backend; cách áp cấu hình | |
| 9 | Ma trận quyền staff so với admin; audit log | |
| 10 | Cách mã hóa; quản lý khóa; lịch job xóa; hạn lưu trữ (số ngày) | |
| 11 | Hành vi khi mất mạng ở cổng; chia ngân sách latency; ONNX hay pt | |
| 12 | Xác nhận phạm vi ngoài MVP | |
