# Kickoff prompt: viết đồ án, output DOCX theo biểu mẫu chính thức

Dán khối dưới vào một session mới để bắt đầu lại phần spec quy trình viết.

---

```
Viết đồ án tốt nghiệp UIT "Hệ thống quản lý bãi giữ xe thông minh ứng dụng thị
giác máy tính và Edge AI". Bắt đầu LẠI phần spec quy trình viết, output chính là
DOCX. Dùng superpowers: brainstorming -> writing-plans, ghi spec vào
docs/superpowers/specs/YYYY-MM-DD-hinh-thuc-docx-design.md.

## Chuẩn hình thức: BẮT BUỘC theo đúng hai file, không sáng tạo thêm
- report/BieuMau.docx  — biểu mẫu chính thức: bố cục bìa chính, bìa phụ (có GVHD),
  trang thông tin hội đồng chấm, thứ tự front matter, phân cấp tiêu đề tới 4 mức
  (Chương N / N.M / N.M.P / N.M.P.Q), tên chương IN HOA.
- report/phuluc2_hinhthuctrinhbay (3).docx — quy định trình bày.
Đọc và trích đúng cả hai TRƯỚC khi thiết kế. Nếu LaTeX và pandoc không thể tái tạo
100% một chi tiết của BieuMau, chọn đường tạo DOCX bám sát BieuMau nhất (reference.docx
lấy style từ BieuMau) và ghi rõ chỗ lệch.

## Ràng buộc cứng (từ hai file trên)
- Output nộp: DOCX khớp BieuMau. PDF chỉ là bản phụ để soát.
- Font Times New Roman 13pt, giãn dòng 1,5.
- Lề: trên 3cm, dưới 3,5cm, trái 3,5cm, phải 2cm.
- Thân bài tối thiểu 50 trang, không quá 100 (không kể bìa, cảm ơn, mục lục, TLTK).
  Tóm tắt (Abstract) 1 đến 2 trang.
- Front matter đúng thứ tự: bìa chính, bìa phụ, thông tin hội đồng chấm, lời cảm ơn,
  mục lục, danh mục hình, danh mục bảng, danh mục từ viết tắt (xếp alphabet), tóm tắt.
- Đánh số trang: KHÔNG đánh cho hội đồng/cảm ơn/mục lục/các danh mục; bắt đầu số Ả Rập
  TỪ Tóm tắt; đặt GIỮA BÊN DƯỚI.
- Bố cục nội dung 6 phần: MỞ ĐẦU, TỔNG QUAN, NGHIÊN CỨU (Model/Method), ĐÁNH GIÁ KẾT QUẢ
  (đề tài phần mềm PHẢI có hồ sơ thiết kế UML: use case, lớp, tuần tự, ER), KẾT LUẬN,
  HƯỚNG PHÁT TRIỂN, TÀI LIỆU THAM KHẢO, PHỤ LỤC.
- Tiêu đề: "Chương N" bold 14pt; mục N.M / tiểu mục N.M.P bold 13pt; số Ả Rập, không La Mã.
- Hình/bảng đánh số theo chương (Hình 3.1, Bảng 3.1); mỗi cái có caption và ghi rõ nguồn.
  Bảng xoay ngang thì đầu bảng ở lề trái.
- Chú thích (footnote) đánh số, ghi ở cuối trang.
- TLTK theo IEEE, TÁCH RIÊNG tài liệu tiếng Việt và tiếng Anh, mỗi danh mục xếp alphabet
  theo tên tác giả.

## Quyết định đã chốt (không hỏi lại)
- Nhắm 70 đến 90 trang, viết dày, khai thác mọi nội dung có thật.
- MỘT báo cáo tiếng Việt (không dịch song ngữ). Chỉ TLTK tách hai danh mục Việt/Anh.
- Giữ khung 9 chương hiện có, ánh xạ vào 6 phần chính thức. UML đặt trong chương Hệ thống.

## Hiện trạng repo (đã có, tái dùng, đừng dựng lại)
- report/ là nguồn LaTeX duy nhất; build.sh sinh PDF (xelatex+biber) và DOCX (pandoc+
  citeproc, ieee.csl, reference.docx). check.py là cổng kiểm tra tự động.
- 9 file chương chapters/01..09, refs.bib 89 entry, main.tex, preamble.tex.
- Chương 1 và 2 đã viết bản đầy đủ. Chương 3,5,6 có nháp chuyển từ Markdown. 4,7,8,9 còn khung.
- Figure sinh qua src/ml/figstyle.py (Times, xuất cả .pdf 300dpi lẫn .png). 3 hình đã sinh:
  eda_class_distribution, plate_ocr_progression, vehicle_style_confusion_matrices.
- Toolchain còn thiếu biber và latexmk (cần sudo tlmgr, người dùng tự cài).

## Sự thật code đã kiểm chứng (docs/report/tuan-*.md ghi SAI, đừng chép)
- Đường suy luận VẪN cần torch; hai detector chạy .pt qua ultralytics, chỉ OCR và
  classifier kiểu dáng chạy ONNX.
- Mô hình kiểu dáng triển khai là ResNet18, KHÔNG phải MobileNetV3-Small.
- Detector biển số chạy .pt, không phải .onnx.
- Classifier kiểu dáng chỉ chạy khi yolo_class == "car".
- charset OCR đúng 37 ký tự (có "Đ").
- Backend và edge worker dùng chung một runner OnnxAlprPipeline.

## Luật viết (ưu tiên cao nhất, ghi đè mặc định)
- Không tự chạy git commit hay git push. Chỉ git add rồi dừng.
- Không dùng gạch ngang trong prose, kể cả ligature -- và ---. Chỉ giữ trong mã có
  nghĩa: 51A-0718, 24/2023/TT-BCA, MobileNetV3-Small.
- Ngôi thứ ba, văn phong học thuật tiếng Việt; thuật ngữ tiếng Anh chuẩn giữ nguyên,
  lần đầu ghi "tiếng Việt (English)".
- KHÔNG bịa số. Chỗ chưa rõ: \wip{} cho đoạn, \ph{} cho số. Mọi số truy được về file
  nguồn, ghi đường dẫn trong comment LaTeX ngay trên bảng. Mọi luận điểm từ tài liệu
  có \autocite với key tồn tại trong refs.bib.

## Việc đầu tiên
Brainstorm để dựng spec mới đè spec cũ (2026-09-09-ke-hoach-viet-bao-cao-design.md và
report/PLAN.md), tập trung: cơ chế tạo DOCX khớp BieuMau, ánh xạ 9 chương vào 6 phần,
phân bổ trang cho mốc 70-90, cấu hình TLTK tách Việt/Anh, và cập nhật cổng check.py
(sàn 50 / trần 100 thay cho trần 35).
```
