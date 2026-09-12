## Tiêu đề đề xuất

Tuần 7 (26/08 đến 04/09): Hoàn thiện luồng dashboard end to end kèm kiến trúc hệ thống, chuẩn bị môi trường kiểm thử trên Raspberry Pi 5

## Phân công và kết quả

**Đức: hoàn thiện luồng quản lý bãi xe end to end trên dashboard, kèm thiết kế kiến trúc hệ thống**

- Dựng đầy đủ backend FastAPI và giao diện React cho một luồng nghiệp vụ hoàn chỉnh: nhận diện tại cổng, tạo phiên gửi xe, đối soát khi ra, tính phí, thu tiền, in biên lai, tra cứu phiên và thống kê.
- Chốt kiến trúc hai đường thu nhận ảnh: đường kiosk trên máy tính (backend chạy model) và đường cổng tự động (thiết bị biên chạy model, backend không suy luận lại).
- Tách lớp cấu hình phân quyền theo vai, danh mục nhóm xe làm nguồn duy nhất cho bảng giá, cấu hình bật tắt từng thành phần AI.
- Toàn bộ đã gộp vào `main` qua pull request số 19.

**Nhật: chuẩn bị môi trường kiểm thử trên Raspberry Pi 5, kiểm tra kết nối, chạy thử mô hình trên môi trường giả lập Pi5, rà soát mã của Đức, hoàn thiện luồng phát hiện biển số**

- Viết worker cho thiết bị biên chạy pipeline ALPR thật tại chỗ, tách phần cứng sau interface để chạy được khi chưa có camera hay GPIO.
- Đóng gói pipeline suy luận sang ONNX, chạy không cần torch, phù hợp thiết bị biên.
- Dựng môi trường giả lập Pi5 trên máy host, kiểm tra kết nối từ worker về backend, chạy thử end to end.
- Rà soát mã tích hợp backend và dashboard của Đức, hoàn thiện luồng phát hiện biển số kèm bản trọng số ONNX theo dõi được qua git.

## Đã hoàn thành

### 1. Backend FastAPI cho toàn bộ nghiệp vụ bãi xe (Đức)

Mã nguồn: [src/backend/app](../../src/backend/app)

- Mô hình dữ liệu đầy đủ cho nghiệp vụ: phiên gửi xe, lượt đọc biển, thanh toán, quy tắc giá, nhóm xe, sự cố, thiết bị, ca trực, vé tháng, danh sách biển, tài sản ảnh, nhật ký kiểm toán.
- Bộ router theo từng chức năng: xác thực, phiên, thu nhận ảnh, cổng qua websocket, thanh toán, thống kê, cấu hình, nhóm xe, đồng bộ.
- Phân quyền theo vai gắn với JWT. Vai không hợp lệ bị xoá token và đưa về trang đăng nhập thay vì rơi vào màn cổng.
- Danh mục nhóm xe là nguồn duy nhất cho bảng giá: chặn tạo giá với nhóm không có trong danh mục, chặn xoá nhóm khi còn được tham chiếu.

### 2. Luồng cổng end to end trên dashboard (Đức)

Mã nguồn: [src/frontend/src/features/gate](../../src/frontend/src/features/gate)

- Chọn camera, xem trước, chụp khung hình từ webcam qua hook thu nhận camera.
- Gửi khung hình tới backend để suy luận, đẩy kết quả về đúng hướng vào hoặc ra qua websocket.
- Bảng quyết định tại cổng hiển thị biển số, nhóm xe, giá, cho phép xác nhận cho qua.
- Mở hộp thoại thu tiền khi xe ra có phí, bỏ qua khi miễn phí, in được biên lai.
- Bố cục trạm cổng kèm phím tắt theo ngữ cảnh và bảng tra cứu phím tắt.

### 3. Quản lý phiên và thống kê (Đức)

Mã nguồn: [src/frontend/src/features/sessions](../../src/frontend/src/features/sessions), [src/frontend/src/features/stats](../../src/frontend/src/features/stats)

- Bộ lọc danh sách phiên theo nhóm xe, khoảng thời gian vào, cờ đối soát. Xử lý đúng trường hợp lọc trong cùng một ngày.
- Trang chi tiết phiên trả về nhân viên xử lý, bãi và khu, các lần thanh toán, ảnh chụp mức phí tại thời điểm chốt.
- Bổ sung cột loại xe, người chốt phiên, phương thức thanh toán vào danh sách phiên.
- Trang thống kê kèm xuất CSV cho vai quản lý và vai gốc.

### 4. Worker cho thiết bị biên và pipeline ONNX (Nhật)

Mã nguồn: [src/edge/worker.py](../../src/edge/worker.py), [src/ml/pipeline/onnx_pipeline.py](../../src/ml/pipeline/onnx_pipeline.py)

- Worker chạy pipeline ALPR thật tại chỗ trên thiết bị cổng: chờ tín hiệu kích hoạt, đọc một khung từ camera, chạy detector YOLO cùng OCR CRNN và phân loại kiểu dáng, gửi kết quả đã suy luận về backend.
- Phần cứng gồm tín hiệu kích hoạt và camera được tách sau interface, nhờ đó kiểm thử được mà không cần camera, GPIO hay model thật. Đã có bộ test cho worker.
- Pipeline đóng gói ONNX chạy không phụ thuộc torch, kèm test khói xác nhận chạy được, đúng hướng tối ưu cho thiết bị biên.

### 5. Môi trường giả lập Pi5 và kiểm tra kết nối (Nhật)

- Dựng môi trường giả lập Pi5 trên máy host thay vì trong container, do container trên macOS gặp lỗi đọc thư mục bind mount.
- Kiểm tra đường đi từ worker về backend qua khoá xác thực thiết bị biên, xác nhận backend nhận payload đã suy luận kèm ảnh JPEG mà không suy luận lại.
- Chạy thử toàn tuyến trên môi trường giả lập, đối chiếu kết quả với đường kiosk.

### 6. Rà soát mã và hoàn thiện luồng phát hiện biển số (Nhật)

- Rà soát phần tích hợp backend và dashboard của Đức, tập trung vào điểm nối giữa dashboard và pipeline thị giác máy tính.
- Hoàn thiện luồng phát hiện biển số, xuất bản trọng số ONNX đặt trong thư mục trọng số theo dõi được qua git, tránh phụ thuộc file lớn bị chặn bởi git.

## Kiến trúc hệ thống end to end

Thiết kế xoay quanh hai đường thu nhận ảnh song song, cùng đổ về một backend.

**Đường kiosk trên máy tính.** Giao diện cổng chụp khung hình từ webcam rồi gửi tới backend. Backend chạy pipeline suy luận, trả về biển số, kiểu dáng, màu biển. Dùng cho trạm có người trực.

**Đường cổng tự động trên thiết bị biên.** Worker trên Raspberry Pi 5 chạy pipeline ngay tại chỗ khi có tín hiệu kích hoạt, rồi gửi kết quả đã suy luận kèm ảnh về backend qua khoá xác thực thiết bị biên. Backend không suy luận lại, chỉ ghi nhận. Mục tiêu độ trễ dưới hai giây mỗi xe.

**Xử lý nghiệp vụ tại backend.** Từ một lượt đọc biển, backend tạo phiên gửi xe khi vào, đối soát biển khi ra, tính phí theo quy tắc giá gắn với nhóm xe, chuyển sang thu tiền và in biên lai, cuối cùng đưa dữ liệu lên phần tra cứu phiên và thống kê. Kênh websocket đẩy ảnh thu nhận theo hướng vào ra tới giao diện cổng.

**Nền tảng chung.** Phân quyền theo vai gắn JWT, cấu hình bật tắt từng thành phần AI, nhật ký kiểm toán. Dữ liệu biển số và ảnh xe là dữ liệu cá nhân, cần kiểm soát truy cập và tự xoá sau thời hạn lưu trữ theo Luật Bảo vệ dữ liệu cá nhân có hiệu lực từ ngày 01/01/2026.

## Kế hoạch tuần sau

- Viết báo cáo và chuẩn bị slide trình bày.
- Rà soát và hoàn thiện toàn bộ luồng ứng dụng quản lý bãi xe, đưa hệ thống chạy trên Raspberry Pi 5 thật thay vì môi trường giả lập.

## Kết quả đạt được

- Có một luồng quản lý bãi xe chạy được đầu cuối trên dashboard, từ nhận diện tại cổng tới thu phí, tra cứu và thống kê, kèm bản thiết kế kiến trúc rõ hai đường thu nhận ảnh.
- Pipeline suy luận đã đóng gói ONNX chạy không cần torch, có worker thiết bị biên kiểm thử được mà không cần phần cứng.
- Đã chạy thử toàn tuyến trên môi trường giả lập Pi5 và kiểm tra kết nối, sẵn sàng cho bước triển khai trên Raspberry Pi 5 thật.
- Mã của hai thành viên đã gộp vào nhánh chính qua hai pull request, có rà soát chéo giữa phần dashboard và phần pipeline.
