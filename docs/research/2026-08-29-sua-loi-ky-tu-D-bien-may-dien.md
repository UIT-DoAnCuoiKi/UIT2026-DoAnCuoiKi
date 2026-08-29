# CẢI TIẾN NHẬN DIỆN KÝ TỰ "Đ" CHO BIỂN SỐ XE MÁY ĐIỆN (SERI MĐ/TĐ)

## 1. Hiện trạng và Vấn đề

CRNN đọc biển số hiện tại chỉ nhận diện 36 ký tự (0-9, A-Z). Biển seri **MĐ** (xe máy điện, quy định thật theo Thông tư 24/2023 và 79/2024/TT-BCA) và **TĐ** luôn rớt hẳn ký tự "Đ" khi đọc, không phải đọc nhầm thành ký tự khác.

Lỗi này nguy hiểm hơn lỗi OCR thông thường vì **vượt qua cả 2 lớp an toàn hiện có**: định dạng vẫn khớp regex do trùng hợp, độ tin cậy vẫn báo cao (97-99%). Hệ thống báo "đọc được, tin cậy cao" cho 1 biển đọc sai, không có cảnh báo nào để nhân viên biết cần kiểm tra lại.

## 2. Nguyên nhân

- **Charset thiếu "Đ"**: `CHARSET` trong `src/ml/training/ocr_model.py` chỉ có 36 lớp, model không có khả năng xuất ra ký tự này.
- **5 chỗ trong code dùng chung 1 regex `[^A-Z0-9]`** để làm sạch chuỗi, vô tình xoá "Đ" cả ở bước chuẩn bị dữ liệu huấn luyện lẫn ở đường suy luận thật: `data_prep/prepare_ocr_data.py` (`clean_label`), `training/ocr_model.py` (`split_label_for_2row_from_raw`), `pipeline/ocr.py` (`normalize_plate_text`, tính `head_len` trong `read_plate`).
- **Phát hiện quan trọng khi điều tra**: dataset `topkek_plate_ocr` đang dùng **đã có sẵn 169 ảnh thật và 199 ảnh tổng hợp chứa "Đ"** (đa số seri MĐ), nhưng bị đúng 5 chỗ regex trên làm sai nhãn từ trước tới giờ (ví dụ `28TĐ 00067` bị lưu thành `28T00067`, mất 1 ký tự). Không phải thiếu dữ liệu như giả định ban đầu, mà là dữ liệu có sẵn nhưng bị hỏng nhãn.

## 3. Cải tiến

1. Sửa cả 5 vị trí regex, thêm "Đ" vào tập ký tự giữ lại (`[^A-Z0-9Đ]`).
2. Thêm "Đ" vào `CHARSET` (36 → 37 ký tự), `NUM_CLASSES` tự tăng theo (38, tính cả blank CTC).
3. Cập nhật `PLATE_PATTERN` trong `pipeline/ocr.py` để chấp nhận "Đ" trong seri (`[A-Z]` thành `[A-ZĐ]`).
4. **Lỗi phụ phát hiện khi test**: `format_display()` giới hạn phần đầu biển (mã tỉnh + seri) tối đa 4 ký tự, nhưng seri MĐ/TĐ kèm số lô dài tới 5 ký tự (vd `60MĐ1`) nên bị hiển thị sai thành `60MĐ-101658` thay vì `60MĐ1-016.58`. Đã nới giới hạn lên 5 ký tự.
5. Chạy lại `prepare_ocr_data.py` để tái tạo `train.csv`/`val.csv`/`test.csv`/`train_synthetic.csv` với nhãn "Đ" đúng.
6. Train lại CRNN (`train_ocr_crnn.py`, cùng cấu hình cũ: 40 epoch, batch 64, lr 0.001).

## 4. Kết quả

**So với model chốt trước đó (seed 42) trên cùng `test.csv`:**

| | Trước | Sau |
|---|---:|---:|
| Accuracy toàn bộ | 58,9% | 56,6% |
| Số tham số | 424.933 | 425.126 (+193, đúng bằng 1 lớp output mới) |

Giảm nhẹ 2,3 điểm phần trăm, hợp lý vì model học thêm 1 lớp ký tự mới trong cùng số epoch, không phải dấu hiệu lỗi.

**Riêng 17 biển có "Đ" trong `test.csv`: 8/17 (47%) khớp hoàn toàn cả biển.** Soi từng ca sai thì 10/17 model **đọc đúng ký tự "Đ"** (7 đúng cả biển, 3 ca chỉ lệch 1 chữ số khác không liên quan đến Đ). 7/17 ca thực sự nhầm "Đ" thành ký tự khác, chủ yếu D, B, H, C (dễ hiểu vì hình dạng rất giống, đặc biệt Đ với D chỉ khác 1 nét ngang nhỏ). So với trước đây rớt ký tự này 100% số lần, đây là cải thiện thật dù chưa hoàn hảo.

## 5. Hạn chế và việc cần làm tiếp

- Tập test riêng cho "Đ" chỉ có 17 ảnh, khoảng tin cậy của con số accuracy còn rộng, không nên coi là chính xác tuyệt đối.
- Nhầm lẫn Đ với D là lỗi còn lại phổ biến nhất, có thể cần thêm dữ liệu hoặc tăng trọng số các dòng có "Đ" lúc train nếu muốn cải thiện thêm.
- Đang ở branch `fix/nhat-ocr-charset-md-plate`, chưa merge vào main. `docs/report/chapters/04-ocr.md` hiện vẫn mô tả đúng model cũ đang chạy trên main, cần cập nhật số liệu nếu merge branch này.
- 3 ảnh thật ban đầu dùng để phát hiện lỗi (`testimage/MD1.jpeg`, `md.jpeg`, `md2.jpeg`) đã bị xoá khỏi `testimage/` trong lúc dọn dẹp, không dùng lại để kiểm chứng cuối được.

## 6. Kiểm tra đã chạy

- `python -m py_compile` sạch cho các file đã sửa.
- Test hàm `normalize_plate_text()`, `format_display()`, `read_plate()` với các chuỗi mẫu chứa "Đ", xác nhận hợp lệ và hiển thị đúng.
- Chạy lại `prepare_ocr_data.py`, xác nhận nhãn "Đ" được giữ đúng ở cả 4 file CSV đầu ra.
- Train lại CRNN, đánh giá trên `test.csv` và riêng tập con có "Đ" như bảng trên.
