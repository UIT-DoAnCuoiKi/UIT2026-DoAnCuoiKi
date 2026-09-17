# Prompt tiếp tục: hoàn thiện báo cáo (output DOCX)

Dán nguyên khối dưới đây vào một session Claude Code mới (chạy tại thư mục gốc repo).

---

Mục tiêu duy nhất của phiên này: **hoàn thiện báo cáo LaTeX trong `report/` cho thật tốt**.
Đây là đồ án tốt nghiệp UIT về hệ thống bãi giữ xe thông minh.

**Định dạng xuất là DOCX**, không phải PDF. Dựng bằng `bash report/build.sh` (dùng pandoc +
`postprocess.py` sinh `report/main.docx`). KHÔNG cần cài latexmk/biber, KHÔNG cần build PDF;
stage PDF trong `build.sh` tự bỏ qua khi thiếu toolchain, coi đó là bình thường.

**Quy tắc (không được vi phạm):**
- Chỉ báo cáo số liệu THẬT, đã kiểm chứng từ file nguồn. Chỗ chưa có dữ liệu để `\wip{...}`
  hoặc `\ph{...}` (dấu đỏ trung thực), tuyệt đối không đoán.
- Không dùng gạch ngang dài (en/em dash) hay `--`/`---` trong văn xuôi; dùng "từ X đến Y"
  cho khoảng. Chỉ giữ hyphen trong thuật ngữ chuẩn (end-to-end, F1-macro, MobileNetV3-Small).
- Văn phong học thuật tiếng Việt, ngôi thứ ba. Mọi `\caption` phải có dòng `Nguồn:`.
- KHÔNG tự `git commit`/`git push` khi chưa được yêu cầu rõ. Chỉ `git add`.
- Sau mỗi thay đổi: chạy `python3 report/check.py` (mọi cổng phải OK trừ R1 các marker chủ
  đích còn lại) rồi `bash report/build.sh`; kiểm tra nội dung mới có trong `report/main.docx`
  (ví dụ: `pandoc report/main.docx -t plain | grep <số cần kiểm>`).

## Việc chính, theo thứ tự ưu tiên

### 1. Rà soát chất lượng toàn báo cáo (làm trước)
Đọc lần lượt `report/chapters/01`..`09` và `report/frontmatter/`:
- Mọi `\ref{}` phải trỏ đúng; mọi hình/bảng phải được nhắc trong văn (`Hình~\ref`, `Bảng~\ref`).
- Thuật ngữ và số liệu nhất quán giữa các chương (đặc biệt: kiểu dáng triển khai =
  MobileNetV3-Small; loại xe = ResNet18; độ trễ Pi 0,464 s; PC 260,2 ms).
- Mạch lập luận trôi chảy, không lặp, không mâu thuẫn giữa các chương.
- Kiểm tra bản DOCX render đúng: tiêu đề chương IN HOA, mục tài liệu tham khảo chia nhóm
  tiếng Việt/tiếng Anh, bảng không tràn lề.

### 2. Ảnh chụp dashboard (Chương 7)
Marker: `report/chapters/07-hethong.tex`, tìm `\wip{cần ảnh chụp dashboard}`.
- Dựng frontend React (`src/frontend`, Vite cổng 5173) + backend FastAPI (`src/backend`,
  có `.venv`) + PostgreSQL, chạy trực tiếp trên host (container macOS lỗi EINTR libkrun).
  Dashboard KHÔNG cần suy luận ML; seed vài phiên mẫu vào DB để có dữ liệu hiển thị.
- Chụp: Trạm cổng (`features/gate`), Tra cứu phiên + chi tiết phiên (`features/sessions`),
  Thống kê + biểu đồ + nút xuất CSV (`features/stats`). Có thể dùng Claude in Chrome mở
  `localhost:5173` để chụp.
- Lưu ảnh vào `report/figures/` (vd `dashboard-gate.png`, `dashboard-sessions.png`,
  `dashboard-stats.png`). Thay `\wip` bằng các `\begin{figure}` `\includegraphics` +
  `\caption` + dòng `{\footnotesize Nguồn: ảnh chụp giao diện hệ thống ...}`, nhắc bằng
  `Hình~\ref` trong văn.

### 3. Tóm tắt (abstract) và các ô người dùng
- `report/frontmatter/abstract.tex`: viết tóm tắt cuối 200 đến 300 từ, thay `\wip`/`\ph`.
  Số THẬT để điền (KHÔNG overclaim, đừng ghi ">90%"):
  - Phát hiện biển mAP@0,5 = 0,983; OCR vn_plate 80,2% / topkek 56,6%.
  - Loại xe 98,66% (ResNet18); kiểu dáng 90,07% (MobileNetV3-Small).
  - Độ trễ đầu-cuối trên Raspberry Pi 5: trung vị 0,464 s/lượt xe, dưới 2 s.
- `report/frontmatter/titlepage.tex`: điền ô "[điền ngành]".
- `report/refs.bib`: thêm số hiệu chính xác Luật Bảo vệ dữ liệu cá nhân cho khóa
  `vn2025lutbvdlcn` (đã bỏ "63/2025/QH15" vì chưa chắc; kiểm chứng số hiệu và ngày ban
  hành trước khi thêm, nếu không chắc thì để nguyên trạng thái hiện tại).

## Dấu đỏ còn lại cần dữ liệu, để nguyên (không đoán)
- `report/chapters/08-trienkhai.tex`: accuracy màu nền biển (`\ph{Chưa có tập test có nhãn
  màu}`). Cần ~200 crop biển cân bằng 4 màu gán nhãn tay (xem
  `src/ml/plate_color_pipeline/notebooks/validate-plate-color.ipynb` mục 5). Chỉ điền khi
  có nhãn thật.
- Accuracy đọc biển đúng toàn luồng đối chiếu ground truth và tỉ lệ vào ra khớp: cần tập
  ảnh cổng toàn cảnh có nhãn text. Hiện đã có độ trễ và kiểm chứng khớp dev/Pi 50/50.

## Đã hoàn thành (tham chiếu, không làm lại)
- Ch6: model loại xe tự huấn luyện 98,66%, test OOD, lỗi pipeline 57% và cách sửa.
- Ch7: độ trễ PC 260,2 ms; pipeline 4 model.
- Ch8: đo Raspberry Pi 5 thật (từng model, toàn pipeline, công suất, nhiệt độ, RAM),
  so sánh PC với Pi, end-to-end qua API 0,464 s/lượt; model kiểu dáng chuyển sang
  MobileNetV3-Small. Cổng `check.py` chỉ còn R1 với marker màu biển (Ch8), dashboard (Ch7),
  abstract (frontmatter).
