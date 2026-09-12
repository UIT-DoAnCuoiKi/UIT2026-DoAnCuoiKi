# Kickoff prompt: viết nội dung 9 chương báo cáo (máy tạo DOCX đã xong)

Dán khối dưới vào một session mới để bắt đầu phase viết nội dung.

---

```
Viết nội dung báo cáo đồ án tốt nghiệp UIT "Hệ thống quản lý bãi giữ xe thông minh
ứng dụng thị giác máy tính và Edge AI". MÁY tạo DOCX khớp BieuMau đã hoàn tất; việc
bây giờ là VIẾT NỘI DUNG 9 chương cho đủ 70 đến 90 trang thân bài, từ dữ liệu có
thật, không bịa số.

Dùng superpowers: brainstorming -> writing-plans -> subagent-driven-development.
Phân rã theo chương hoặc cụm chương, mỗi cụm một plan. Chỉ sửa report/chapters/*.tex,
report/frontmatter/*, refs.bib, figures/. KHÔNG dựng lại máy build.

## Nền tảng đã có (đọc trước, tái dùng, đừng dựng lại)
- Spec hình thức: docs/superpowers/specs/2026-09-10-hinh-thuc-docx-design.md (nguồn chân lý).
- Plan máy build: docs/superpowers/plans/2026-09-10-hinh-thuc-docx-build.md.
- report/ LaTeX là nguồn duy nhất. build.sh sinh PDF proof + main.docx khớp BieuMau.
  postprocess.py dựng front matter, đánh số trang, field mục lục, tách thư mục Việt/Anh.
  ieee-vi-en.csl xếp thư mục Việt trước Anh, số IEEE liên tục, trích dẫn tự khớp.
- check.py là cổng kiểm. Chạy `python3 report/check.py`, phải sạch trước khi coi là xong.
- docs/report/chapters/*.md (01-tongquan, 02-dulieu, 04-ocr, 05-phanloai) ĐÓNG BĂNG làm
  lịch sử. Không sửa; chỉ trích nội dung sang .tex.
- 14 note trong docs/research/ cấp trích dẫn và số liệu.

## Trạng thái chương hiện tại (dòng .tex)
- 03-dulieu (309), 05-ocr-maubien (406), 06-phanloai (303): bản thảo dày, cần đánh bóng,
  bổ sung hình + dòng Nguồn, chốt số, kiểm \autocite.
- 01-gioithieu (58), 02-lienquan (46): bản thảo NGẮN, phải mở rộng cho đủ 5 và 8 trang.
- 04-phathien (24), 07-hethong (28), 08-trienkhai (50), 09-ketluan (21): KHUNG, viết mới.
- Placeholder còn: 08 có 14, 07 có 7, 09 có 5, 04 có 5, 03 có 2, 05 có 1 chỗ \wip/\ph.

## Ngân sách trang thân bài (nhắm ~78, band 70 đến 90)
Tóm tắt 1,5 | Ch1 5 | Ch2 8 | Ch3 9 | Ch4 8 | Ch5 14 | Ch6 6 | Ch7 12 | Ch8 11 | Ch9 4.
Phụ lục A,B,C khoảng 10 trang, KHÔNG tính vào sàn 50 trần 100. Vượt hạn chương thì cắt
chương đó, không mượn trang chương khác.

## Ánh xạ 9 chương vào 6 phần chính thức (không có heading PHẦN)
MỞ ĐẦU=Ch1 | TỔNG QUAN=Ch2 | NGHIÊN CỨU=Ch3,4,5,6 | ĐÁNH GIÁ KẾT QUẢ (kèm UML)=Ch7,8 |
KẾT LUẬN+HƯỚNG PHÁT TRIỂN=Ch9 | TLTK, PHỤ LỤC=back matter.
UML đặt trong Ch7 (use case, lớp, tuần tự, ER). Dùng skill architecture-diagrams / TikZ.

## Nguồn số liệu theo chương
- Ch1: docs/DCDATN_*.docx, README.md, docs/report/chapters/w1-tongquan.docx. Hình pipeline mới.
- Ch2: docs/report/chapters/01-tongquan.md (mục 2.3, 2.4, 2.6) + docs/research/
  2026-07-18-yolo-architecture.md, 2026-07-19-similar-parking-systems.md,
  khao-sat-he-thong-alpr.md (mục 2.1, 2.2, 2.5).
- Ch3: docs/report/chapters/02-dulieu.md, docs/research/quy-dinh-bien-so-xe-vn.md,
  2026-07-28-dataset-inventory-verified.md, docs/research/eda_outputs/*.csv.
- Ch4: src/ml/experiments.csv, src/ml/plate_detection_pipeline/output/*/results.csv.
  Số PHẢI đo mới: eval A1 sau khử trùng lặp gần (drop_dups=True), báo mAP trước và sau.
- Ch5: docs/report/chapters/04-ocr.md, src/ml/experiments/ocr_full_progression.csv,
  ocr_comparison.csv, ocr_baselines_summary.csv, docs/research/2026-08-29-sua-loi-ky-tu-D*.md.
- Ch6: docs/report/chapters/05-phanloai.md, src/ml/experiments.csv.
- Ch7: docs/architecture/current-architecture.md, docs/report/tuan-08.md, 12 spec trong
  docs/superpowers/specs/, code src/backend/app/, src/frontend/src/features/.
- Ch8: docs/report/tuan-07.md, tuan-08.md, src/edge/worker.py, src/ml/pipeline/onnx_pipeline.py.
- Ch9: tổng hợp, đối chiếu đề cương, giới hạn, hướng phát triển.

## Thí nghiệm cam kết đo (lấy số thật, KHÔNG placeholder khi đã có)
- Eval lại A1 sau khử trùng lặp gần (drop_dups=True): mAP trước và sau.
- Độ chính xác đọc biển end to end trên bộ ảnh cổng.
- Lượng tử hóa INT8 và bảng so sánh trước sau khi nén.
Để placeholder \ph{} tới khi có dữ liệu:
- Benchmark Raspberry Pi 5 thật (độ trễ, FPS, RAM, CPU). Mục 8.5 ghi rõ tình trạng.

## Đính chính sự thật code (báo cáo tuần ghi SAI, phải ghi đúng trong chương)
- Suy luận VẪN cần torch; hai detector chạy .pt qua ultralytics; chỉ OCR và classifier
  kiểu dáng chạy ONNX.
- Mô hình kiểu dáng triển khai là ResNet18, KHÔNG phải MobileNetV3-Small (vẫn giữ bảng
  so sánh hai model, nhưng bản triển khai là ResNet18).
- Detector biển số chạy .pt, không phải .onnx.
- Classifier kiểu dáng chỉ chạy khi yolo_class == "car".
- charset OCR đúng 37 ký tự, có "Đ".
- Backend và edge worker dùng chung một runner OnnxAlprPipeline.

## Hình cần xử lý
Đã có .pdf: eda_class_distribution, plate_ocr_progression, vehicle_style_confusion_matrices.
Chương đang trỏ tới NHIỀU .png CHƯA sinh: eda_plate_area_ratio, eda_sample_context,
eda_size_brightness, plate_ocr_accuracy_comparison, plate_ocr_data_distribution,
plate_ocr_edge_comparison, plate_ocr_loss_curves, plate_ocr_resource_usage,
plate_ocr_sample_predictions, vehicle_style_class_distribution, vehicle_style_comparison,
vehicle_style_loss_curves, vehicle_style_resource_usage, pipeline. Mỗi hình: hoặc SINH lại
qua src/ml/figstyle.py + notebook (font serif Times, xuất cả .pdf lẫn .png), hoặc bỏ tham
chiếu. Chốt danh mục hình chính thức, cắt phần thừa xuống phụ lục hoặc bỏ.

## Văn phong (bắt buộc)
- Tinh gọn, rõ ràng, rành mạch, logic. Không lan man, không viết dài lấy trang.
- Viết TRỌN ý nhưng gãy gọn: một ý một đoạn, đoạn tối đa năm câu, bỏ câu chuyển tiếp rỗng.
- Trình bày đầy đủ thông tin nhưng KHÔNG bịa. Đủ trang bằng nội dung thật (phân tích, bảng,
  hình, hồ sơ thiết kế), không bằng chữ độn.
- Phần nào chưa viết được PHẢI đánh dấu để bổ sung: \wip{ghi rõ còn thiếu gì} cho đoạn,
  \ph{...} cho số. Không để trống lặng lẽ, không lấp bằng phỏng đoán.

## Luật viết (ưu tiên cao nhất, cổng check.py bắt)
- R1: KHÔNG tự git commit/push. Chỉ git add rồi dừng.
- R2: KHÔNG gạch ngang trong prose, kể cả -- và ---. Chỉ giữ trong mã có nghĩa: 51A-0718,
  24/2023/TT-BCA, MobileNetV3-Small.
- R3: ngôi thứ ba, học thuật tiếng Việt; thuật ngữ tiếng Anh chuẩn giữ nguyên, lần đầu ghi
  "tiếng Việt (English)". Không "chúng em", "chúng tôi".
- R4: KHÔNG bịa số. \ph{} cho số, \wip{} cho đoạn. Mọi số truy về file nguồn, ghi đường
  dẫn trong comment LaTeX ngay trên bảng.
- Mọi luận điểm từ tài liệu có \autocite{key}, key PHẢI tồn tại trong refs.bib. Ref mới
  thêm phải gắn langid = {vietnamese|english} (nếu không, cổng langid FAIL).
- Mọi hình và bảng có \caption VÀ một dòng "Nguồn: ..." trong vòng 3 dòng (cổng caption
  bắt; hiện 16 caption thiếu nguồn).
- Nếu trích văn bản pháp luật tiếng Việt (ví dụ Thông tư TT-BCA) thì thêm entry refs.bib
  langid=vietnamese để nhóm "Tài liệu tiếng Việt" có nội dung.

## Quy trình mỗi vòng
1. brainstorming chốt sườn chương/cụm, đối chiếu ngân sách trang và danh mục hình.
2. writing-plans ra plan chi tiết cho chương/cụm.
3. subagent-driven-development thực thi, mỗi task một subagent, review giữa các task.
4. Sau mỗi chương: chạy `cd report && ./build.sh` (PDF stage có thể trượt nếu thiếu
   latexmk, bỏ qua) và `python3 report/check.py`. Chương coi là xong khi build ra main.docx
   và các cổng nội dung của chương đó sạch.
5. Cài toolchain còn thiếu (cần sudo, người dùng tự chạy):
   sudo tlmgr update --self && sudo tlmgr install biblatex biber biblatex-ieee \
     babel-vietnamese siunitx latexmk

## Việc đầu tiên
Brainstorm để chốt thứ tự viết (đề xuất: 04, 07, 08, 09 khung trước vì trống nhất; rồi
mở rộng 01, 02; rồi đánh bóng 03, 05, 06 và sinh hình). Chốt danh mục hình chính thức và
những thí nghiệm chạy ngay. Sau đó ra plan cho cụm đầu tiên.
```

---

Ghi chú: prompt trên là self-contained. Trạng thái số liệu (dòng .tex, placeholder, hình
thiếu) chụp ngày 11/09/2026; kiểm lại bằng `wc -l report/chapters/*.tex` và
`grep -rc '\wip{\|\ph{' report/chapters/` nếu đã có thay đổi.
