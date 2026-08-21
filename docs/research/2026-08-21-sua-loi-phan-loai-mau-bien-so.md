# CẢI TIẾN PHÂN LOẠI MÀU NỀN BIỂN SỐ
Loại bỏ nhiễu viền từ ảnh crop trước khi đếm màu nền

---

## 1. Hiện trạng và Vấn đề
Trong luồng xử lý hiện tại, hàm `classify_color()` (thuộc `plate_color_pipeline`) tiếp nhận trực tiếp ảnh crop biển số từ module `PlateDetector`.
Tuy nhiên, trong quá trình cắt ảnh, `PlateDetector` đang áp dụng một giá trị mở rộng biên cố định (`pad = 4` pixel) xung quanh bounding box phát hiện bởi YOLO:

```python
# plate_detection_pipeline/plate_detect/inference/plate_detector.py, build_detections()
def build_detections(boxes, classes, confs, image, names, pad: int = 4) -> list[PlateDetection]:
    ...
    x1 = int(max(0, min(W, x1 - pad))); y1 = int(max(0, min(H, y1 - pad)))
    x2 = int(max(0, min(W, x2 + pad))); y2 = int(max(0, min(H, y2 + pad)))
```

## 2. Phân tích rủi ro (Nhiễu tín hiệu viền)
Việc sử dụng tham số `pad=4` cố định mà không xét đến nội dung thực tế của ảnh đang gây ra rủi ro sai lệch nhận diện. Cụ thể:
- Ảnh crop biển số thường có kích thước rất nhỏ (chỉ từ 30-100px). Vì vậy, vài pixel biên thừa này chiếm tỷ trọng không hề nhỏ trong tổng thể ảnh.
- Phần biên thừa thường lẫn các vùng nhiễu: màu sơn của xe, viền đen/chữ đỏ của biển số, hoặc quang sai màu ở rìa ảnh.

**Thực nghiệm kiểm chứng:**
Ghi nhận một trường hợp thực tế: biển số màu **Trắng** bị mô hình phân loại nhầm thành màu **Xanh (Blue)** với độ tự tin (confidence) là `0.55`. 
Khi thực hiện kiểm tra bằng cách cắt bớt viền (tăng dần margin), kết quả cho thấy:
- Số lượng điểm ảnh màu xanh (blue) giảm mạnh: từ **1669** xuống chỉ còn **388**.
- Số lượng điểm ảnh màu trắng (white) gần như giữ nguyên: duy trì ở mức **1354**.

**Kết luận:** Tín hiệu màu sai lệch (nhiễu) chủ yếu tập trung ở dải viền xung quanh crop, hoàn toàn không nằm trong phần nền chính của biển số.

## 3. Giải pháp đề xuất
Thay vì phụ thuộc vào viền `pad` cố định, bổ sung một bước tiền xử lý để **tự động xác định và cô lập đúng vùng nền biển số** trước khi đếm màu. Giải pháp tận dụng kỹ thuật **Otsu threshold** kết hợp **Contour detection**:

1. **Otsu Thresholding:** Tự động tính toán ngưỡng độ sáng tối ưu để phân tách ảnh xám thành 2 vùng (sáng/tối) thay vì sử dụng ngưỡng hardcode thủ công.
2. **Contour Detection:** Tìm đường viền của các vùng liền khối trên ảnh phân ngưỡng đó. Vùng sáng có diện tích lớn nhất có khả năng cao nhất chính là nền thực tế của biển số.
3. **Cắt ảnh động (Dynamic Cropping):** Trích xuất bounding box của contour lớn nhất này để làm vùng đếm màu thực tế, qua đó loại bỏ được phần viền thừa.

*Ghi chú:* Kỹ thuật này tái sử dụng lại tư duy thuật toán đang áp dụng trong hàm `deskew()` (`pipeline/ocr.py` - tìm góc nghiêng biển). Điểm khác biệt là tại đây chúng ta lấy bounding box của contour thay vì lấy góc xoay.

**Cơ chế an toàn (Fallback):**
Trường hợp diện tích của contour lớn nhất tìm được nhỏ hơn **30%** diện tích crop ban đầu, hệ thống sẽ đánh giá độ tin cậy thấp. Thuật toán sẽ bỏ qua bước cắt viền và giữ nguyên ảnh crop gốc (không ép cắt).

## 4. Chi tiết triển khai mã nguồn

Các thay đổi cụ thể trên source code:

- **`src/ml/plate_color_pipeline/plate_color/color/classifier.py`**:
  Bổ sung bước xử lý Otsu + Contour trước khi tính toán dải màu HSV.
- **`src/ml/plate_color_pipeline/plate_color/color/thresholds.py`**:
  Thêm hằng số cấu hình ngưỡng diện tích an toàn: `COLOR_MIN_CONTOUR_AREA_FRAC = 0.3`.
- **Giới hạn phạm vi ảnh hưởng:**
  Chỉ áp dụng thuật toán này cho luồng phân loại màu (Color Classification).
- **Sửa lỗi phụ (Bug Fix):**
  Cập nhật lại biến `total` (dùng để tính toán tỷ lệ `considered_frac`). Trước đây biến này bị lỗi không được cập nhật lại theo diện tích mới sau khi crop bị thu nhỏ.
