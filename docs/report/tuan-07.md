## Tiêu đề đề xuất
Tuần 7 (26/08 - 02/09): Sửa ký tự "Đ" cho biển xe máy điện, tối ưu và đóng gói mô hình ONNX

## Bối cảnh

Rà lại toàn bộ pipeline trước khi vào việc mới, phát hiện Đức đang có branch `feat/duc-dashboard-backend` (FastAPI, gọi trực tiếp `run_pipeline_on_image()` từ `src/ml/e2e_pipeline_test.py`). Script này giờ là điểm tích hợp thật với backend, không còn là script test riêng của Nhật nữa.

## Đã hoàn thành

### 1. Sửa ký tự "Đ" cho biển seri MĐ/TĐ (xe máy điện)

Chi tiết đầy đủ: [docs/research/2026-08-29-sua-loi-ky-tu-D-bien-may-dien.md](../research/2026-08-29-sua-loi-ky-tu-D-bien-may-dien.md)

- Nguyên nhân: 5 chỗ trong code dùng chung 1 regex `[^A-Z0-9]` xoá mất ký tự "Đ", cả ở bước chuẩn bị dữ liệu lẫn đường suy luận. Dataset `topkek_plate_ocr` **đã có sẵn 169 ảnh thật và 199 ảnh tổng hợp chứa "Đ"** nhưng bị đúng bug này làm sai nhãn từ trước tới giờ.
- Sửa cả 5 vị trí, thêm "Đ" vào `CHARSET` (36 → 37 ký tự), nới giới hạn `format_display()` lên 5 ký tự phần đầu (phát hiện thêm lúc test: seri MĐ kèm số lô dài 5 ký tự bị hiển thị sai).
- Train lại CRNN: accuracy toàn bộ `test.csv` giảm nhẹ 58,9% → 56,6%; tập độc lập `vn_plate` giảm 87,5% → 80,2%. Riêng 17 biển có "Đ" trong test.csv: 8/17 khớp hoàn toàn, nhưng 10/17 model đọc đúng ký tự "Đ" (trước đây rớt 100%).
- **Chưa xác định được mức giảm này là do thêm "Đ" hay chỉ là nhiễu giữa các lần train** (chương 4 mục 4.3 đã ghi nhận nhiễu này có thể trên 10 điểm phần trăm). Cần train thêm seed khác để kiểm chứng, chưa làm.

### 2. Phát hiện và sửa bug: file `.pt` và `.onnx` là hai model khác nhau

Lúc thêm backend ONNX cho `CRNNRecognizer` (việc 3), kiểm chứng 2 backend có khớp nhau không thì phát hiện **lệch ở 55/120 biển test**, quá lớn để là sai số làm tròn.

Nguyên nhân: `train_crnn()` trong `src/ml/training/ocr_model.py` lưu file `.pt` từ **checkpoint tốt nhất** (val CER thấp nhất) nhưng trả về biến `model` ở **epoch cuối** (thường tệ hơn) để các script export `.onnx` từ đó. Nghĩa là **mọi bản `.onnx` OCR từ trước tới giờ không phải model đã đo accuracy và báo cáo**, mà là 1 model khác, kém hơn. Lỗi này ảnh hưởng cả 3 script train OCR (`train_ocr_crnn.py`, `train_ocr_filtered.py`, `train_ocr_ablation.py`); bộ phân loại xe không bị.

Sửa tại gốc: `train_crnn()` nạp lại checkpoint tốt nhất vào `model` trước khi trả về. Xuất lại `.onnx`, kiểm chứng trên toàn bộ 666 biển `test.csv`: **666/666 khớp tuyệt đối giữa `.pt` và `.onnx`**, chênh lệch confidence 4x10^-7 (nhiễu số thực bình thường).

### 3. Thêm backend ONNX cho OCR và cho model phát hiện biển số

Động lực: file `.pt` bị `.gitignore` chặn (dung lượng lớn), không đi theo git. Nếu Đức pull code mới mà không có file `.pt` mới tương ứng, backend sẽ crash ngay (`size mismatch`, đã tái hiện được lỗi này khi test). File `.onnx` thì có track qua git.

- `CRNNRecognizer` (`pipeline/ocr.py`) thêm backend `onnx`, tự nhận theo đuôi file. Charset và hàm giải mã CTC dời về module này (không phụ thuộc torch) làm nguồn duy nhất, `ocr_model.py` import lại thay vì tự khai báo, tránh đúng loại lỗi lệch charset đã sửa ở việc 1.
- Xuất `src/ml/plate_detection_pipeline/weights/yolov8n_a1_640.onnx` (đặt đúng thư mục `weights/` mà package đã có quy ước track qua git, khác `output/runs/` đang bị `.gitignore` chặn hoàn toàn). Kiểm chứng khớp bản `.pt` trên 16/17 ảnh `testimage/`; 1 ca lệch là biển rất nhỏ/xa ở rìa ngưỡng tin cậy (0,65 → 0,09 khi đổi sang onnx), không phải lỗi export.
- `e2e_pipeline_test.py` và notebook chuyển cả 2 model sang chạy ONNX. Toàn bộ pipeline giờ suy luận được **không cần torch**, đúng hướng việc Tuần 7 trong đề cương ("tối ưu và đóng gói mô hình theo hướng khả chuyển").

### 4. Đính chính số liệu tuần 5

Khi đối chiếu lại báo cáo tuần 5, phát hiện cách đọc sai: bảng ghi "15/16 biển hợp lệ" bị hiểu nhầm là "15/16 đọc đúng", nhưng cờ hợp lệ chỉ kiểm tra **định dạng** chuỗi, không kiểm tra đọc có đúng hay không (đúng điều chương 4 mục 221 đã cảnh báo trước: *"Không dùng `valid_format` như thước đo chất lượng"*).

Đối chiếu bằng mắt với ảnh gốc: model của tuần 5 (36 ký tự) đọc sai ít nhất `t5.png` (`99F3-2294`, biển thật `89F3-2294`) dù báo tin cậy 99%. Không sửa báo cáo tuần 5 (giữ nguyên làm mốc lịch sử), ghi lại đính chính ở đây.

### 5. Điều tra nguyên nhân lỗi ký tự trên tập test hiện tại

Đo trên toàn bộ `test.csv` (4.167 ký tự so sánh được, model đã sửa "Đ"):

| Loại lỗi | Số lỗi | Tỉ lệ trong tổng lỗi |
|---|---:|---:|
| Tổng lỗi ký tự | 293 / 4.167 (7,0%) | |
| số → số | 187 | 64% |
| chữ → chữ | 50 | 17% |
| lẫn số với chữ | 56 | 19% |

Giả thuyết ban đầu ("M/H dễ lẫn vì H nhiều gấp 2,3 lần M trong dữ liệu") **bị số liệu bác bỏ**: M→H không xuất hiện lần nào trong toàn tập test. Nguyên nhân thật là nhầm lẫn giữa các chữ số (64% tổng lỗi: 1→7, 6→8, 8→9, 5→6...), khớp với phát hiện đã có ở chương 4 về ảnh hưởng của độ phân giải thấp, không phải phát hiện mới.

Cũng xác nhận lại kết luận cũ của chương 4 (mục lọc dữ liệu dưới 25px/dòng): **không nên lọc ảnh khó khỏi tập train** (đã thử, làm mất 36% dữ liệu, model overfit, kém hơn ở mọi dải độ phân giải) và **không nên lọc khỏi tập test** (làm sai lệch số liệu báo cáo). Hướng cải thiện đúng là chất lượng ảnh đầu vào lúc lắp camera thật, không phải lọc dữ liệu.

## Việc còn treo

- [ ] Train thêm 1-2 seed khác để xác định mức giảm accuracy do thêm "Đ" hay do nhiễu train.
- [ ] Commit các thay đổi (đang ở branch `fix/nhat-ocr-charset-md-plate`, chưa commit).
- [ ] Cập nhật `docs/report/chapters/04-ocr.md` với số liệu mới nếu quyết định giữ thay đổi "Đ" (đã quyết định giữ).
- [ ] Quantization mô hình (còn lại của việc Tuần 7).
- [ ] Model phát hiện xe thô (YOLOv8n COCO) còn nhầm SUV thành xe tải, chưa có hướng xử lý.
