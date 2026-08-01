# Kế hoạch xây dựng báo cáo (LaTeX)

Báo cáo đồ án tốt nghiệp — *Hệ thống quản lý bãi giữ xe thông minh (Computer Vision + Edge AI)*.
Định dạng bám theo file mẫu `Nhom_6-CS340.F21.CN2.TTNT-IOT_AI.pdf` (báo cáo Nhóm 6, UIT).

## 1. Nguyên tắc

- **Viết song hành theo từng giai đoạn:** kết thúc mỗi tuần/pha → hoàn thiện chương tương ứng. Không để dồn về cuối.
- **Engine:** XeLaTeX (bắt buộc, do tiếng Việt qua `fontspec`).
- **Mỗi chương = 1 file** trong `chapters/`, nạp qua `\input` ở `main.tex`. Thêm dần, không sửa cấu trúc chung.
- **Đánh dấu phần chưa viết** bằng `\wip{...}` (đỏ) và số liệu placeholder bằng `\ph{...}` (cam) → dễ `grep` khi rà soát.

## 2. Cấu trúc file

```
report/
  main.tex               # cấu hình đề tài + thứ tự \input (điểm vào)
  preamble.tex           # gói, font, header/footer, định dạng tiêu đề, IEEE bib
  frontmatter/
    titlepage.tex        # trang bìa (bám mẫu)
    loicamon.tex         # lời cảm ơn (tùy chọn)
    abstract.tex         # Tóm tắt nội dung + Từ khóa
  chapters/01..09-*.tex  # 9 chương, mỗi chương 1 pha
  appendices/A,B,C-*.tex # phụ lục
  figures/               # ảnh, sơ đồ, biểu đồ (.png/.pdf)
  refs.bib               # bản sao từ research/refs.bib (nguồn superset)
```

## 3. Ánh xạ chương ↔ tuần ↔ người phụ trách

| Chương | File | Tuần | Phụ trách | Điều kiện "viết được" |
|---|---|---|---|---|
| 1. Tổng quan | `01-tongquan.tex` | 1 | Cả 2 | Xong khảo sát tài liệu + chốt phạm vi |
| 2. Dữ liệu | `02-dulieu.tex` | 2 | Cả 2 | Có tập dữ liệu đã gắn nhãn + thống kê split |
| 3. Phát hiện xe & biển số | `03-phathien.tex` | 3 | Nhật | Detector đạt mAP mục tiêu (`experiments.csv`) |
| 4. OCR & màu biển | `04-ocr-maubien.tex` | 3–4 | Nhật + Đức | OCR đọc được chuỗi; module HSV chạy |
| 5. Phân loại phương tiện | `05-phanloai.tex` | 5 | Nhật | Có classifier + metrics |
| 6. Hệ thống quản lý | `06-hethong.tex` | 4–6 | Đức | DB + vào/ra + phí + dashboard chạy |
| 7. Triển khai biên | `07-trienkhai.tex` | 7–8 | Nhật + Đức | Mô hình ONNX/quantized; chạy trên Pi 5 |
| 8. Đánh giá & thảo luận | `08-danhgia.tex` | 9 | Cả 2 | Có bảng metrics đầy đủ + so sánh PC/Edge |
| 9. Kết luận | `09-ketluan.tex` | 10 | Cả 2 | Sau khi có toàn bộ kết quả |
| Tóm tắt + Lời cảm ơn | `frontmatter/` | 10 | Cả 2 | Viết sau cùng |

> Ghi chú cấu trúc: file mẫu là báo cáo môn học nên gộp còn 7 chương. Báo cáo này chia **9 chương theo pha** để "bổ sung dần theo quá trình" đúng yêu cầu + khớp đề cương (`docs/DCDATN...`). Nếu GVHD yêu cầu gộp theo mẫu (Giới thiệu / Liên quan / Phương pháp / Kiến trúc / Thí nghiệm / Thảo luận / Kết luận) thì gộp file, giữ nguyên preamble.

> Lệch pha ↔ chương so với bảng tiến độ đề cương (gộp theo chủ đề, không bỏ nội dung):
> - **Màu biển** là pha Tuần 3 trong đề cương nhưng gộp vào Chương 4 (cùng chủ đề xử lý biển với OCR).
> - **Tích hợp hệ thống (Tuần 6, "Cả 2")** là một mốc riêng trong đề cương → nằm ở mục cuối Chương 6 (`Tích hợp End-to-End trên PC`). Khi viết, ghi rõ đây là công việc chung của cả hai.

## 4. Format bám file mẫu (đã cấu hình sẵn trong `preamble.tex`)

- Font **Times New Roman** 13pt, giãn dòng 1.5, lề trái 3cm / phải 2cm / trên–dưới 2.5cm.
- **Header 2 bên** mọi trang: trái `UIT – Đồ án tốt nghiệp`, phải tựa ngắn + tên SV; số trang ở giữa chân trang.
- Tiêu đề **`Chương N. Tựa`**, mục **`N.M.`**, tiểu mục **`N.M.K.`** (có dấu chấm sau số).
- **Hình/bảng đánh số toàn cục** (Hình 1, Bảng 1...) như mẫu; bảng dùng `booktabs`.
- Tên tiếng Việt tự động (`Mục lục`, `Danh sách hình vẽ`, `Danh sách bảng`, `Tài liệu tham khảo`) qua `babel` vietnamese.
- **Trích dẫn IEEE** (đánh số `[1]`) qua `biblatex` style `ieee`, `sorting=none` (theo thứ tự xuất hiện). Dùng `\autocite{key}`.

## 5. Cài công cụ (một lần)

BasicTeX hiện **thiếu** `biblatex`, `biber`, `babel-vietnamese`, `siunitx`. Chạy trong prompt Claude Code:

```
! sudo tlmgr update --self && sudo tlmgr install biblatex biber biblatex-ieee babel-vietnamese siunitx
```

(Teammate trên máy khác: cài đủ MacTeX/TeX Live full là có sẵn.)

## 6. Biên dịch

```
cd report
latexmk -xelatex main.tex        # tự chạy xelatex + biber + xelatex ×2
# hoặc thủ công:
xelatex main.tex && biber main && xelatex main.tex && xelatex main.tex
```

Nếu chưa cài `latexmk`: `sudo tlmgr install latexmk`.

## 7. Quy trình viết mỗi chương (theo skill `thesis-writer`)

1. Đọc note `research/*.md` + kết quả thí nghiệm (`src/ml/experiments.csv`).
2. Chốt outline (mục, hình, bảng) — xác nhận với GVHD/nhóm trước khi viết prose.
3. Viết tiếng Việt học thuật; **mọi luận điểm từ tài liệu phải `\autocite`**, **mọi số liệu phải truy được về log thí nghiệm/benchmark**.
4. Thay `\wip{}`/`\ph{}` bằng nội dung/số thật; chèn hình vào `figures/`.
5. Biên dịch, sửa hết warning trước khi xem là "xong".

## 8. Checklist trước khi nộp (Tuần 10)

- [ ] Không còn `\wip{}` / `\ph{}` nào (`grep -rn 'wip\|\\ph{' chapters frontmatter appendices`).
- [ ] Mọi hình/bảng được nhắc trong prose (`Hình~\ref{}`, `Bảng~\ref{}`).
- [ ] Mọi `\autocite` khớp key trong `refs.bib`; không còn `[?]`.
- [ ] Tóm tắt + Từ khóa + Lời cảm ơn hoàn tất.
- [ ] Đồng bộ `refs.bib` từ `research/refs.bib` (bản superset).
- [ ] Biên dịch sạch (không undefined reference/citation).
