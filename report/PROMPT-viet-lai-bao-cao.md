# PROMPT: Viết lại báo cáo ĐATN — gãy gọn, focus, logic, rich figure

Dùng prompt này để hiệu chỉnh format và viết lại từng chương của báo cáo trong `report/`.
Chạy **từng chương một**, không sửa hàng loạt cả báo cáo trong một lượt.

---

## 0. Vai trò

Bạn là người viết luận văn kỹ thuật, viết văn phong học thuật tiếng Việt, ngôi thứ ba.
Mục tiêu: mỗi chương **ngắn hơn 25–40% số chữ** so với bản hiện tại mà **không mất một sự
thật đã kiểm chứng nào**, đọc **trực diện, rành mạch, logic**, hình và bảng nói thay chữ.

Nguồn tham chiếu:
- Báo cáo của ta: `report/chapters/*.tex` (9 chương), `report/frontmatter/`, `report/appendices/`.
- Bản của Nhật: `BaoCao_DATN - v2.docx` (gốc repo) — bản hợp nhất 5 chương, đã kiểm số. Đọc để
  lấy hình/cách trình bày tốt hơn, **không** copy văn dài.
- Số liệu gốc: `src/ml/experiments/` và `src/ml/experiments.csv`.

---

## 1. Nguyên tắc viết (bắt buộc)

1. **Trực diện.** Mỗi mục mở bằng 1 câu nêu vấn đề hoặc kết luận, rồi mới đến bằng chứng.
   Cấu trúc ngầm cho mỗi tiểu mục: *vấn đề → cách giải quyết → kết quả/nhận xét*.
2. **Một ý một đoạn.** Bỏ câu đệm, bỏ nhắc lại bối cảnh, bỏ "như đã biết", "có thể thấy rằng",
   "đáng chú ý là". Không viết dài để lấp trang.
3. **Không lặp giữa các chương.** Mỗi khái niệm giải thích đúng một lần; nơi khác chỉ tham chiếu
   (`Chương~\ref{...}`, `Mục~\ref{...}`).
4. **Ưu tiên bảng/hình thay cho liệt kê dài.** Nếu một đoạn liệt kê 4+ mục có cấu trúc giống
   nhau, chuyển thành bảng.
5. **Mọi con số phải truy được nguồn.** Giữ dòng `% Nguồn: ...` và footnote nguồn dưới mỗi
   bảng/hình. Không có nguồn thì không viết số (theo quy tắc "chỉ báo cáo cái đã kiểm chứng").
6. **Ngôn ngữ.** Tiếng Việt học thuật, ngôi thứ ba (không "em/tôi/ta/nhóm em"). Giữ thuật ngữ
   tiếng Anh chuẩn (mAP, OCR, pipeline, inference...). Số thập phân dùng dấu phẩy (siunitx).
7. **Ký tự gạch.** Không dùng gạch dài/ngắn U+2013/U+2014 và ligature `--`/`---` (cổng
   `check.py` chặn). Giữ gạch trong mã có nghĩa: `TT-BCA`, `X-Edge-Key`, `YOLOv8n`, `mAP@0,5`.
8. Sau khi sửa mỗi chương: chạy `python3 report/check.py` phải PASS.

---

## 2. Sự thật đã chốt — KHÔNG được đổi khi viết lại

**Phát hiện biển (YOLOv8n, bộ A1):**
- mAP@0,5 = **0,983** (sau khử trùng lặp gần, tập test 342 ảnh) / 0,9892 (thô, 572 ảnh, TB 3 seed).
  Dùng **0,983** làm số chính; nêu 0,9892 kèm cảnh báo 230 cặp ảnh gần trùng train↔test.
- mAP@0,5:0,95 = 0,834 (dedup). YOLO26n = 0,9801. Chọn YOLOv8n seed 0.

**OCR (CRNN 37 ký tự, model triển khai) — nguồn `ocr_vnplate_results.csv` variant `current`:**
- a1: **91,9%** (n=172, CER 0,015; 1 dòng 91,5%, 2 dòng 92,3%) — **kết quả điều kiện tiêu chuẩn (headline)**.
- vn_plate: 80,2% (n=96). topkek: 56,6% (n=666; 1 dòng 59,6%, 2 dòng 55,4%).
- So baseline trên topkek: RapidOCR 34,2%, EasyOCR 11,7%. CRNN 425.126 tham số, ONNX 1,7 MB.
- Chữ "Đ": model 37 ký tự đọc đúng 10/17 biển có "Đ" (khớp cả chuỗi 8/17); model 36 ký tự rớt 17/17.

**Phân loại:**
- Loại xe: ResNet18 **98,66%** acc, F1 0,9619 (triển khai). MobileNetV3-Small 97,99%.
- Kiểu dáng: MobileNetV3-Small **90,07%** acc, F1 0,9069 (triển khai). ResNet18 89,97%.

**Raspberry Pi 5 (e2e, cấu hình triển khai):**
- Độ trễ đầu cuối qua API: trung vị **463,4 ms**, p90 487,9 ms (backend suy luận 445,8; ngoài 17,5).
- Suy luận 50 ảnh cổng: trung vị **464,4 ms**. Lượt đầu (nạp model) 4,8 s.
- Năng lượng ~**3,12 J/lượt** (MobileNetV3-Small); ResNet18 3,25 J.
- Pipeline theo luồng (ảnh 12 biển): 1 luồng 813,9 (.pt)/1067,4 (ONNX); 4 luồng 495,3 (.pt)/535,0 (ONNX).
- Model riêng 4 luồng: YOLO 142,9; CRNN 2,3; ResNet18 45,3; MobileNetV3-Small 5,8 ms.
- Kết quả nhận diện Pi khớp máy dev **50/50** cả ba đầu ra. Không throttle trong lúc đo.

**INT8: CHƯA thực hiện.** Chỉ nêu ở "Hướng phát triển". Không có bảng kết quả INT8, không đánh "Đạt".

**Màu biển:** chỉ có nhãn trắng/đỏ (178 crop, đúng 100%). Vàng/xanh chưa có nhãn → mới đánh giá 2/4 màu.

**Dữ liệu:** A1 detect 4.578 ảnh/5.200 biển (1.641 một dòng, 3.559 hai dòng), test dedup 342 ảnh.
B5 kiểu dáng 10.000 ảnh, 12→3 nhóm, 7.014/1.999/987. Loại xe từ A1: 993 ảnh (442 ô tô, 478 xe máy,
73 xe tải), 695/149/149. **Chưa tự thu thập ảnh bãi xe thật** (chỉ tự gán nhãn 2 tập kiểm tra OCR).

**Kiểm thử:** backend 272 pass, edge 3, pipeline 3, màu 24, phát hiện biển 44, frontend 129.

**Phần cứng đo:** Pi5 16 GB, Debian 13, kernel 6.18, Cortex-A76 4 nhân 2,4 GHz. Ghi đúng máy dev
theo file nguồn của từng phép đo (không trộn lẫn hai máy dev khác nhau trong cùng một bảng).

---

## 3. Hình ảnh — rich figure, copy from Nhật khi tốt hơn

Đã có trong `report/figures/`, **dùng lại**:
- `pipeline-example.png` (pipeline kết quả trung gian thật, của Nhật) → dùng thay schematic cũ.
- EDA: `eda_class_distribution`, `eda_plate_area_ratio`, `eda_size_brightness`, `eda_sample_context`.
- Phát hiện: `plate_det_curves`. OCR: `plate_ocr_data_distribution`, `plate_ocr_progression`,
  `plate_ocr_accuracy_comparison`, `plate_ocr_sample_predictions`.
- Kiểu dáng: `vehicle_style_class_distribution`, `vehicle_style_comparison`,
  `vehicle_style_confusion_matrices`, `vehicle_style_loss_curves`, `vehicle_style_resource_usage`.
- UML: `uml-kientruc`, `uml-er`, `uml-seq`, `uml-usecase`, `uml-class`.
- Dashboard (6, phân giải cao): `dashboard-gate-in`, `dashboard-gate-out`, `dashboard-sessions`,
  `dashboard-session-detail`, `dashboard-stats-new`, `dashboard-config`.

Cân nhắc **copy thêm từ Nhật** (đã trích ở `scratchpad/nhat/media/`, nếu cần thì trích lại từ
`BaoCao_DATN - v2.docx`) khi hình của ta yếu hơn:
- `image2` — sơ đồ đối chiếu biển + tính phí khi xe ra (bổ trợ Mục Logic vào/ra Ch7 nếu `uml-seq` chưa rõ).
- `image4` — use case theo tác nhân (nếu `uml-usecase` khó đọc).

Quy tắc hình:
- Mỗi hình **được nhắc trong prose** bằng `Hình~\ref{...}` trước khi xuất hiện.
- Caption ngắn, nêu hình cho thấy điều gì; footnote `{\footnotesize Nguồn: ...}` bên dưới.
- Đặt `\begin{figure}[htbp]`, chừa khoảng trắng đủ; ảnh chân dung để `width=0,5\textwidth`,
  ảnh ngang `0,9`–`0,95\textwidth`. Không nhồi nhiều ảnh sát nhau không caption.
- **Không vẽ hình chỉ để có.** Mỗi hình phải thêm thông tin (số liệu, kiến trúc, hoặc bằng chứng thật).

---

## 4. Bảng biểu — phải rõ ràng

- Dùng `booktabs` (`\toprule`/`\midrule`/`\bottomrule`) trong LaTeX. Bản docx đã tự động thêm viền
  cho mọi bảng qua `report/postprocess.py` (`apply_table_borders`) — **không cần** kẻ viền tay trong tex.
- Mỗi bảng: `\caption{...}` (đánh số), nhãn `\label{tab:...}`, và footnote nguồn.
- Cột số canh phải (`r`), cột chữ canh trái (`l`/`p{}`). Đơn vị ghi ở tiêu đề cột, không lặp trong ô.
- Bảng dài, nhiều mục cùng cấu trúc thì gộp; tránh bảng một cột hoặc bảng chỉ 2 dòng.
- Mọi số trong bảng khớp Mục 2 và khớp file nguồn.

---

## 5. Đánh số mục — phải đầy đủ

- Chỉ dùng `\chapter`/`\section`/`\subsection` **có đánh số** cho nội dung chính (không `\section*`).
- Không để tiểu mục mồ côi (một `\subsection` đứng một mình trong section). Gộp hoặc bỏ.
- Kiểm `secnumdepth` trong `preamble.tex` đủ để hiện số tới `subsection` (và `subsubsection` nếu dùng).
- Mọi hình/bảng có `\caption` để vào `\listoffigures`/`\listoftables`.
- Tham chiếu chéo dùng `\ref`/`\autoref`, không ghi "bảng bên dưới".

---

## 6. Ngân sách và trọng tâm từng chương

Đọc dòng `% Ngân sách` ở đầu mỗi file `.tex` và bám theo. Tổng báo cáo giữ trong 50–100 trang
(cổng `check.py`). Trọng tâm cắt gọn:

| Chương | Trọng tâm khi viết lại |
|---|---|
| 01 Giới thiệu | Giữ: vấn đề đặt ra, 4 câu hỏi NC, mục tiêu, phạm vi, tiêu chí, đóng góp. Cắt lặp bối cảnh. Hình pipeline dùng `pipeline-example`. |
| 02 Liên quan | **Đã đầy đủ hơn bản Nhật — không thêm.** Chỉ cắt câu dài, giữ bảng so sánh + luận điểm sai số cộng dồn + kết quả theo điều kiện. |
| 03 Dữ liệu | Gộp mô tả từng bộ vào 1 bảng; giữ 4 hình EDA; nêu rõ dedup 230 cặp và chưa tự thu thập. |
| 04 Phát hiện | Kết quả 3 seed vào 1 bảng; nhấn 0,983 (dedup) và vì sao chọn YOLOv8n. Cắt lý thuyết YOLO đã có ở Ch2. |
| 05 OCR + màu | **Verbose — cắt mạnh.** Giữ bảng 3 tập (a1/vn_plate/topkek), bảng ablation, so baseline. Màu: nêu rõ 2/4 màu. |
| 06 Phân loại | Bảng loại xe + kiểu dáng; ma trận nhầm lẫn; bài học "học tắt theo nguồn ảnh". Cắt diễn giải dài. |
| 07 Hệ thống | Giữ kiến trúc 2 đường, bảng vai trò/quyền, bảng 2 cấu hình, ER, 6 ảnh dashboard, logic vào/ra, tính phí, bảo mật. Prose ngắn, bám mã. |
| 08 Triển khai | **Verbose — cắt mạnh.** Bỏ hẳn INT8 (chỉ future work). Giữ bảng độ trễ Pi (model riêng, toàn pipeline, e2e API), PC-vs-Pi, công suất/nhiệt, so sánh công trình liên quan. |
| 09 Kết luận | Trả lời 4 câu hỏi NC, bảng đối chiếu mục tiêu, giới hạn, hướng phát triển (gồm INT8). Ngắn, không lặp số đã nêu ở Ch8. |

---

## 7. Quy trình cho MỖI chương

1. Đọc file `.tex` của chương và các file nguồn số liệu liên quan.
2. Đối chiếu số trong chương với Mục 2; sửa số sai, xóa số không có nguồn.
3. Viết lại theo Mục 1 (trực diện, gãy gọn); chuyển liệt kê dài thành bảng; đảm bảo mọi hình/bảng
   được nhắc trong prose, có caption + nguồn + đánh số.
4. Không đổi label đang được `\ref` ở chương khác; nếu buộc phải đổi, sửa luôn nơi tham chiếu.
5. Chạy `python3 report/check.py` → PASS.
6. Dựng thử docx: `bash report/build.sh` (hoặc chỉ chạy `pandoc` + `postprocess.py` như trong
   build.sh) → mở `report/main.docx` kiểm bảng có viền, hình đủ caption, mục đánh số đủ.
7. Không `git commit`/`push` (theo quy ước dự án) — để thay đổi ở trạng thái chưa commit.

---

## 8. Giữ nguyên (không "sửa" thành sai)

- mAP dedup 0,983 (nghiêm hơn 0,9892 thô) — **giữ của ta**, đừng thay bằng số thô của Nhật.
- Đánh giá màu trắng/đỏ 178 crop của ta — **giữ**, chỉ nói rõ mới 2/4 màu.
- Ch2 liên quan của ta đầy đủ hơn bản Nhật — **không port thêm**.
- Cấu trúc 9 chương hiện tại — giữ, chỉ cắt gọn nội dung.
- Kết quả kiểm thử, tên bảng/trường CSDL, tên biến môi trường lấy đúng từ mã nguồn.
