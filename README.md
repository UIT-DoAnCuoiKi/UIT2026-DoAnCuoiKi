# Hệ thống quản lý bãi giữ xe thông minh ứng dụng thị giác máy tính và Edge AI

**Smart Parking Management System using Computer Vision and Edge AI**

Đồ án tốt nghiệp — Trường Đại học Công nghệ Thông tin, ĐHQG-HCM (UIT).

## Thông tin đề tài

| | |
|---|---|
| **Cán bộ hướng dẫn** | ThS. Phan Đình Duy |
| **Sinh viên thực hiện** | 25410104 – Nguyễn Minh Nhật · 25410034 – Lê Quang Hoài Đức |
| **Thời gian thực hiện** | 15/07/2026 – 23/09/2026 |

## Mục tiêu

Xây dựng một hệ thống quản lý bãi giữ xe thông minh có khả năng tự động nhận diện phương tiện (biển số, loại xe, màu nền biển số) bằng thị giác máy tính. Hệ thống được thiết kế độc lập nền tảng (khả chuyển), triển khai được trên máy chủ, PC hoặc thiết bị biên — ưu tiên minh họa khả năng chạy trên **Edge AI** (ví dụ Raspberry Pi) để giảm phụ thuộc máy chủ và tăng tính ứng dụng thực tế. Hệ thống hỗ trợ quản lý xe vào/ra, đối chiếu chống gian lận, tính phí tự động và cung cấp dashboard thống kê.

### Mục tiêu cụ thể

- **Nhận diện biển số xe**: phát hiện vùng biển + OCR đọc ký tự, hỗ trợ biển 1 hàng (ô tô) và 2 hàng (xe máy) theo chuẩn Việt Nam.
- **Phân loại phương tiện**: ô tô, xe máy, xe tải, xe buýt; nhận diện màu nền biển số (trắng, vàng, xanh, đỏ) để phân nhóm xe cá nhân/kinh doanh/cơ quan nhà nước.
- **Quản lý vào/ra**: ghi nhận thời gian, đối chiếu biển số vào–ra chống gian lận, lưu ảnh toàn cảnh làm bằng chứng, tính phí gửi xe tự động.
- **Dashboard quản lý & thống kê**: theo dõi xe ra/vào thời gian thực, tra cứu phương tiện trong bãi, thống kê theo loại xe/màu biển/lưu lượng/doanh thu.
- **Triển khai khả chuyển**: tối ưu mô hình (ONNX, quantization) để chạy trên thiết bị biên, minh họa cụ thể trên Raspberry Pi.

## Phạm vi

- **Phương tiện**: tập trung vào xe máy và ô tô (phổ biến nhất tại bãi giữ xe Việt Nam); mô hình phân loại vẫn huấn luyện đủ 4 lớp nhưng chỉ đánh giá chuyên sâu trên 2 lớp chính.
- **Chức năng**: nhận diện biển số, loại xe, màu biển, quản lý vào/ra, tính phí, dashboard thống kê — chưa xử lý xe di chuyển tốc độ cao (free-flow).
- **Nền tảng**: thiết kế độc lập nền tảng (PC/máy chủ hoặc thiết bị biên); phần triển khai minh họa trên một thiết bị biên cụ thể.
- **Dữ liệu**: kết hợp bộ dữ liệu biển số/phương tiện Việt Nam công khai với ảnh tự thu thập trong điều kiện thực tế.
- **Bảo vệ dữ liệu cá nhân**: biển số và hình ảnh phương tiện được xử lý theo Luật Bảo vệ dữ liệu cá nhân (hiệu lực 01/01/2026) — kiểm soát truy cập, mã hóa dữ liệu nhạy cảm, tự động xóa sau thời hạn quy định kể từ khi xe rời bãi.

## Đối tượng nghiên cứu

- Mô hình phát hiện đối tượng: **YOLOv8, YOLO26**
- Mô hình phân loại ảnh: **ResNet, MobileNet**
- OCR: **PaddleOCR / EasyOCR**
- Xử lý ảnh: **OpenCV**, không gian màu **HSV**
- Nền tảng triển khai: máy chủ/PC đến thiết bị biên (**Raspberry Pi, Jetson**…) và camera
- Tối ưu & đóng gói mô hình đa nền tảng: **ONNX, TensorRT, quantization**

## Phương pháp thực hiện

1. **Nghiên cứu tài liệu**: kiến trúc YOLO, kỹ thuật OCR, xử lý màu HSV, tối ưu mô hình cho thiết bị biên, quy định biển số xe Việt Nam.
2. **Thực nghiệm**: thu thập & gắn nhãn dữ liệu, huấn luyện mô hình trên GPU, tích hợp các mô-đun thành một luồng xử lý, tối ưu và nạp mô hình xuống thiết bị biên.
3. **Kiểm thử & đánh giá theo thành phần**:
   - Phát hiện xe/biển số: mAP@0.5, mAP@0.5:0.95, precision, recall
   - OCR: độ chính xác mức nguyên biển & mức ký tự (CER)
   - Phân loại loại xe: accuracy, F1, ma trận nhầm lẫn
   - Màu biển: accuracy
   - Thử nghiệm ở nhiều điều kiện ánh sáng khác nhau
4. **Đánh giá khả năng triển khai trên thiết bị biên**: inference time (mô hình riêng và end-to-end), FPS, kích thước mô hình, mức dùng bộ nhớ, độ chính xác trước/sau quantization, (tùy điều kiện) điện năng tiêu thụ (W, FPS/W); so sánh hiệu năng PC vs. thiết bị biên.

## Kết quả mong đợi

- **Sản phẩm phần mềm**: hệ thống nhận diện & quản lý bãi giữ xe hoạt động end-to-end với dashboard trực quan; độ chính xác đọc biển số > 90% trong điều kiện tiêu chuẩn.
- **Triển khai**: chạy được trên PC và thiết bị biên (minh họa trên Raspberry Pi), xử lý từng lượt xe với độ trễ mục tiêu **< 2 giây/lượt** trên Raspberry Pi 5, kèm số liệu so sánh hiệu năng đa nền tảng.
- **Tài liệu**: báo cáo đồ án tốt nghiệp hoàn chỉnh (viết song hành theo từng giai đoạn), mã nguồn, bộ dữ liệu tự thu thập, video demo.

## Tài liệu

Đề cương chi tiết đầy đủ: [`docs/DCDATN_25410104_NguyenMinhNhat_25410034_LeQuangHoaiDuc.docx`](docs/DCDATN_25410104_NguyenMinhNhat_25410034_LeQuangHoaiDuc.docx)
