## Tiêu đề đề xuất
Tuần 1 (15/07 – 22/07): Khởi động & nghiên cứu tổng quan

## Đã chốt
- **Nhận diện & đọc biển số**: hỗ trợ cả biển dọc và biển vuông; output là chuỗi text đọc được từ biển số (OCR). Chú ý xử lý biển số có ký tự đặc biệt (nếu có).
- **Phân loại phương tiện**: xe máy, sedan, suv, bán tải, xe tải (có thể mở rộng nhãn nếu dữ liệu cho phép).
- **Phân loại màu biển**: bắt buộc trắng, vàng; tùy chọn (optional) xanh, đỏ.
- Đã tạo GitHub repo.

## Việc cần làm

- [x] Research các hệ thống ALPR / nhận diện phương tiện tương tự (để reference & so sánh kết quả) — @Nhật → [docs/research/khao-sat-he-thong-alpr.md](../research/khao-sat-he-thong-alpr.md)
- [ ] Research các hệ thống quản lý bãi xe / dashboard tương tự (để reference & so sánh kết quả) — @Đức
- [ ] Research YOLO — tìm hiểu và so sánh YOLOv8 vs YOLO26 —  @Đức
- [x] Research quy định biển số xe Việt Nam (bố cục, kích thước, ký tự) và quy chiếu màu biển —@Nhật → [docs/research/quy-dinh-bien-so-xe-vn.md](../research/quy-dinh-bien-so-xe-vn.md)
- [ ] Setup môi trường dev — @Đức @Nhật

> Phân công dựa theo vai trò tổng thể trong đề cương (Nhật: phát hiện/OCR/phân loại xe; Đức: màu biển/CSDL/dashboard/triển khai biên). Lưu ý: bản đề cương gốc ghi hoán đổi tạm thời riêng cho mục khảo sát hệ thống tương tự của tuần 1 (Đức tìm hiểu huấn luyện mô hình, Nhật tìm hiểu hệ thống & triển khai biên) — nếu muốn giữ đúng hoán đổi đó, đổi lại 2 dòng research hệ thống tương tự ở trên.

## Kết quả cần đạt
- Danh sách các hệ thống ALPR và hệ thống quản lý bãi xe tương tự đã khảo sát, kèm nhận xét để làm mốc so sánh kết quả sau này.
- Bảng so sánh YOLOv8 vs YOLO26 (kiến trúc, tốc độ, độ chính xác, khả năng chạy trên thiết bị biên) và quyết định chọn phiên bản dùng cho đề tài.
- Tóm tắt quy định bố cục/kích thước/ký tự biển số xe Việt Nam và bảng quy chiếu màu biển đã áp dụng.
- Môi trường dev (GPU/training và dashboard/edge) cài đặt xong, chạy thử được.
- Bản nháp chương tổng quan của báo cáo, tổng hợp từ các mục nghiên cứu trên.
