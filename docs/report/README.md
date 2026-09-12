# Report: báo cáo đồ án

**Nguồn duy nhất của báo cáo là `report/` (LaTeX).** Xuất PDF bằng XeLaTeX và DOCX bằng pandoc, cả hai qua `report/build.sh`. Cổng kiểm tra: `python3 report/check.py`. Kế hoạch, sườn chương và rule viết: `report/PLAN.md`.

Thư mục `chapters/*.md` trong đây là **bản thảo lịch sử đã đóng băng** từ ngày 09/09/2026, giữ để tra cứu. Không sửa nữa; mọi thay đổi nội dung diễn ra trong `report/chapters/*.tex`.

Thư mục `figures/` giữ figure bản cũ. Figure dùng trong báo cáo được sinh lại bằng `src/ml/figstyle.py` và ghi thẳng sang `report/figures/` dưới hai định dạng `.pdf` và `.png`.

`tuan-*.md` là báo cáo tiến độ theo tuần, giữ nguyên làm mốc lịch sử. **Không chép số liệu từ đó vào báo cáo**: một số chỗ đã được xác minh là sai so với code. Danh sách sai lệch nằm ở mục "Sự thật đã kiểm chứng từ code" trong `report/PLAN.md`.
