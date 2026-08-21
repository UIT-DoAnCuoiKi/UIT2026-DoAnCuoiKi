# HỆ THỐNG QUẢN LÝ BÃI ĐỖ XE


## 1. Quy trình nghiệp vụ

**Xe vào:** camera chụp, AI nhận diện, nhân viên xác nhận, hệ thống tạo session `in_lot`.

**Xe ra, khớp biển:** camera chụp, đối chiếu session, tính phí, nhân viên xác nhận thu tiền, session chuyển `completed`.

**Xe ra, OCR đọc sai vài ký tự:** độ chính xác OCR đo được 58,9% đến 87,5% tùy điều kiện ảnh, nên sai vài ký tự là bình thường, không phải lỗi hệ thống. Ô sửa tay luôn có sẵn trên màn hình, hệ thống nối lại đúng session sau khi sửa.

**Xe ra, nghi vấn:** biển khác hẳn, không phải lỗi đọc nhầm ký tự đơn lẻ. Session chuyển `disputed`, không tự tính phí. Nhân viên đối chiếu ảnh vào/ra, xử lý tay hoặc báo quản lý.

**AI lỗi:** nút nhập tay hoàn toàn luôn có trên màn hình, tạo và đóng session không cần qua AI. Đây là đường lùi bắt buộc để hệ thống không thành điểm nghẽn.

---

## 2. Giao diện

MVP có 5 màn hình, mỗi màn hình gồm các chức năng sau:

**1. Trạm kiểm soát (Cổng)**
- Xem luồng camera trực tiếp
- Xem kết quả nhận diện: biển số, loại xe, màu biển
- Sửa tay biển số
- Xác nhận xe vào, xác nhận xe ra
- Nhập tay hoàn toàn khi AI lỗi
- Cảnh báo tranh chấp

**2. Quản lý & Tra cứu**
- Danh sách session đang đỗ và lịch sử
- Lọc theo biển số, theo trạng thái
- Xem ảnh vào/ra của từng session
- Xử lý session tranh chấp

**3. Báo cáo Thống kê**
- Số xe đang trong bãi
- Lưu lượng theo giờ, theo ngày
- Doanh thu theo khoảng thời gian

**4. Xác thực & Phân quyền**
- Đăng nhập
- Phân quyền staff và admin

**5. Cấu hình**
- Sửa bảng giá theo loại phương tiện
- Tạo, khóa, đổi mật khẩu tài khoản nhân viên
- Cấu hình URL luồng camera (RTSP) cho lane đang có
- Cầu hình enable/disable từng AI features: đọc biển số, phân loại màu biển, phần loại xe. Mục đích để người dùng có thể chủ động cấu hình tùy theo nhu cầu sử dụng.

---

## 3. Bảo mật & Quyền riêng tư

- Mã hóa biển số và ảnh khi lưu trữ.
- Truy cập ảnh bằng chứng yêu cầu đăng nhập.
- Tự động xóa session và ảnh sau hạn lưu trữ đã cam kết trong đề cương.
- Ảnh có thể vô tình lọt khuôn mặt, chỉ dùng để nhân viên đối chiếu bằng mắt khi có tranh chấp, không dùng mô hình nhận diện khuôn mặt tự động. Vẫn áp cùng chính sách mã hóa và xóa tự động như trên.

---

## 4. Định hướng phát triển

- **Vé tháng và cư dân:** 
- **Đối soát theo ca hoặc nhân viên:** 
- **Đa lane, đa camera:** 
- **Điều khiển barrier vật lý:** 