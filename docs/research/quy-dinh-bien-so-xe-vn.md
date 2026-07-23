# Quy định biển số xe Việt Nam — bố cục, kích thước, ký tự, màu biển

> W1 research — @Nhật. Tổng hợp phục vụ thiết kế nhãn (labels) cho module phát hiện/OCR biển số và phân loại màu biển của đề tài. Không phải văn bản pháp lý chính thức — khi cần trích dẫn chính xác cho báo cáo, đối chiếu lại văn bản gốc theo link ở mục Nguồn.

## 1. Căn cứ pháp lý hiện hành

Kể từ **01/01/2025**, bộ quy định biển số xe cơ giới tại Việt Nam được điều chỉnh bởi:

| Văn bản | Nội dung | Thay thế | Nguồn |
|---|---|---|---|
| **Luật Trật tự, an toàn giao thông đường bộ 2024** (QH thông qua 27/06/2024, hiệu lực 01/01/2025) | Đưa quy định màu biển số vào luật (trước đây chỉ ở thông tư) | — | [Nhận biết biển số xe theo màu sắc từ 01/01/2025](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/67844/nhan-biet-bien-so-xe-theo-mau-sac-tu-01-01-2025) |
| **Thông tư 79/2024/TT-BCA** (Bộ Công an) | Cấp, thu hồi chứng nhận đăng ký xe, biển số xe cơ giới/xe máy chuyên dùng; seri, số lượng ký tự, phụ lục 02/03/04 quy định seri & kích thước chữ/số theo từng loại xe | Thông tư 58/2020/TT-BCA, Thông tư 24/2023/TT-BCA | [Quy định về biển số xe từ 01/01/2025 theo TT 79/2024](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/76322/quy-dinh-ve-bien-so-xe-tu-ngay-01-01-2025-theo-thong-tu-79-2024) |
| **Thông tư 81/2024/TT-BCA** — ban hành **QCVN 08:2024/BCA** | Quy chuẩn kỹ thuật quốc gia về biển số xe: kích thước biển, chất liệu, phông chữ, độ phản quang | Quy chuẩn cũ trong TT 58/2020 | [Quy chuẩn kỹ thuật quốc gia về biển số xe (baochinhphu.vn)](https://baochinhphu.vn/quy-chuan-ky-thuat-quoc-gia-ve-bien-so-xe-102241209094144236.htm) |
| **Thông tư 51/2025/TT-BCA** | Điều chỉnh mã biển số theo địa giới hành chính mới (sáp nhập tỉnh 01/07/2025) | — | [Sáp nhập tỉnh, biển số xe thay đổi ra sao? (danviet.vn)](https://danviet.vn/sap-nhap-tinh-thanh-pho-tu-ngay-1-7-2025-dang-ky-xe-va-bien-so-xe-thay-doi-ra-sao-d1340325.html) |

Biển số quản lý theo **mã số định danh cá nhân/tổ chức** của chủ xe (từ [Thông tư 24/2023/TT-BCA](https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/Thong-tu-24-2023-TT-BCA-cap-thu-hoi-dang-ky-bien-so-xe-co-gioi-559088.aspx), tiếp tục áp dụng), không phải theo xe — khi sang tên, biển số không đổi mà giữ theo chủ mới đăng ký lần đầu hoặc trả lại kho biển ([điểm mới của TT 24/2023](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/iThong/51005/diem-moi-thong-tu-24-2023-tt-bca-ve-dang-ky-xe-va-cap-bien-so-xe)).

## 2. Cấu trúc chuỗi ký tự trên biển số

Định dạng chung: **`[Mã tỉnh 2 số]-[Seri 1 chữ cái (+ 1 số nếu hết seri)] [Số thứ tự 5 chữ số, nhóm 3.2]`**

Ví dụ: `30A-123.45`, `51F-678.90`, biển mô tô nhiều seri có thể có dạng `59-P1 234.56` (thêm số vào seri khi một chữ cái không đủ dung lượng cấp — phổ biến ở các tỉnh/thành đông xe máy).

- **Mã tỉnh**: 2 chữ số (11–99), gắn với địa phương đăng ký xe ([bảng mã 63 tỉnh, thành trước sáp nhập](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/tu-van-phap-luat/29523/ky-hieu-bien-so-xe-o-to-xe-may-cua-cac-tinh-thanh-trong-nuoc); xem mục 6 — mã tỉnh **không đổi** sau sáp nhập hành chính 2025 với xe đã đăng ký trước đó).
- **Seri đăng ký**: chọn trong tập **20 chữ cái**: `A B C D E F G H K L M N P S T U V X Y Z`.
  Các chữ **I, J, O, Q, R, W** **không** dùng cho biển dân sự (dễ nhầm với số 0/1, hoặc dành riêng cho biển sơ-mi rơ-moóc/rơ-moóc). → hữu ích để ràng buộc bộ ký tự hợp lệ khi hậu xử lý kết quả OCR (loại bỏ nhầm lẫn O/0, I/1).
- **Số thứ tự**: 5 chữ số tự nhiên, hiển thị nhóm `xxx.xx`, từ `000.01` đến `999.99`.
- [Từ 2025, biển ô tô không còn phân biệt chữ cái theo loại xe](https://kienthuc.net.vn/bo-phan-biet-chu-cai-tren-bien-so-oto-tu-nam-2025-post1043088.html) như quy ước cũ (vd. seri A dành cho xe 7–9 chỗ, B cho xe kinh doanh vận tải, C cho xe tải…) — chữ cái nay cấp ngẫu nhiên. Riêng các ký hiệu đặc biệt như **LD, DA** (không thuộc seri thường) vẫn giữ nguyên, không bị gộp vào quy định cấp ngẫu nhiên này. Ảnh cũ trong dataset có thể còn theo quy ước trước 2025 — cần lưu ý khi gắn nhãn nếu có ý định suy ra loại xe từ chữ cái trên biển (không nằm trong scope hiện tại của đề tài).

## 3. Số lượng biển & quy định gắn biển theo loại xe

Điểm dễ hiểu nhầm nhất khi thiết kế dữ liệu: **"biển dài 1 dòng" và "biển ngắn 2 dòng" không phải là hai kiểu biển thay thế nhau giữa các xe** — với ô tô, đây là **hai biển bắt buộc phải gắn đồng thời trên cùng một xe**.

| Loại xe | Số biển | Bố cục từng biển | Kích thước (D × C, mm) | Vị trí gắn | Nguồn |
|---|---|---|---|---|---|
| Ô tô (con, tải, khách…) và xe máy chuyên dùng | **2 biển**: 1 biển dài + 1 biển ngắn (không được gắn 2 biển cùng kích thước, trừ trường hợp xe không lắp được biển kết hợp thì đổi đồng bộ sang 2 dài hoặc 2 ngắn) | Biển dài: **1 dòng** (mã tỉnh-seri + số thứ tự trên cùng hàng). Biển ngắn: **2 dòng** (dòng 1 = mã tỉnh-seri, dòng 2 = số thứ tự) | Dài: 520 × 110 · Ngắn: 330 × 165 | Luật không bắt buộc thứ tự trước/sau — tuỳ thiết kế xe, nhưng thực tế phổ biến là **biển dài gắn trước, biển ngắn gắn sau** | [Bộ Công an đề xuất ô tô lắp 2 biển số 1 dài 1 ngắn (thanhnien.vn)](https://thanhnien.vn/bo-cong-an-de-xuat-o-to-duoc-lap-2-bien-so-gom-1-dai-1-ngan-185230318123353455.htm) · [Kích thước biển số xe mới nhất](https://luatgia.com.vn/kich-thuoc-bien-so-xe-moi-nhat-tu-01-01-2025/) |
| Mô tô, xe gắn máy (kể cả xe máy điện) | **1 biển** (chỉ gắn phía sau) | Luôn **2 dòng**: dòng 1 = mã tỉnh + seri, dòng 2 = số thứ tự | 190 × 140 | Phía sau xe | [Kích thước biển số xe mới nhất](https://luatgia.com.vn/kich-thuoc-bien-so-xe-moi-nhat-tu-01-01-2025/) |
| Máy kéo, rơ-moóc, sơ-mi rơ-moóc | **1 biển** (chỉ gắn phía sau) | **2 dòng**, cùng bố cục với biển ngắn của ô tô | 330 × 165 | Phía sau xe | [Kích thước biển số sơ mi rơ moóc](https://thuvienphapluat.vn/hoi-dap-phap-luat/kich-thuoc-bien-so-xe-so-mi-ro-mooc-la-bao-nhieu-138080998.html) |

Hệ quả quan trọng cho pipeline detection/OCR:
- **Với một chiếc ô tô, camera có thể "thấy" 1 trong 2 bố cục khác nhau tuỳ góc chụp** (camera đầu bãi thấy biển dài 1 dòng, camera cuối bãi thấy biển ngắn 2 dòng của **cùng một xe**) — không phải do 2 loại xe khác nhau. Dữ liệu huấn luyện/test cần cân bằng cả hai bố cục, và nếu hệ thống ghi nhận cả ảnh đầu lẫn đuôi xe thì có thể dùng 2 kết quả OCR để đối chiếu chéo (cross-check), tăng độ tin cậy.
- Biển mô tô và biển rơ-moóc/sơ-mi rơ-moóc/máy kéo **cùng kích thước và bố cục 2 dòng** (330×165 hoặc 190×140, khác nhau về kích thước tuyệt đối nhưng cùng tỉ lệ 2 dòng) — nếu đề tài từng gặp nhầm giữa biển ngắn ô tô, biển rơ-moóc và biển mô tô trong dữ liệu, đây là lý do: cả ba đều theo cùng một bố cục 2 dòng, chỉ khác kích thước và (với ô tô/rơ-moóc) khác việc có "biển thứ hai" đi kèm hay không.
- Do luật cho phép đổi đồng bộ sang 2 biển dài hoặc 2 biển ngắn nếu xe không lắp được biển kết hợp, thực tế đường phố vẫn có một tỷ lệ nhỏ ô tô gắn 2 biển cùng kích thước — không phải lỗi gán nhãn nếu dữ liệu thu thập gặp trường hợp này.

## 4. Chất liệu, kích thước ký tự & đặc điểm bảo mật vật lý

Theo [QCVN 08:2024/BCA](https://luatvietnam.vn/giao-thong/quy-chuan-ky-thuat-quoc-gia-qcvn-08-2024-bca-bien-so-xe-378478-d3.html) (ban hành kèm TT 81/2024/TT-BCA):

- **Chất liệu nền:** hợp kim nhôm tấm, mác **A1100H14** theo TCVN 13065:2020, chiều dày **(1 ± 0,05) mm**.
- **Màng phản quang:** dán lên tấm nhôm, không có vết rỗ khí; có hoa văn bảo mật dạng **đường vân** và dòng chữ **"CSGT"/"TRAFFIC POLICE"** chỉ hiện rõ khi nhìn nghiêng ở góc khoảng 30° — đây là đặc điểm chống làm giả, không phải lỗi in ấn nếu ảnh chụp thấy biển có vệt sáng bất thường ở một số góc.
- **Chữ, số, ký hiệu:** được **dập nổi** trên bề mặt biển, chiều cao phần dập nổi **(1,7 ± 0,1) mm**; có ký hiệu bảo mật hình Công an hiệu đóng chìm rõ nét.
- **Khoảng cách ký tự:** trên biển ô tô, khoảng cách giữa các chữ/số liền kề là **10 mm** (riêng số "1" có khoảng cách khác do bề rộng nét mảnh hơn: 19 mm với ký tự liền kề, 28 mm giữa hai số "1"); trên biển mô tô, khoảng cách dòng trên là **5 mm**, dòng dưới là **10 mm**. Kích thước chi tiết từng chữ/số nằm trong phụ lục bản vẽ kỹ thuật của quy chuẩn, không thấy công bố dưới dạng bảng tóm tắt.
- **4 góc biển đều bo tròn** theo khuôn mẫu quy định (Hình 1, Hình 2 của quy chuẩn).
- **Màu sắc chuẩn hoá theo toạ độ màu CIE** (bảng hệ số phản quang ngày/đêm riêng cho từng màu nền) — nghĩa là màu biển trong quy chuẩn được định nghĩa chặt hơn nhiều so với tên gọi thông thường ("trắng", "vàng", "xanh dương", "đỏ"); ảnh chụp thực tế dưới các điều kiện ánh sáng khác nhau (đèn flash hồng ngoại ban đêm, ánh nắng trực tiếp) có thể lệch tông màu đáng kể so với màu chuẩn, cần lưu ý khi gán nhãn màu biển từ ảnh thay vì suy từ tên loại xe.

Hai điểm đáng chú ý cho bài toán thị giác máy tính của đề tài:
- **Chữ dập nổi + màng phản quang** khiến biển số phản chiếu ánh sáng đèn flash/đèn pha rất mạnh vào ban đêm (hiện tượng loá sáng — glare), một trong những nguyên nhân chính khiến OCR biển số thất bại về đêm; đây không phải là đặc thù chỉ riêng biển Việt Nam nhưng đáng ghi chú vì ảnh hưởng trực tiếp tới góc quay camera bãi xe.
- Riêng [Hà Nội đang thí điểm](https://antv.gov.vn/kinh-te-5/ha-noi-dinh-danh-xe-dien-bang-mau-bien-so-va-ma-qr-04A9A9B8F.html) gắn thêm **mã QR** lên biển số xe sử dụng năng lượng sạch, tích hợp với hệ thống thu phí không dừng (ETC) — đây là **chương trình thí điểm của địa phương**, chưa phải quy định bắt buộc áp dụng toàn quốc theo QCVN 08:2024/BCA, nên không đưa vào giả định mặc định khi thiết kế hệ thống, trừ khi phạm vi triển khai của đề tài giới hạn ở Hà Nội.

## 5. Bảng quy chiếu màu biển (áp dụng cho phân loại màu biển của đề tài)

| Màu nền — màu chữ/số | Đối tượng cấp | Ưu tiên trong đề tài | Nguồn |
|---|---|---|---|
| **Trắng — chữ/số đen** | Cá nhân, tổ chức trong nước không thuộc các nhóm dưới (biển phổ biến nhất) | **Bắt buộc** | [Nhận biết biển số xe theo màu sắc từ 01/01/2025](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/67844/nhan-biet-bien-so-xe-theo-mau-sac-tu-01-01-2025) |
| **Vàng — chữ/số đen** | Xe kinh doanh vận tải (taxi, xe công nghệ, xe khách, xe tải kinh doanh…) | **Bắt buộc** | [Nhận biết biển số xe theo màu sắc từ 01/01/2025](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/67844/nhan-biet-bien-so-xe-theo-mau-sac-tu-01-01-2025) |
| **Xanh dương — chữ/số trắng** | Cơ quan Đảng, Nhà nước, tổ chức chính trị - xã hội, đơn vị sự nghiệp công lập, Công an nhân dân | Tuỳ chọn | [Nhận biết biển số xe theo màu sắc từ 01/01/2025](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/67844/nhan-biet-bien-so-xe-theo-mau-sac-tu-01-01-2025) |
| **Đỏ — chữ/số trắng** | Xe quân sự (Quốc phòng) | Tuỳ chọn | [Nhận biết biển số xe theo màu sắc từ 01/01/2025](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/67844/nhan-biet-bien-so-xe-theo-mau-sac-tu-01-01-2025) |
| Trắng — chữ đỏ, số đen, ký hiệu **"NG"** | Cơ quan đại diện ngoại giao, lãnh sự, nhân viên mang chứng minh thư ngoại giao | Ngoài phạm vi (hiếm gặp ở bãi xe dân sự) | [Nhận diện màu sắc, seri, ký hiệu biển số xe (Bộ Công an)](https://bocongan.gov.vn/chinh-sach-phap-luat/bai-viet/nhan-dien-mau-sac-seri-ky-hieu-bien-so-xe-cua-co-quan-to-chuc-ca-nhan-tu-01012025-d1-t1617) |
| Trắng — chữ đỏ, số đen, ký hiệu **"QT"** | Cơ quan đại diện tổ chức quốc tế | Ngoài phạm vi | [Nhận diện màu sắc, seri, ký hiệu biển số xe (Bộ Công an)](https://bocongan.gov.vn/chinh-sach-phap-luat/bai-viet/nhan-dien-mau-sac-seri-ky-hieu-bien-so-xe-cua-co-quan-to-chuc-ca-nhan-tu-01012025-d1-t1617) |

**Lưu ý quan trọng — dễ hiểu nhầm:** xe điện/xe dùng năng lượng sạch **không có màu biển riêng**. Biển vẫn theo màu của nhóm chủ sở hữu (trắng/vàng/xanh…) như bảng trên, chỉ được dán thêm **một tem nhận diện màu xanh lá cây** trên biển số. Nếu dataset/ảnh thu thập có tem xanh lá, đó là dấu hiệu "xe năng lượng sạch", **không** phải nhãn màu biển thứ 5 — tránh nhầm lẫn khi gán nhãn.

Việc ưu tiên trắng/vàng bắt buộc, xanh/đỏ tuỳ chọn (đã chốt trong [phân công tuần 1](../task/tuan-01.md)) khớp với thực tế: hai màu này chiếm tuyệt đại đa số xe cá nhân và xe kinh doanh vận tải tại bãi giữ xe dân sự — nguồn dữ liệu thu thập thực tế nhiều khả năng sẽ khan hiếm mẫu xanh dương/đỏ, cần lưu ý khi đánh giá accuracy (imbalance).

## 6. Ảnh hưởng của sáp nhập tỉnh (01/07/2025) đến mã tỉnh trên biển số

Từ 01/07/2025, Việt Nam sáp nhập đơn vị hành chính cấp tỉnh **từ 63 xuống còn 34 tỉnh/thành phố** (Thông tư 51/2025/TT-BCA quy định mã biển số mới theo địa giới mới). Điểm cần lưu ý cho hệ thống:

- **Xe đăng ký trước 01/07/2025 giữ nguyên biển số/mã tỉnh cũ** — không bắt buộc đổi biển.
- **Xe đăng ký mới sau 01/07/2025** dùng mã biển số **gộp** từ các tỉnh đã hợp nhất (một tỉnh mới có thể cấp mới dưới nhiều mã cũ của các tỉnh cấu thành).
- Hệ quả: bảng tra cứu "mã tỉnh → tên tỉnh" **không còn là ánh xạ 1-1 cố định** như trước — cùng một tỉnh/thành sau sáp nhập có thể có nhiều mã tỉnh hợp lệ đang lưu hành song song trên đường trong nhiều năm tới. Nếu đề tài có tính năng suy ra "tỉnh đăng ký" từ biển số (không nằm trong scope hiện tại), cần dùng bảng ánh xạ theo **nhóm mã → tỉnh mới**, cập nhật theo TT 51/2025/TT-BCA, thay vì bảng 63 tỉnh cũ.
- Không ảnh hưởng tới bài toán OCR/phân loại màu biển cốt lõi của đề tài (chuỗi ký tự và màu vẫn theo đúng format ở mục 2 và mục 5), chỉ ảnh hưởng nếu về sau muốn suy diễn địa phương từ biển số.

## 7. Gợi ý áp dụng cho hậu xử lý OCR (post-processing)

Regex tham khảo để lọc/validate kết quả OCR thô (không thay thế logic chính thức, chỉ để loại nhiễu). Áp dụng theo bố cục nhận được (xem mục 3), không theo loại xe — cùng một ô tô có thể trả về cả 2 dạng tuỳ camera chụp được biển nào:

```
Biển 1 dòng (biển dài ô tô):
  ^\d{2}[A-HK-NPSTUVXYZ]-\d{3}\.\d{2}$

Biển 2 dòng (biển ngắn ô tô, mô tô, rơ-moóc/sơ-mi rơ-moóc/máy kéo):
  dòng trên  ^\d{2}[A-HK-NPSTUVXYZ]\d?$
  dòng dưới  ^\d{3}\.\d{2}$
```

(Tập chữ cái hợp lệ = 20 chữ cái ở mục 2; nên chuẩn hoá nhầm lẫn OCR phổ biến trước khi áp regex: `O↔0`, `I/1↔1`, `S↔5`, `B↔8`. Lưu ý biển kích thước 2 dòng của ô tô/rơ-moóc thường không có số phụ sau seri như biển mô tô đông xe — nếu cần phân biệt loại xe từ bố cục, kết hợp thêm output của model phân loại phương tiện thay vì suy từ riêng chuỗi ký tự.)

## Nguồn tham khảo bổ sung

Nguồn cho từng văn bản/mục cụ thể đã gắn trực tiếp trong cột "Nguồn" của các bảng ở mục 1, 3, 5 và các link inline ở mục 1, 2, 4. Dưới đây là các nguồn nền/bổ sung không gắn với một dòng cụ thể:

- [Biển xe cơ giới Việt Nam – Wikipedia tiếng Việt](https://vi.wikipedia.org/wiki/Bi%E1%BB%83n_xe_c%C6%A1_gi%E1%BB%9Bi_Vi%E1%BB%87t_Nam) — tổng quan lịch sử biển số xe VN.
- [Biển số xe các tỉnh sau sáp nhập 2025 (inmax.vn)](https://inmax.vn/tin-tuc/bien-so-xe-cac-tinh-sau-sap-nhap.html) — góc nhìn khác về việc gộp mã tỉnh, đối chiếu thêm với nguồn danviet.vn ở mục 1.
