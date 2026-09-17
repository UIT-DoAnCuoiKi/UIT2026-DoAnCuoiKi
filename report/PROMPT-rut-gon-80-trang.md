# PROMPT: Rút gọn báo cáo ĐATN còn khoảng 80 trang (cô đọng, khoa học)

Dán nguyên khối này vào một session Claude Code mới, chạy tại thư mục gốc repo.
Mục tiêu của phiên: **rút gọn toàn báo cáo trong `report/` xuống khoảng 80 trang**, giữ lại
những luận điểm quan trọng nhất, cắt hết phần lê thê, lặp lại và diễn giải không làm tăng
thông tin. Làm **từng chương một**, không sửa hàng loạt trong một lượt.

---

## 0. Bắt đầu phiên (bắt buộc)

1. Kích hoạt skill `thesis-writer` và skill `academic-editing` trước khi viết. Hai skill này
   quy định văn phong học thuật tiếng Việt, quy tắc thuật ngữ, và quy trình biên tập một mục
   một lượt (có bản trước/sau, không ghi đè âm thầm).
2. Đọc `report/PROMPT-viet-lai-bao-cao.md`. File đó là **nguồn chân lý** cho:
   - Mục 2: các sự thật đã chốt (số liệu không được đổi).
   - Mục 3: danh sách hình dùng lại và quy tắc hình.
   - Mục 4 và 5: quy tắc bảng biểu và đánh số mục.
   - Mục 8: những thứ giữ nguyên (mAP dedup 0,983, màu 2/4, Ch2 đầy hơn bản Nhật...).
   Prompt này **không lặp lại** các mục đó. Khi cần số liệu hay tên hình, tra ở đó và ở file
   nguồn `src/ml/experiments/`, không nhớ theo trí nhớ.
3. Nguyên tắc bất di bất dịch: chỉ báo cáo số liệu THẬT đã kiểm chứng; chỗ chưa có dữ liệu để
   `\wip{...}`/`\ph{...}`, không đoán; không tự `git commit`/`git push`.

---

## 1. Mục tiêu độ dài và ngân sách trang

Hiện trạng: thân bài khoảng 37.700 từ (đo trên `report/main.docx`), phần chữ dài hơn mức cần
cho một báo cáo khoa học. Đích: **tổng quyển khoảng 80 trang** (cổng `report/check.py` cho phép
thân bài 50 đến 100 trang; 80 nằm giữa, có biên an toàn).

Ngân sách phân bổ (trang là ước lượng sau khi dựng; **số từ** là mốc đo trực tiếp trong lúc
viết, tính trên nội dung `.tex` gồm cả macro):

| Phần | Trang mục tiêu | Trần số từ (.tex) | Hiện tại |
|---|---|---|---|
| Front matter (bìa, lời cảm ơn, mục lục, danh mục hình/bảng, viết tắt) | ~9 | giữ nguyên | |
| Tóm tắt | 1 | 250 từ prose | 431 |
| Ch1 Giới thiệu | 5 | 2200 | 2830 |
| Ch2 Liên quan | 7 | 3600 | 4284 |
| Ch3 Dữ liệu | 7 | 3200 | 4364 |
| Ch4 Phát hiện | 5 | 2200 | 2697 |
| Ch5 OCR và màu biển | 8 | 3800 | 5770 |
| Ch6 Phân loại | 7 | 3300 | 4518 |
| Ch7 Hệ thống | 9 | 3000 | 3359 |
| Ch8 Triển khai và đánh giá | 7 | 3200 | 4370 |
| Ch9 Kết luận | 3 | 1500 | 2276 |
| Tài liệu tham khảo | ~3 | giữ nguyên | |
| Phụ lục A, B, C | ~6 | giữ nguyên | |

Tổng thân bài mục tiêu khoảng 26.000 từ (giảm khoảng 24% so với hiện tại). Trần số từ là
**mức trần, không phải hạn ngạch phải lấp**: nếu diễn đạt đủ ý mà ngắn hơn thì để ngắn, không
thêm chữ cho đủ trang.

---

## 2. Nguyên tắc cô đọng (áp dụng cho mọi chương)

Rút gọn ở đây nghĩa là **bỏ chữ mà không bỏ thông tin**. Bốn thao tác chính:

1. **Cắt phần thừa, không cắt bằng chứng.** Bỏ câu đệm, câu chuyển ý sáo rỗng ("có thể thấy
   rằng", "đáng chú ý là", "như đã đề cập"), phần nhắc lại bối cảnh đã nêu ở chương trước, và
   mọi đoạn diễn giải lại điều bảng/hình đã nói. Giữ nguyên số liệu, luận điểm, và mọi câu mang
   dữ kiện mới.
2. **Gộp diễn giải dài thành bảng hoặc câu ngắn.** Nếu một đoạn liệt kê từ 4 mục trở lên có cấu
   trúc giống nhau (mô tả các bộ dữ liệu, các cấu hình, các lớp), chuyển thành một bảng và giữ
   lại một câu nhận xét. Một ý dài ba câu mà chỉ có một dữ kiện thì viết lại thành một câu.
3. **Mỗi khái niệm giải thích đúng một lần.** Lý thuyết mô hình (YOLO, CRNN, ResNet,
   MobileNet) trình bày một chỗ; các chương sau chỉ tham chiếu bằng `Chương~\ref{}` hoặc
   `Mục~\ref{}`. Xóa mọi định nghĩa và mô tả kiến trúc bị lặp giữa các chương.
4. **Trực diện.** Mỗi mục mở bằng một câu nêu vấn đề hoặc kết luận, rồi mới tới bằng chứng. Cấu
   trúc ngầm cho mỗi tiểu mục: vấn đề, cách giải quyết, kết quả hoặc nhận xét. Câu dài quá 35 từ
   thì tách. Thay định lượng mơ hồ ("nhiều", "một số", "khá cao") bằng con số cụ thể từ dữ liệu.

Văn phong: tiếng Việt học thuật, ngôi thứ ba, không "em/tôi/nhóm em". Giữ thuật ngữ tiếng Anh
chuẩn (mAP, OCR, pipeline, inference, quantization). Số thập phân dùng dấu phẩy. Không dùng gạch
dài en/em hay `--`/`---` trong văn xuôi; dùng "từ X đến Y" cho khoảng, giữ hyphen chỉ trong mã
có nghĩa (end-to-end, F1-macro, MobileNetV3-Small, TT-BCA).

---

## 3. Tiêu chí chọn lọc: giữ gì, cắt gì

Với mỗi đoạn, hỏi: **đoạn này thêm dữ kiện, số liệu, hay luận điểm mới không?** Nếu không, cắt.

**Giữ** (cốt lõi khoa học):
- Phát biểu vấn đề, câu hỏi nghiên cứu, mục tiêu, phạm vi, đóng góp.
- Mọi con số có nguồn và câu nhận xét rút ra từ nó.
- Lý do chọn phương pháp hoặc mô hình (một lần, ngắn gọn) và đánh đổi kèm theo.
- Bảng kết quả, ma trận nhầm lẫn, hình EDA và hình kết quả thật.
- Giới hạn đã biết và cách xử lý (dedup train/test, màu mới 2/4, chưa thu ảnh bãi thật, INT8
  chưa làm).

**Cắt** (không làm tăng thông tin):
- Nhắc lại bối cảnh và động cơ đã nêu ở Chương 1.
- Lý thuyết mô hình chép từ tài liệu, không gắn với quyết định thiết kế của đồ án.
- Đoạn văn diễn giải lại nội dung bảng hoặc hình liền kề.
- Liệt kê ưu nhược điểm chung chung không dẫn tới lựa chọn cụ thể.
- Câu hứa hẹn, câu dẫn dắt, câu tổng kết lặp ở đầu và cuối mỗi mục.

---

## 4. Trọng tâm cắt gọn từng chương

Bảng dưới bổ sung cho Mục 6 của `PROMPT-viet-lai-bao-cao.md`, nhấn vào việc **rút xuống ngân
sách trang** ở Mục 1.

| Chương | Giữ | Cắt mạnh |
|---|---|---|
| 01 Giới thiệu | 4 câu hỏi NC, mục tiêu, phạm vi, tiêu chí, đóng góp; hình `pipeline-example`. | Bối cảnh ngành lặp; đoạn động cơ dài; mô tả sơ bộ phương pháp (để dành cho chương chuyên). |
| 02 Liên quan | Bảng so sánh, luận điểm sai số cộng dồn, kết quả theo điều kiện. **Đã đầy hơn bản Nhật, không thêm.** | Câu dài; đoạn tóm tắt từng công trình quá chi tiết, rút còn một câu điểm khác biệt. |
| 03 Dữ liệu | 4 hình EDA; nêu rõ dedup 230 cặp và chưa tự thu ảnh bãi thật. | Gộp mô tả từng bộ dữ liệu vào một bảng; bỏ mô tả quy trình gán nhãn dài dòng. |
| 04 Phát hiện | Bảng 3 seed; nhấn mAP 0,983 (dedup) và lý do chọn YOLOv8n. | Lý thuyết YOLO (đã ở Ch2); diễn giải lại đường cong huấn luyện. |
| 05 OCR và màu | Bảng 3 tập (a1, vn_plate, topkek), bảng ablation, so baseline; màu nêu rõ 2/4. **Chương verbose nhất, cắt nhiều nhất.** | Mô tả CRNN dài; đoạn phân tích từng lỗi lặp ý; diễn giải lại các hình mẫu dự đoán. |
| 06 Phân loại | Bảng loại xe và kiểu dáng; ma trận nhầm lẫn; bài học học tắt theo nguồn ảnh. | Diễn giải dài về từng lớp; lặp mô tả kiến trúc ResNet/MobileNet. |
| 07 Hệ thống | Kiến trúc 2 đường, bảng vai trò/quyền, bảng 2 cấu hình, ER, 6 ảnh dashboard, logic vào/ra, tính phí, bảo mật. | Prose bám mã, câu ngắn; bỏ mô tả lại nội dung sơ đồ UML bằng lời. |
| 08 Triển khai | Bảng độ trễ Pi (model riêng, toàn pipeline, e2e API), PC với Pi, công suất/nhiệt, so công trình liên quan. | **Bỏ hẳn INT8 khỏi thân bài** (chỉ nêu ở hướng phát triển); bỏ diễn giải lại từng ô số của bảng độ trễ. |
| 09 Kết luận | Trả lời 4 câu hỏi NC, bảng đối chiếu mục tiêu, giới hạn, hướng phát triển (gồm INT8). | Không lặp lại số đã nêu ở Ch8; bỏ đoạn tóm tắt lại toàn bộ báo cáo. |

---

## 5. Quy trình cho mỗi chương

1. Đọc file `.tex` của chương và file nguồn số liệu liên quan.
2. Đối chiếu mọi con số với Mục 2 của `PROMPT-viet-lai-bao-cao.md`; sửa số sai, xóa số không
   nguồn.
3. Biên tập theo Mục 2 và Mục 3 trên: cắt phần thừa, gộp liệt kê thành bảng, viết lại trực diện.
   Bám trần số từ ở Mục 1. Với mỗi mục lớn, dùng chế độ biên tập của skill `academic-editing`
   (nêu vấn đề phát hiện, bản sửa, giải thích) để tự kiểm trước khi ghi đè.
4. Bảo đảm mọi hình và bảng còn lại được nhắc trong văn bằng `Hình~\ref`/`Bảng~\ref`, có
   `\caption` đánh số và dòng nguồn. Không đổi `\label` đang được `\ref` ở chương khác; nếu buộc
   phải đổi thì sửa luôn nơi tham chiếu.
5. Đo lại số từ chương: `wc -w report/chapters/<file>.tex`, so với trần ở Mục 1.
6. Chạy `python3 report/check.py` phải PASS (chỉ chấp nhận R1 với các marker chủ đích còn lại).
7. Dựng `bash report/build.sh`, mở `report/main.docx` kiểm bảng có viền, hình đủ caption, mục
   đánh số đủ, và ước lượng tổng số trang tiến về 80.
8. Không `git commit`/`git push`; để thay đổi ở trạng thái chưa commit.

---

## 6. Không được làm

- Không cắt số liệu, giới hạn, hay câu mang dữ kiện để lấy độ ngắn. Rút gọn là bỏ chữ thừa,
  không bỏ thông tin.
- Không đổi các sự thật đã chốt ở Mục 2 của `PROMPT-viet-lai-bao-cao.md` (mAP dedup 0,983, OCR
  a1 91,9%, loại xe 98,66% ResNet18, kiểu dáng 90,07% MobileNetV3-Small, e2e Pi 0,464 s, INT8
  chưa làm, màu 2/4).
- Không thêm số liệu, trích dẫn, hay khái niệm mới vào Tóm tắt và Kết luận.
- Không thêm hình chỉ để lấp trang; mỗi hình phải thêm thông tin.
- Không đoán để điền chỗ trống; giữ `\wip`/`\ph` nếu chưa có dữ liệu thật.
- Không tự commit hay push.
