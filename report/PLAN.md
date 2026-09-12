# Kế hoạch xây dựng báo cáo

Báo cáo đồ án tốt nghiệp, *Hệ thống quản lý bãi giữ xe thông minh ứng dụng thị giác máy tính và Edge AI*.
Định dạng bám file mẫu `Nhom_6-CS340.F21.CN2.TTNT-IOT_AI.pdf` (báo cáo Nhóm 6, UIT).
Cập nhật 09/09/2026.

## 1. Nguyên tắc

- **`report/` là nguồn duy nhất.** Bản thảo Markdown ở `docs/report/chapters/*.md` đã đóng băng ngày 09/09/2026, chỉ giữ để tra cứu.
- **Hai định dạng đầu ra từ một nguồn.** `./build.sh` sinh `main.pdf` (XeLaTeX kèm biber) và `main.docx` (pandoc kèm citeproc).
- **Mỗi chương một file** trong `chapters/`, nạp qua `\input` ở `main.tex`.
- **Đánh dấu phần chưa viết** bằng `\wip{...}` (đỏ) và số liệu chưa có bằng `\ph{...}` (cam). Cổng kiểm tra bắt được cả hai.

## 2. Cấu trúc file

```
report/
  main.tex               cấu hình đề tài + thứ tự \input
  preamble.tex           gói, font, header/footer, định dạng tiêu đề, IEEE bib
  build.sh               sinh PDF và DOCX
  check.py               cổng kiểm tra tự động
  ieee.csl               style trích dẫn cho đường DOCX
  reference.docx         template style DOCX, đã chỉnh Times New Roman 13pt
  refs.bib               đồng bộ từ docs/research/refs.bib (bản superset, 89 entry)
  frontmatter/           titlepage, abstract
  chapters/01..09-*.tex  9 chương
  appendices/A,B,C-*.tex phụ lục
  figures/               .pdf và .png sinh từ src/ml/figstyle.py
```

## 3. Khung 9 chương và ngân sách trang

Mục tiêu 25 trang toàn quyển, trần cứng 35. Vượt hạn chương thì cắt chương đó, không mượn trang chương khác.

| Ch | File | Nội dung | Mục tiêu | Trần | Phụ trách |
|---|---|---|---:|---:|---|
| 1 | `01-gioithieu.tex` | Bối cảnh, vấn đề, mục tiêu, đóng góp, cấu trúc báo cáo | 1,5 | 2,0 | Cả 2 |
| 2 | `02-lienquan.tex` | YOLO, ALPR, ALPR Việt Nam, bãi giữ xe, Edge AI, khoảng trống | 1,5 | 2,5 | Cả 2 |
| 3 | `03-dulieu.tex` | Quy định biển số, bộ dữ liệu, EDA, trùng lặp gần, tiền xử lý | 2,0 | 3,0 | Cả 2 |
| 4 | `04-phathien.tex` | YOLOv8n với YOLO26n, kết quả, giới hạn detector xe | 2,0 | 3,0 | Nhật |
| 5 | `05-ocr-maubien.tex` | CRNN kèm CTC, bốn vòng cải tiến, ký tự Đ, hậu xử lý, màu biển | 3,0 | 4,5 | Nhật + Đức |
| 6 | `06-phanloai.tex` | ResNet18 với MobileNetV3-Small, lựa chọn cho biên | 1,5 | 2,0 | Nhật |
| 7 | `07-hethong.tex` | Kiến trúc hai đường, CSDL, vào ra, phí, phân quyền, dashboard | 2,5 | 4,0 | Đức |
| 8 | `08-trienkhai.tex` | Pi 5, đóng gói ONNX, giao thức đo, kết quả, so PC với Pi | 2,5 | 4,0 | Cả 2 |
| 9 | `09-ketluan.tex` | Đóng góp, đối chiếu đề cương, giới hạn, hướng phát triển | 1,0 | 1,0 | Cả 2 |
| | | **Thân bài** | **17,5** | **26,0** | |

Ngoài thân bài: bìa 1, tóm tắt 1, mục lục và hai danh sách 2, tài liệu tham khảo 1,5, phụ lục 2. Đã bỏ lời cảm ơn để tiết kiệm trang.

**10 hình, 7 bảng.** Hình: sơ đồ pipeline (ch1), phân bố lớp (ch3), biển một và hai hàng (ch5), tiến trình OCR (ch5), kết quả đọc biển trên ảnh mẫu (ch5), ma trận nhầm lẫn (ch6), kiến trúc hai đường (ch7), giao diện trạm cổng (ch7), phân phối độ trễ Pi 5 (ch8), nhận diện end to end trên ảnh thật (ch8). Bảng: thống kê dữ liệu, YOLOv8n với YOLO26n, OCR V0 tới V3, so engine pretrained, ResNet18 với MobileNetV3-Small, tổng hợp theo thành phần, PC với Pi 5.

## 4. Rule viết

| # | Rule | Cách kiểm |
|---|---|---|
| R1 | Chỗ chưa rõ dùng `\ph{...}` cho số, `\wip{...}` cho đoạn. Không bịa số, không ước lượng | `check.py` cổng R1 |
| R2 | Mọi số liệu truy được về file nguồn. Ghi đường dẫn nguồn trong comment LaTeX ngay trên mỗi bảng | Rà từng bảng |
| R3 | Một ý một đoạn, đoạn tối đa 5 câu. Không lặp nội dung giữa các chương | Đọc soát |
| R4 | Bám ngân sách trang ở mục 3 | `check.py` cổng R4 |
| R5 | Ngôi thứ ba, văn phong học thuật. Không "chúng em", "chúng tôi". Thuật ngữ tiếng Anh giữ nguyên khi đã chuẩn: mAP, quantization, inference, bounding box, dataset, precision, recall, F1, FPS, CER. Lần đầu ghi "tiếng Việt (English)" | `check.py` cổng R5 |
| R6 | Times New Roman 13pt, giãn 1,5, lề 3/2/2,5cm, header hai bên, "Chương N.", hình và bảng đánh số toàn cục, booktabs, IEEE `[1]` | Có sẵn trong `preamble.tex` |
| R7 | Một họ font cho prose, bảng và hình. Figure sinh bằng `src/ml/figstyle.py`, xuất cả `.png` 300dpi lẫn `.pdf` | Kiểm bằng mắt |
| R8 | Mọi luận điểm từ tài liệu phải có `\autocite{key}`, key tồn tại trong `refs.bib` | `check.py` cổng R8 |
| R9 | Không dùng gạch ngang trong prose, kể cả ligature `--` và `---` của LaTeX. Chỉ giữ trong mã có nghĩa: `51A-0718`, `24/2023/TT-BCA`, `MobileNetV3-Small` | `check.py` hai cổng R9 |
| R10 | Không tự chạy `git commit` hay `git push`. Chỉ `git add` rồi để người dùng commit | Theo `CLAUDE.md` |

## 5. Sự thật đã kiểm chứng từ code

Bốn điểm sau đối chiếu code ngày 09/09/2026. Tài liệu trong `docs/report/tuan-*.md` ghi sai, **không chép lại**.

| Sự thật | Bằng chứng |
|---|---|
| Đường suy luận **vẫn cần torch**. Chỉ OCR và classifier kiểu dáng chạy ONNX; hai detector chạy `.pt` qua ultralytics | `src/ml/predict_vehicle.py:29` và `:49`, `src/ml/plate_detection_pipeline/plate_detect/inference/plate_detector.py:53` |
| Mô hình kiểu dáng đang triển khai là **ResNet18** 43 MB, không phải MobileNetV3-Small. Bản ONNX của MobileNet không có trong repo | `src/ml/pipeline/onnx_pipeline.py`, `_DEFAULTS["style_onnx"]` |
| Detector biển số triển khai là `.pt` | `_DEFAULTS["plate_weights"]` trỏ `.../yolov8n_s0_640/weights/best.pt` |
| Classifier kiểu dáng **chỉ chạy khi** `yolo_class == "car"` | `src/ml/pipeline/onnx_pipeline.py`, nhánh `if det_info["yolo_class"] == "car"` |
| charset OCR đúng 37 ký tự | `src/ml/pipeline/ocr.py:28` |
| Backend và edge worker dùng chung một runner | `src/backend/app/services/ml_inference.py` và `src/edge/worker.py:214` |

## 6. Cài công cụ (một lần)

BasicTeX thiếu 5 gói. Chạy:

```bash
sudo tlmgr update --self && sudo tlmgr install biblatex biber biblatex-ieee babel-vietnamese siunitx latexmk
```

Kiểm tra đủ chưa:

```bash
for b in xelatex biber latexmk pandoc; do printf "%-10s " "$b"; command -v $b >/dev/null && echo OK || echo MISSING; done
for p in biblatex.sty siunitx.sty vietnamese.ldf ieee.bbx; do printf "%-16s " "$p"; kpsewhich $p >/dev/null 2>&1 && echo OK || echo MISSING; done
```

Cả 8 dòng phải in `OK`.

## 7. Biên dịch và kiểm tra

```bash
./report/build.sh          # sinh main.pdf và main.docx
python3 report/check.py    # cổng kiểm tra, exit 0 khi mọi cổng OK
```

## 8. Xuất DOCX

`build.sh` chạy pandoc với `--citeproc --csl=ieee.csl --reference-doc=reference.docx --resource-path=.:figures`.

Đã kiểm chứng chạy được: `\autocite` ra `[1]` kiểu IEEE, danh mục tài liệu tham khảo đúng style, ảnh nhúng vào `word/media/`, bảng booktabs và dấu phẩy thập phân giữ nguyên, font Times New Roman 13pt.

Hai chỗ lệch so với bản PDF, phải sửa tay trong Word nếu DOCX là bản nộp chính:

1. Đánh số chéo ra dạng "Hình 1.1" thay vì "Hình 1", vì pandoc không đọc phần đánh số toàn cục trong `preamble.tex`.
2. Caption của figure có thể rơi mất. Kiểm từng hình, thiếu thì gõ lại.
3. Header hai bên và số trang không sang được, phải đặt lại trong Word.

Quy ước ảnh giúp một nguồn ra hai định dạng: mọi `\includegraphics` viết **không đuôi**, XeLaTeX bắt `.pdf`, pandoc bắt `.png`.

## 9. Quy trình viết mỗi chương

1. Đọc file nguồn ghi trong comment đầu file chương, và kết quả thí nghiệm trong `src/ml/experiments/`.
2. Viết tiếng Việt học thuật. Mọi luận điểm từ tài liệu phải `\autocite`, mọi số liệu phải truy được về log thí nghiệm.
3. Thay `\wip{}` và `\ph{}` bằng nội dung và số thật.
4. Chạy `./report/build.sh` rồi `python3 report/check.py`, sửa hết cổng hỏng trước khi coi là xong.

## 10. Checklist trước khi nộp

- [ ] `python3 report/check.py` trả exit 0, mọi cổng in `OK`
- [ ] Số trang nằm trong khoảng 25 tới 35
- [ ] Mở `main.docx` bằng Word, kiểm ba chỗ lệch ở mục 8
- [ ] Tóm tắt, từ khoá và phụ lục hoàn tất
