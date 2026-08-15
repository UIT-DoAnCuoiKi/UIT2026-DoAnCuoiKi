# Khảo sát dataset OCR biển số Việt Nam, lần 2 (spec chặt)

**Ngày:** 2026-08-14 · **Mode:** 3 (dataset research) · **Người thực hiện:** research-agent
**Bối cảnh:** CRNN+CTC đã train xong, accuracy toàn biển 50,9% trên tập test topkek; phân tích theo độ phân giải cho thấy nút thắt là chất lượng ảnh (<20px/dòng: 39,9%; >=40px/dòng: 87,8%), không phải kiến trúc. Lọc bỏ ảnh nhỏ rồi train lại thất bại (31,5%) vì mất 36% dữ liệu. Vì vậy mục tiêu lần này là **tìm thêm dữ liệu có nhãn chuỗi ký tự, độ phân giải cao**, ưu tiên ảnh ban đêm và góc cổng bãi xe.
**Bổ sung cho:** [[2026-07-26-datasets-vietnam]], [[2026-07-28-dataset-inventory-verified]], [[2026-07-30-parking-vehicle-plate-datasets]]. Các bộ đã có (topkek, dtkngan, duydieu A1, nguyenquanglinh) không khảo sát lại.

**Giả định đã chọn khi đề bài có chỗ mở:** "có nhãn chuỗi ký tự" được tính là ĐẠT nếu nhãn cho phép **suy ra chuỗi một cách xác định**, tức là nhãn chuỗi trực tiếp (CSV/txt) hoặc nhãn bbox từng ký tự có **tên lớp là ký tự thật** (OCR-as-detection, sắp xếp theo toạ độ x của bbox và tách dòng theo y). Nhãn bbox từng ký tự nhưng tên lớp chỉ là **số thứ tự không có bảng ánh xạ** thì tính là KHÔNG đạt, vì không khôi phục được ký tự.

---

## 0. Kết luận nhanh

1. Manh mối Roboflow "Viet Nam OCR plate" là **đúng hướng nhưng bản đang xem là bản sao kém nhất**. Đã truy được **bản gốc** cùng 3.819 ảnh, cùng tên file, nhưng có **tên lớp là ký tự thật (31 lớp)** và **không bị resize**: `license-plate-vn/license-plate-ocr-hugcj`. Đây là ứng viên tốt nhất tìm được trong lần khảo sát này.
2. Dataset MAPR 2018 (3.000 ảnh xe máy chụp tại bãi giữ xe, có cả toạ độ lẫn chuỗi biển) **vẫn chưa từng được phát hành ở bất kỳ đâu**: không có mirror GitHub, Zenodo, IEEE DataPort, HuggingFace, không có paper nào công bố kèm link. Trang gốc vẫn ghi "update soon". Đề xuất: **xin trực tiếp**, vì đơn vị tổ chức chính là UIT, cùng trường với nhóm.
3. **Không có bộ nào đạt đủ toàn bộ tiêu chí**. Tiêu chí ban đêm (số 4) và góc cổng bãi xe (số 5) không bộ công khai nào có nhãn chuỗi đáp ứng được.
4. Bù lại có 2 bộ nước ngoài rất sát use-case để tiền huấn luyện, đều có chuỗi biển + 4 góc + ảnh đêm: **RodoSol-ALPR** (20.000 ảnh, 1280x720, một nửa là xe máy biển 2 dòng, chụp ngày và đêm tại trạm thu phí) và **UFPR-ALPR** (4.500 ảnh, 1920x1080). Cả hai cần ký license agreement gửi từ email trường.
5. Ngoài hướng "tìm thêm dữ liệu", có một hướng thứ ba được chứng minh bằng số liệu: **siêu phân giải (super-resolution) + hợp nhất nhiều khung hình**. Trên UFPR-SR-Plates, nhận dạng đúng tăng từ 1,7% lên 31,1% với ảnh siêu phân giải đơn và lên 44,7% khi hợp nhất nhiều kết quả (mục C4). Đây là bằng chứng học thuật trực tiếp cho đúng vấn đề nhóm đang gặp.

---

## A. Xác minh 2 manh mối từ lần trước

### A1. Roboflow "Viet Nam OCR plate" và phả hệ của nó

Trang gốc chặn WebFetch (403), toàn bộ số liệu dưới đây lấy qua bản render `r.jina.ai` ngày 2026-08-14.

#### A1.1. Bản đang xem lần trước: `license-plate-reg/viet-nam-ocr-plate`

| Mục | Nội dung |
|---|---|
| URL | [universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate](https://universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate) |
| Size | 3.819 ảnh; split v1: 3.054 train (80%) / 765 valid (20%) / 0 test |
| Classes | **32 lớp: `0, 1, 2, ..., 29`, `C`, `words`** (xác minh qua trang model, [nguồn](https://universe.roboflow.com/paracel/viet-nam-ocr-plate-klrfn) trích cùng danh sách lớp) |
| Có nhãn chuỗi ký tự? | **KHÔNG (theo giả định ở đầu note)**. Tên lớp là số thứ tự 0-29 và không có bảng ánh xạ số-sang-ký-tự công bố. Suy đoán 0-9 là chữ số, 10-29 là 20 chữ cái, cộng lớp `C` là 21 chữ cái seri, nhưng **đây là suy đoán, chưa xác minh được** |
| Độ phân giải | **Bị phá hỏng**: tiền xử lý v1 ghi rõ "Auto-Orient: Applied" và **"Resize: Stretch to 640x640"**. Ảnh crop biển bị kéo giãn lên 640x640, tức là nội suy phóng to, không thêm chi tiết thật, và làm méo tỉ lệ biển 1 dòng |
| Loại biển | Suy từ tên file trong tab browse: `xemay*.jpg` (xe máy, biển 2 dòng), `CarLongPlate*.jpg` (biển dài ô tô, 1 dòng), `PlateBaza*.jpg` (không rõ nguồn gốc, **chưa xác minh được là biển VN hay không**). Trong 50 ảnh đầu của split valid, đa số là `xemay*`, chưa đếm được tỉ lệ đầy đủ |
| Ánh sáng | Trang không mô tả; không quan sát được dấu hiệu ảnh đêm trong phần preview |
| License | Public Domain CC0 1.0 (theo trang) |
| Ngày publish | Khoảng 3/2025 |

Nguồn: [r.jina.ai render trang chính](https://r.jina.ai/https://universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate), [render trang dataset v1](https://r.jina.ai/https://universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate/dataset/1), [render tab browse](https://r.jina.ai/https://universe.roboflow.com/license-plate-reg/viet-nam-ocr-plate/browse).

#### A1.2. Bản gốc tìm được: `license-plate-vn/license-plate-ocr-hugcj` (ứng viên số 1)

| Mục | Nội dung |
|---|---|
| URL | [universe.roboflow.com/license-plate-vn/license-plate-ocr-hugcj](https://universe.roboflow.com/license-plate-vn/license-plate-ocr-hugcj) |
| Size | **3.819 ảnh** (trùng khít con số của A1.1); split v1: 2.675 train / 764 valid / 380 test. Bản v3 có 9.169 ảnh do augment 3 output/ảnh train |
| Classes | **31 lớp, tên là ký tự thật: `0-9` và `A B C D E F G H K L M N P R S T U V X Y Z`** |
| Có nhãn chuỗi ký tự? | **CÓ (gián tiếp)**. Đây là OCR-as-detection với tên lớp là ký tự thật, nên ghép chuỗi được bằng cách sắp xếp bbox theo x và tách 2 dòng theo y |
| Độ phân giải | **Giữ nguyên ảnh gốc**: tiền xử lý v1 chỉ có "Auto-Orient: Applied", **không có bước Resize**. Kích thước thật **chưa xác định được, cần tải về đo** |
| Loại biển | Cùng bộ tên file `xemay*`, `CarLongPlate*`, `PlateBaza*`. **Tỉ lệ 1 dòng / 2 dòng chưa xác định được, cần tải về đếm theo prefix tên file** |
| Ánh sáng | Không có mô tả, **chưa xác minh được** |
| License | **Trang không ghi license** (chỉ có footer "© 2026 Roboflow, Inc."). Bản sao ở A1.1 ghi CC0, bản dẫn xuất ở A1.3 ghi CC BY 4.0. **Ba bản của cùng một dữ liệu ghi ba license khác nhau, phải coi là chưa xác minh** |
| Ngày publish | 11-12/04/2024 (sớm hơn A1.1 gần một năm) |
| Ghi chú | Trang công bố model mAP@50 98,5%, precision 97,0%, recall 97,7%. Đây là số tác giả tự công bố trên tập valid cùng phân phối, không phải đánh giá độc lập |

Nguồn: [render trang chính](https://r.jina.ai/https://universe.roboflow.com/license-plate-vn/license-plate-ocr-hugcj), [render dataset v1](https://r.jina.ai/https://universe.roboflow.com/license-plate-vn/license-plate-ocr-hugcj/dataset/1), [render dataset v3](https://r.jina.ai/https://universe.roboflow.com/license-plate-vn/license-plate-ocr-hugcj/dataset/3), [render browse](https://r.jina.ai/https://universe.roboflow.com/license-plate-vn/license-plate-ocr-hugcj/browse).

**Vì sao bộ 31 lớp này đáng tin là biển VN:** tập chữ cái `A B C D E F G H K L M N P R S T U V X Y Z` khớp đúng tập seri hợp lệ của biển Việt Nam (loại bỏ I, J, O, Q, W) đã ghi ở note [[quy-dinh-bien-so-xe-vn]] mục 2, cộng thêm chữ R vốn dùng cho rơ-moóc. Một dataset nước ngoài sẽ không có đúng tập chữ cái thiếu I/J/O/Q/W này.

#### A1.3. Bản dẫn xuất mới nhất: `ntts-workspace/ocr-license-plate-vn`

| Mục | Nội dung |
|---|---|
| URL | [universe.roboflow.com/ntts-workspace/ocr-license-plate-vn](https://universe.roboflow.com/ntts-workspace/ocr-license-plate-vn) |
| Size | 3.188 ảnh; split v3: 6.696 train (đã augment) / 637 valid / 319 test |
| Classes | **36 lớp: `0-9` và `A-Z` đầy đủ** |
| Có nhãn chuỗi ký tự? | CÓ (gián tiếp, như A1.2). Lưu ý 36 lớp gồm cả I, J, O, Q, W vốn không có trên biển VN, nhiều khả năng các lớp này rỗng hoặc gần rỗng |
| Độ phân giải | "Resize: Fit (white edges) in 640x640" cộng augment (xoay ±8°, brightness ±15%, exposure ±15%, blur tới 2px, noise 0,5%). Fit có viền trắng nên **không méo tỉ lệ** như bản A1.1, nhưng vẫn là ảnh đã chuẩn hoá, không phải gốc |
| Loại biển | Cùng bộ tên file `xemay*`, `CarLongPlate*`, `PlateBaza*` |
| License | CC BY 4.0 (theo trang) |
| Ngày publish | Bản v3 generated 16/05/2026 (mới nhất trong 3 bản) |

Nguồn: [render trang chính](https://r.jina.ai/https://universe.roboflow.com/ntts-workspace/ocr-license-plate-vn), [render dataset v3](https://r.jina.ai/https://universe.roboflow.com/ntts-workspace/ocr-license-plate-vn/dataset/1), [render browse](https://r.jina.ai/https://universe.roboflow.com/ntts-workspace/ocr-license-plate-vn/browse).

**Chốt cho manh mối A1:** cả 3 bản là cùng một dữ liệu gốc (tên file trùng nhau). Nếu dùng, **lấy bản `license-plate-vn/license-plate-ocr-hugcj`** vì tên lớp là ký tự thật và không bị resize. Việc cần làm ngay: xin `ROBOFLOW_API_KEY` (tài khoản free là đủ), tải bản v1, rồi đo phân bố kích thước ảnh và đếm tỉ lệ `xemay` / `CarLongPlate` / `PlateBaza`, đồng thời kiểm tra `PlateBaza*` có phải biển VN không.

### A2. Dataset MAPR 2018 "Vietnamese Bike License Plate Recognition"

| Mục | Nội dung |
|---|---|
| URL | [mapr.uit.edu.vn/2018/vietnamese-bike-license-plate-recognition](https://mapr.uit.edu.vn/2018/vietnamese-bike-license-plate-recognition) |
| Size | 3.000 ảnh xe máy: 2.000 train, 1.000 test |
| Bối cảnh | Chụp tại **bãi giữ xe của một khách sạn ở Việt Nam**, đúng use-case của đề tài nhất trong toàn bộ khảo sát |
| Nhãn | Mỗi ảnh kèm một file text. Định dạng ví dụ trên trang: `1 397 223 121 92 52M6-9848`, tức là số lượng biển, rồi `x y w h`, rồi **chuỗi biển**. Có cả toạ độ lẫn chuỗi |
| Có nhãn chuỗi ký tự? | CÓ theo mô tả, nhưng không dùng được vì không tải được |
| Tình trạng | Trang vẫn ghi "Link the download the training data: **update soon**". Tổ chức bởi VAPR (Vietnamese Association for Pattern Recognition) và **Trường Đại học Công nghệ Thông tin (UIT)**, hội nghị MAPR 2018 tổ chức tại TP.HCM ngày 05-06/04/2018 |
| Đã tìm mirror ở đâu | GitHub (nhiều truy vấn khác nhau), HuggingFace Datasets, Zenodo/IEEE DataPort qua tìm kiếm web, các paper ALPR có trích MAPR, trang tổng hợp dataset ALPR của UFRGS. **Không tìm thấy bất kỳ bản phát hành lại nào**. Các repo GitHub Việt Nam có mô tả "biển số xe máy trong bãi giữ xe" (`neyugncol/vietnamese-motorbike-license-plate-recognition`, `nqkhanh2002`, `mrzaizai2k`) đều **không kèm dataset và không nhắc tới MAPR** |

Nguồn: [trang challenge MAPR 2018](https://mapr.uit.edu.vn/2018/vietnamese-bike-license-plate-recognition), [trang MAPR 2018](https://mapr.uit.edu.vn/2018/mapr-2018), [repo neyugncol (MIT, không có dataset)](https://github.com/neyugncol/vietnamese-motorbike-license-plate-recognition), [trang tổng hợp dataset ALPR của UFRGS, chỉ liệt kê AOLP/SSIG/Cars, không có MAPR](https://www.inf.ufrgs.br/~crjung/alpr-datasets/).

**Đề xuất hành động (chi phí thấp, lợi ích cao):** nhóm đang học tại chính UIT, đơn vị đồng tổ chức MAPR. Nhờ giảng viên hướng dẫn gửi email tới ban tổ chức MAPR (`mapr@uit.edu.vn`, ghi trên trang Contact us của hội nghị) hoặc liên hệ MMLab/khoa để xin bản dữ liệu challenge 2018 cho mục đích đồ án. Nếu xin được, đây là **bộ duy nhất vừa đúng bối cảnh bãi giữ xe, vừa toàn xe máy biển 2 dòng, vừa có chuỗi ký tự**, giải quyết đúng lỗi hệ thống hiện tại (mất chữ số phụ của seri ở dòng trên).

---

## B. Ứng viên mới khảo sát trong đợt này (biển Việt Nam)

### B1. Kaggle `raidendg/license-plate-dataset`

| Mục | Nội dung |
|---|---|
| URL | [kaggle.com/datasets/raidendg/license-plate-dataset](https://www.kaggle.com/datasets/raidendg/license-plate-dataset) |
| Size | 1.000 ảnh, tổng dung lượng **24,75 MB** |
| Có nhãn chuỗi ký tự? | **KHÔNG**. Trang chỉ mô tả là ảnh thô, không nêu file nhãn nào |
| Độ phân giải | Không ghi. Suy ra trung bình khoảng 25 KB/ảnh, tức là ảnh nén nhỏ. **Cần tải về đo nếu vẫn muốn dùng** |
| Bối cảnh | Tự mô tả là "Vietnamese Vehicle License Plate (CCTV) Dataset", nhắm tới cả bài toán bù nhoè do chuyển động |
| License | MIT |
| Verdict | **Loại** theo tiêu chí 1 |

Nguồn: [r.jina.ai render 2026-08-14](https://r.jina.ai/https://www.kaggle.com/datasets/raidendg/license-plate-dataset).

### B2. Roboflow `lowlight-images/low-light-license-plate`

| Mục | Nội dung |
|---|---|
| URL | [universe.roboflow.com/lowlight-images/low-light-license-plate](https://universe.roboflow.com/lowlight-images/low-light-license-plate) |
| Size | 335 ảnh |
| Classes | 1 lớp `license-plate` (chỉ bbox vùng biển) |
| Có nhãn chuỗi ký tự? | **KHÔNG** |
| Ánh sáng | **Là bộ duy nhất tìm được nhắm riêng điều kiện thiếu sáng**, theo tên và ảnh mẫu |
| Biển nước nào | **Chưa xác minh được**, trang không ghi. Không có căn cứ nói là biển VN |
| License | CC BY 4.0 |
| Verdict | Loại khỏi vai trò dữ liệu OCR. Có thể tham khảo cho phần tăng cường ảnh thiếu sáng của Đức, nhưng cỡ mẫu 335 quá nhỏ |

Nguồn: [r.jina.ai render 2026-08-14](https://r.jina.ai/https://universe.roboflow.com/lowlight-images/low-light-license-plate).

### B3. Bộ dữ liệu kèm repo `winter2897` (Jetson Nano ALPR)

| Mục | Nội dung |
|---|---|
| URL | [github.com/winter2897/.../doc/dataset.md](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano/blob/main/doc/dataset.md) |
| Nội dung | Hai bộ tải qua Google Drive: (a) **Detection dataset** (bbox vùng biển, VOC + YOLO), (b) **Recognition dataset** mô tả là để "detect and classify characters", tức là nhãn từng ký tự |
| Có nhãn chuỗi ký tự? | **Có thể có (gián tiếp)** nếu tên lớp của bộ (b) là ký tự thật. **Chưa xác minh được**, phải tải từ Google Drive mới biết |
| Size / độ phân giải | Trang không ghi số ảnh lẫn kích thước |
| License | Không ghi |
| Bối cảnh | Video test mô tả là "street scenes in Vietnam", tức là ảnh đường phố chứ không phải cổng bãi xe |
| Verdict | Đáng tải về kiểm tra vì chi phí thấp, nhưng không kỳ vọng cao (ảnh đường phố, không rõ license) |

### B4. Các bộ VN khác đã rà nhưng loại ngay theo tiêu chí 1

Rà qua trang tìm kiếm Roboflow Universe với truy vấn "vietnam license plate ocr" (50 project đầu, [render](https://r.jina.ai/https://universe.roboflow.com/search?q=vietnam%20license%20plate%20ocr)):

- Chỉ có bbox 1 lớp, không có nhãn ký tự: `tran-ngoc-xuan-tin-k15-hcm-dpuid/vietnam-license-plate-h8t3n` (1.000), `eric-nguyen-knfxn/vietnam-license-plate-curhr` (350), `chicken-and-duck-pkkbi/vietnam-license-plate-detection` (864), `demo-tracking/license-plate-vietnam-car` (235), `tct-pjmki/license-detection-vietnam` (244), `annvuong0110-gmail-com/vietnam-license-plate-srqyi` (55).
- Nhãn loại xe chứ không phải ký tự: `datnguyentan/vietnam-license-plate-w6gdc` (2.030), `.../vietnam-license-plate-ver1` (3.720), `.../vietnam-license-plate-2wheels` (666), đều 3 lớp `car / motorcycle / plate`.
- Tên lớp là số thứ tự `0-26`, không có bảng ánh xạ, cùng dạng vấn đề như A1.1: `nbl/license-plate-ocr-6hifi` (4.020), `licenseplate-vejey/plate-ocr-wpm3t` (3.820), `david-rai-dscloud-me/vietnam-license-v1` (3.820). Ba bộ này cỡ 3.82k rất có thể cũng là bản sao của cùng dữ liệu ở A1.
- Cỡ quá nhỏ: `bs-workspace-g5j7o/vietnam-license-plate-character` (496, lớp `0-9, A-L`), `haihun/vietnam-license-plate-2` (332), `dataset-format-conversion-iidaz/vietnam-license-plate-recognition` (200).
- `hr-alpha/vietnamese-license-plate-ocr` (3,06k) xuất hiện trong kết quả tìm kiếm nhưng **trang trả về 404 khi truy cập, dataset đã bị xoá hoặc chuyển riêng tư** ([render](https://r.jina.ai/https://universe.roboflow.com/hr-alpha/vietnamese-license-plate-ocr)).
- `trandoan/ocr-plate-cdk4t` (5.362 ảnh, CC BY 4.0) có cỡ lớn nhất nhưng **tiền xử lý "Resize to 320x240 (Stretch)"**, tức là hạ giải mạnh, đi ngược đúng tiêu chí quan trọng nhất, và trang không liệt kê tên lớp. Không khuyến nghị ([render](https://r.jina.ai/https://universe.roboflow.com/trandoan/ocr-plate-cdk4t)).

### B5. Nguồn thương mại và tổng hợp toàn cầu (đều không dùng được)

| Bộ | Kết quả kiểm tra |
|---|---|
| [HF `UniDataPro/license-plate-detection`](https://huggingface.co/datasets/UniDataPro/license-plate-detection) | Quảng cáo 1.200.000+ ảnh có OCR, 32+ quốc gia trong đó **có Việt Nam**, nhãn gồm chuỗi biển, bbox, quốc gia, màu biển. Nhưng bản công khai **chỉ là preview 140 ảnh**, license `cc-by-nc-nd-4.0`, muốn bản đầy đủ phải liên hệ mua. **Loại** |
| [HF `ud-smart-city/license-plate-dataset`](https://huggingface.co/datasets/ud-smart-city/license-plate-dataset) | Quảng cáo 2,6 triệu ảnh, 86 quốc gia. Cùng mô hình teaser thương mại. **Chưa xác minh được** phần miễn phí có gì, không khuyến nghị |
| [GLPD, arXiv 2405.10949](https://arxiv.org/abs/2405.10949) | 5 triệu+ ảnh, 74 quốc gia, nhãn rất giàu (chuỗi biển, 4 góc, mask, hãng/màu/đời xe), thu chủ yếu từ Platesmania. **Việt Nam không xuất hiện trong phần phân bố quốc gia của bài báo**, chưa xác minh được có hay không. License CC BY-NC-ND 4.0. Link tải trỏ về HF `siddagra/Global-Licenseplate-Dataset` nhưng **truy cập trả về 401**, chưa xác minh được là tải được hay không |

---

## C. Dataset nước ngoài đúng bối cảnh, dùng để tiền huấn luyện

### C1. RodoSol-ALPR (Brazil): ứng viên tiền huấn luyện tốt nhất

| Mục | Nội dung |
|---|---|
| Trích dẫn | R. Laroca, E. V. Cardoso, D. R. Lucio, V. Estevam, D. Menotti, "On the Cross-dataset Generalization in License Plate Recognition," VISAPP 2022, pp. 166-178 |
| URL | [github.com/raysonlaroca/rodosol-alpr-dataset](https://github.com/raysonlaroca/rodosol-alpr-dataset) |
| Size | **20.000 ảnh**, chia đều 4 nhóm 5.000: ô tô biển Brazil, **xe máy biển Brazil**, ô tô biển Mercosur, **xe máy biển Mercosur** |
| Độ phân giải | **1.280 x 720 px** cho toàn bộ ảnh (ảnh cảnh, không phải crop) |
| Có nhãn chuỗi ký tự? | **CÓ**. Mỗi ảnh một file text: loại xe (car/motorcycle), bố cục biển, **chuỗi biển** (vd `ABC-1234`), và **toạ độ (x, y) của cả 4 góc biển** |
| Loại biển | **Một nửa là xe máy, biển xe máy Brazil/Mercosur có 2 dòng ký tự**, giống bố cục 2 dòng của biển xe máy VN |
| Ánh sáng | **Chụp cả ban ngày và ban đêm**, nhiều làn xe khác nhau, cả ngày nắng lẫn ngày mưa |
| Bối cảnh | **Camera cố định tại trạm thu phí** trên quốc lộ ES-060, khoảng cách xe tới camera gần như không đổi. Đây là bối cảnh gần với cổng kiểm soát ra vào nhất trong nhóm dataset công khai |
| License | Chỉ dùng cho nghiên cứu học thuật, miễn phí cho cơ sở đào tạo/nghiên cứu, phi thương mại. **Phải điền license agreement và gửi từ email trường (.edu/.ac) tới rblsantos@inf.ufpr.br**, phản hồi thường 1-5 ngày làm việc |
| Khác biệt định dạng biển | Biển Brazil `ABC-1234` (3 chữ + 4 số), Mercosur `ABC1D23`. Khác hoàn toàn định dạng VN `2 số + chữ (+số) + 4-5 số`, nên **không dùng để học ràng buộc cú pháp**, chỉ dùng để học đặc trưng hình ảnh của ký tự dập nổi trên nền phản quang, đặc biệt là ký tự dưới ánh đèn ban đêm |
| Mức hữu ích cho transfer learning | **Cao**. Cùng bảng chữ Latin + chữ số, cùng bố cục 2 dòng cho xe máy, có ảnh đêm, có 4 góc để tập nắn phối cảnh. Nên pretrain CRNN trên RodoSol rồi fine-tune trên dữ liệu VN |

Nguồn: [README RodoSol-ALPR](https://github.com/raysonlaroca/rodosol-alpr-dataset/blob/main/README.md?plain=1).

### C2. UFPR-ALPR (Brazil)

| Mục | Nội dung |
|---|---|
| Trích dẫn | R. Laroca và cộng sự, "A Robust Real-Time Automatic License Plate Recognition Based on the YOLO Detector," IJCNN 2018 (đã có trong refs.bib, key `laroca2018ufpr`) |
| URL | [web.inf.ufpr.br/vri/databases/ufpr-alpr/](https://web.inf.ufpr.br/vri/databases/ufpr-alpr/) |
| Size | 4.500 ảnh, 150 xe, hơn 30.000 ký tự biển. Gồm 900 ảnh ô tô biển xám, 300 ảnh ô tô biển đỏ, **300 ảnh xe máy** (con số này tính cho mỗi camera, tổng 1.500 ảnh/camera, 3 camera) |
| Độ phân giải | **1.920 x 1.080 px**, định dạng PNG |
| Có nhãn chuỗi ký tự? | **CÓ**: định danh và vị trí biển, **vị trí từng ký tự**, cộng thông tin xe (loại, hãng, model, năm) |
| Bối cảnh | Ảnh chụp khi **cả xe lẫn camera đều đang di chuyển** (camera đặt trong xe khác). Đây là điểm yếu so với use-case cổng bãi xe tĩnh |
| Ánh sáng | Trang không nêu rõ tỉ lệ ngày/đêm, **chưa xác minh được** |
| License | Học thuật, phi thương mại, phải ký license agreement |
| Mức hữu ích | Trung bình. Độ phân giải cao và có nhãn ký tự nên tốt cho pretrain, nhưng bối cảnh camera động khác xa cổng bãi xe, và chỉ 300 ảnh xe máy |

### C3. CCPD (Trung Quốc) và AOLP-AC (Đài Loan)

Cả hai đã ghi chi tiết ở [[2026-07-30-parking-vehicle-plate-datasets]] mục C1 và C4, không lặp lại. Tóm tắt liên quan tới lần khảo sát này:

- **CCPD**: hơn 300.000 ảnh chụp **tại bãi đỗ xe Bắc Kinh**, nhãn mã hoá trong tên file gồm bbox, **4 toạ độ góc**, **chuỗi biển 7 ký tự**, độ sáng, độ mờ; **38,6% ảnh ban đêm** (số đã xác minh ở note YOLO). License MIT, tải tự do. **Đây là bộ duy nhất vừa đúng bối cảnh bãi xe, vừa có tỉ lệ ảnh đêm được định lượng, vừa tải được ngay không cần xin phép.** Nhược điểm: biển Trung Quốc bắt đầu bằng **một ký tự Hán** chỉ tỉnh, tập ký tự khác hẳn, nên chỉ pretrain phần đặc trưng thị giác chứ không transfer được đầu ra 36 lớp.
- **AOLP subset Access Control (AC)**: 681 ảnh, đúng kịch bản kiểm soát ra vào, nhưng phải xin mật khẩu giải nén qua tác giả, và cỡ mẫu quá nhỏ. Chỉ dùng để đối chiếu số liệu trong chương tổng quan.

### C4. Hai dataset hỗ trợ trực tiếp cho lập luận "nút thắt là độ phân giải"

Không phải dữ liệu train tiếng Việt, nhưng là **bằng chứng học thuật cho đúng vấn đề nhóm đang gặp**, rất đáng trích trong chương OCR để giải thích vì sao accuracy 50,9% không phải lỗi kiến trúc.

| Bộ | Nội dung |
|---|---|
| **UFPR-SR-Plates** (Nascimento và cộng sự, 2025, Journal of the Brazilian Computer Society) | 10.000 track, 100.000 cặp ảnh biển độ phân giải thấp và cao. Kết quả: nhận dạng đúng tăng từ **1,7% lên 31,1%** khi dùng ảnh siêu phân giải, và lên **44,7%** khi hợp nhất kết quả từ nhiều ảnh siêu phân giải trong cùng track. Công khai tại [valfride.github.io/nascimento2024toward](https://valfride.github.io/nascimento2024toward/), [arXiv 2505.06393](https://arxiv.org/abs/2505.06393) |
| **LPLC** (Wojcik và cộng sự, SIBGRAPI 2025) | 10.210 ảnh, 12.687 biển được gán nhãn **mức độ đọc được**: perfect / good / poor / illegible. Công khai tại [github.com/lmlwojcik/lplc-dataset](https://github.com/lmlwojcik/lplc-dataset), [arXiv 2508.18425](https://arxiv.org/abs/2508.18425). Bài không đưa ngưỡng pixel cụ thể, nhưng cung cấp khung phân loại chất lượng để nhóm mô tả tập test của mình theo cách có tham chiếu học thuật thay vì tự đặt ngưỡng 20/30/40px |

Hệ quả thực tiễn: bảng độ phân giải mà nhóm đã đo (39,9% / 53,5% / 67,0% / 87,8% theo 4 mốc pixel) là một đóng góp đo lường hợp lệ, và có thể đặt cạnh hai công trình trên để lập luận. Đồng thời gợi ý một nhánh cải tiến rẻ hơn việc đi tìm dữ liệu mới: **hợp nhất nhiều khung hình của cùng một xe khi nó đi qua cổng** (camera bãi xe cho nhiều frame liên tiếp của cùng biển số), đúng cơ chế đã cho 44,7% so với 31,1% ở UFPR-SR-Plates.

---

## D. Bảng so sánh tổng hợp tất cả ứng viên

Cột "Chuỗi KT" = có nhãn chuỗi ký tự theo giả định ở đầu note. Cột "Độ phân giải" ghi đúng những gì xác minh được.

| # | Dataset | Nguồn | Size | Classes / nhãn | Chuỗi KT | Độ phân giải | Biển 1 dòng / 2 dòng | Ánh sáng | License | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| A1.2 | **license-plate-ocr-hugcj** | Roboflow | 3.819 | 31 lớp ký tự thật (0-9, A-Z trừ I J O Q W) | **CÓ** | **Gốc, không resize; giá trị thật chưa đo** | Có cả hai (`xemay*`, `CarLongPlate*`), tỉ lệ chưa đếm | Không rõ | **Trang không ghi** | ⭐ Ứng viên số 1, cần tải về đo |
| A1.1 | viet-nam-ocr-plate | Roboflow | 3.819 | 32 lớp tên số + `C` + `words` | KHÔNG (không có bảng ánh xạ) | Stretch 640x640, méo tỉ lệ | như trên | Không rõ | CC0 1.0 | Bỏ, dùng bản gốc thay thế |
| A1.3 | ocr-license-plate-vn | Roboflow | 3.188 | 36 lớp `0-9 A-Z` | CÓ | Fit 640x640 + augment | như trên | Không rõ | CC BY 4.0 | Dự phòng nếu A1.2 không rõ license |
| A2 | **MAPR 2018 bike LP** | UIT/VAPR | 3.000 | bbox + **chuỗi biển** | CÓ (theo mô tả) | Không công bố | **100% xe máy 2 dòng** | Không rõ | Chưa phát hành | ⭐ Đúng use-case nhất, **phải xin** |
| B1 | raidendg license-plate | Kaggle | 1.000 | ảnh thô | KHÔNG | ~25 KB/ảnh, nhỏ | Không rõ | Không rõ | MIT | Loại |
| B2 | low-light-license-plate | Roboflow | 335 | 1 lớp bbox | KHÔNG | Không rõ | Không rõ | **Thiếu sáng** | CC BY 4.0 | Loại (tham khảo) |
| B3 | winter2897 recognition set | GitHub/Drive | Không ghi | bbox ký tự | Có thể, chưa xác minh | Không rõ | Không rõ | Không rõ | Không ghi | Tải thử |
| B5a | UniDataPro | HuggingFace | 140 (preview) | chuỗi + bbox + màu | CÓ nhưng bản trả phí | Không rõ | Không rõ | Không rõ | CC BY-NC-ND 4.0 | Loại |
| B5c | GLPD | arXiv/HF | 5.000.000+ | chuỗi + 4 góc + mask | CÓ | Không rõ | Không rõ | Không rõ | CC BY-NC-ND 4.0 | Loại (401, và VN không rõ có mặt) |
| C1 | **RodoSol-ALPR** | UFPR | 20.000 | loại xe + bố cục + **chuỗi** + **4 góc** | CÓ | **1280x720** | 10.000 ô tô 1 dòng / **10.000 xe máy 2 dòng** | **Ngày và đêm, có mưa** | Học thuật, ký agreement | ⭐ Pretrain số 1 |
| C2 | UFPR-ALPR | UFPR | 4.500 | chuỗi + vị trí từng ký tự | CÓ | **1920x1080** | Có ô tô và xe máy | Chưa rõ | Học thuật, ký agreement | Pretrain phụ |
| C3a | CCPD | GitHub | >300.000 | bbox + 4 góc + **chuỗi 7 ký tự** | CÓ (ký tự Trung Quốc) | Không đồng nhất | Chỉ 1 dòng | **38,6% đêm** | MIT, tải tự do | Pretrain, tải được ngay |
| C3b | AOLP-AC | Xin qua form | 681 | chuỗi biển Đài Loan | CÓ | Không rõ | 1 dòng | 1 kịch bản | Học thuật, xin mật khẩu | Chỉ đối chiếu |
| C4a | UFPR-SR-Plates | UFPR | 100.000 cặp LR/HR | chuỗi + cặp độ phân giải | CÓ | Cặp thấp/cao | Brazil | Không rõ | Công khai | Tham chiếu phương pháp |
| C4b | LPLC | GitHub | 10.210 ảnh / 12.687 biển | nhãn mức độ đọc được | Không (nhãn legibility) | Ảnh radar giao thông | Brazil | Nhiều thời điểm trong ngày | Công khai | Tham chiếu phương pháp |

---

## E. Khuyến nghị

Xếp theo thứ tự nên làm, kèm chi phí ước tính.

1. **Tải và đo `license-plate-vn/license-plate-ocr-hugcj` ngay (chi phí: 1 buổi).** Cần `ROBOFLOW_API_KEY` tài khoản free. Việc phải làm sau khi tải: (a) đo phân bố chiều cao vùng ký tự theo từng dòng để biết bộ này có thật sự khá hơn topkek (trung vị 46x30px) hay không, (b) đếm tỉ lệ `xemay` / `CarLongPlate` / `PlateBaza`, (c) mở xem `PlateBaza*` có phải biển VN không, (d) ghép chuỗi từ bbox ký tự rồi validate bằng regex biển VN ở note [[quy-dinh-bien-so-xe-vn]] mục 7, tỉ lệ chuỗi hợp lệ chính là thước đo chất lượng nhãn của bộ này. Nếu (a) cho kết quả tốt hơn topkek thì đây là nguồn bổ sung sạch nhất, thêm khoảng 3.800 mẫu có nhãn.
2. **Gửi email xin dataset MAPR 2018 (chi phí: 1 email, chờ phản hồi).** Qua giảng viên hướng dẫn, gửi `mapr@uit.edu.vn` hoặc liên hệ nội bộ UIT. Đây là bộ duy nhất khớp cả bãi giữ xe, xe máy 2 dòng, và chuỗi biển. Rủi ro: có thể không còn ai giữ dữ liệu sau 8 năm, nên gửi song song với việc làm mục 1 và 3, không chờ.
3. **Ký license agreement RodoSol-ALPR (chi phí: 1 form + email trường, chờ 1-5 ngày).** Dùng để **pretrain CRNN**: 10.000 ảnh xe máy biển 2 dòng, có ảnh đêm, 1280x720, có 4 góc biển để tập nắn phối cảnh. Đây là cách rẻ nhất để có mẫu ban đêm thật cho biển phản quang mà không cần tự đi chụp. Lưu ý viết rõ trong báo cáo: pretrain trên biển Brazil, fine-tune trên biển VN, và **không** dùng ràng buộc cú pháp Brazil.
4. **Tải CCPD (chi phí: dung lượng ổ đĩa).** MIT, tải tự do, không cần xin phép, đúng bối cảnh bãi xe, 38,6% ảnh đêm. Dùng để pretrain phần thị giác (backbone CNN của CRNN) trước khi thay đầu ra sang 36 lớp Latin.
5. **Thử nghiệm hợp nhất nhiều khung hình thay vì chỉ tìm thêm dữ liệu (chi phí: 1-2 ngày code).** Có bằng chứng ở mục C4: 31,1% lên 44,7% khi hợp nhất nhiều kết quả của cùng một biển. Hệ thống bãi xe vốn có nhiều frame liên tiếp của cùng một xe khi xe đi qua cổng, nên đây là cải tiến gần như miễn phí về dữ liệu. Kết hợp với nắn phối cảnh 4 điểm (đã chứng minh 44% lên 76% trên A1).
6. **Không dùng:** GLPD, UniDataPro, ud-smart-city (thương mại hoặc không tải được), raidendg, low-light-license-plate, và toàn bộ nhóm B4 (chỉ bbox hoặc tên lớp số hoặc bị hạ giải).

---

## F. Gap analysis: tiêu chí không bộ nào đáp ứng

| Tiêu chí | Tình trạng sau lần khảo sát 2 |
|---|---|
| 1. Có nhãn chuỗi ký tự + biển VN | **Đạt một phần.** Chỉ có 2 nguồn: topkek (đã có) và nhóm A1 trên Roboflow (khoảng 3.800 ảnh, cùng một dữ liệu gốc bị fork nhiều lần). Không tìm thấy nguồn thứ ba độc lập nào |
| 3. Độ phân giải >=40px mỗi dòng ký tự | **Chưa xác minh được ở bất kỳ bộ VN nào.** Không trang nguồn nào công bố kích thước vùng biển. Bộ duy nhất chắc chắn không bị hạ giải là A1.2, nhưng giá trị thật vẫn phải tải về đo. Các bộ VN còn lại hoặc bị resize cứng (640x640, 320x240) hoặc dung lượng/ảnh quá nhỏ |
| 4. Ảnh ban đêm | **KHÔNG bộ biển VN nào đáp ứng.** Đây vẫn là khoảng trống lớn nhất, đúng như kết luận lần 1. Chỉ có dataset nước ngoài định lượng được: CCPD 38,6% đêm, RodoSol có ngày và đêm. Bộ `low-light-license-plate` (335 ảnh) không xác minh được là biển VN và không có nhãn chuỗi. **Không có bất kỳ mẫu công khai nào về hiện tượng loá màng phản quang biển VN dưới đèn pha hoặc đèn hồng ngoại** |
| 5. Góc camera cổng bãi xe / kiểm soát ra vào | **KHÔNG bộ biển VN nào có nhãn chuỗi đáp ứng.** MAPR 2018 là bộ duy nhất đúng bối cảnh nhưng chưa phát hành. Gần nhất trong nhóm tải được là RodoSol (trạm thu phí, camera cố định) và CCPD (bãi xe), đều là biển nước ngoài. Lưu ý: theo mục H của note [[2026-07-30-parking-vehicle-plate-datasets]], các bộ **detect** (A1-A4 lần 1) thực chất đã là ảnh cổng bãi xe, nên khoảng trống này chỉ còn đúng với riêng dữ liệu **OCR có nhãn chuỗi** |
| 6. Ghi rõ số lượng biển 1 dòng và 2 dòng | **Chưa bộ VN có nhãn chuỗi nào công bố.** Với A1.2 có thể tự đếm theo prefix tên file (`xemay` so với `CarLongPlate`), đây là ưu điểm nhỏ so với topkek. RodoSol công bố chính xác 10.000 / 10.000 |
| 7. Nhãn polygon 4 góc biển | **KHÔNG bộ VN nào có nhãn chuỗi kèm 4 góc.** duydieu (A1 lần 1) có 4 góc nhưng không có chuỗi; nhóm A1 lần này có bbox ký tự nhưng không có 4 góc biển. **RodoSol và CCPD là hai bộ duy nhất có đồng thời 4 góc và chuỗi biển**, đây là lý do mạnh để dùng chúng cho phần nắn phối cảnh |
| 8. License dùng được cho đồ án | **Rủi ro chưa gỡ.** Ứng viên số 1 (A1.2) không ghi license trên trang, trong khi 2 bản sao của cùng dữ liệu ghi CC0 và CC BY 4.0. RodoSol/UFPR-ALPR/AOLP đều cần ký giấy. Chỉ CCPD (MIT) là sạch và tải tự do |

**Khoảng trống tổng kết:** không tồn tại (công khai, tải được) dataset nào đồng thời có biển Việt Nam + nhãn chuỗi + độ phân giải cao + ảnh ban đêm. Sau hai lần khảo sát độc lập, kết luận này ổn định. Phần dữ liệu ban đêm và góc cổng bãi xe **bắt buộc phải tự thu thập**, không có đường vòng.

---

## G. Phương án thay thế nếu không xin được dữ liệu

### G1. Tự thu thập và gán nhãn

**Công cụ (đã kiểm tra license thật):**

| Công cụ | License | Phù hợp ở điểm nào | Nguồn |
|---|---|---|---|
| **Label Studio** | Apache 2.0, self-host bằng Docker/pip | Có sẵn **template OCR**: kết hợp `Rectangle`/`Polygon` để khoanh vùng và `TextArea` với `perRegion="true"` để **gõ chuỗi cho từng vùng**. Đây đúng là thao tác nhóm cần: khoanh biển rồi gõ chuỗi | [labelstud.io/templates/optical_character_recognition](https://labelstud.io/templates/optical_character_recognition), [github.com/HumanSignal/label-studio](https://github.com/HumanSignal/label-studio) |
| **CVAT** | MIT (bản Community), self-host bằng Docker Compose, dữ liệu không rời khỏi máy | Hỗ trợ bbox, **polygon**, mask, keypoint. Mạnh nhất khi cần **polygon 4 góc biển** để nắn phối cảnh. Gõ chuỗi phải làm qua attribute của object | [github.com/cvat-ai/cvat](https://github.com/cvat-ai/cvat) |
| **Roboflow Annotate** | Dịch vụ cloud, gói free có giới hạn dung lượng/số ảnh | Tiện vì export thẳng nhiều định dạng YOLO, nhưng **ảnh biển số là dữ liệu cá nhân** theo Luật Bảo vệ dữ liệu cá nhân (hiệu lực 01/01/2026), đẩy lên cloud bên thứ ba là rủi ro pháp lý cần cân nhắc. Ưu tiên self-host | Ghi chú của nhóm, xem CLAUDE.md và mục G của note lần 1 |

**Khuyến nghị công cụ:** Label Studio self-host cho phần gõ chuỗi (đúng template có sẵn), CVAT nếu ưu tiên polygon 4 góc. Không dùng cloud cho ảnh thật có biển số người khác.

**Ước lượng công sức (đây là ước lượng của người viết note, không có nguồn, cần hiệu chỉnh sau khi gán thử 50 ảnh):**

| Việc | Thời gian / ảnh | 500 ảnh | 1.000 ảnh |
|---|---|---|---|
| Chụp tại cổng bãi xe (đã dựng sẵn camera, chụp liên tục) | không đáng kể | 1-2 buổi | 2-3 buổi |
| Khoanh polygon 4 góc biển | 15-20 giây | 2,0-2,8 giờ | 4,0-5,5 giờ |
| Gõ chuỗi biển (biển 2 dòng chậm hơn vì có số phụ của seri) | 20-30 giây | 2,8-4,2 giờ | 5,5-8,3 giờ |
| Rà soát chéo giữa 2 thành viên trên 30% mẫu | 10 giây/ảnh | 0,4 giờ | 0,8 giờ |
| **Tổng công gán nhãn** | khoảng 40-55 giây/ảnh | **khoảng 5,5-7,5 giờ** | **khoảng 11-15 giờ** |

Nghĩa là 1.000 ảnh tự gán nhãn tốn khoảng **2 ngày công của một người**, chia đôi cho 2 thành viên là khoảng 1 ngày mỗi người. So với lợi ích (mẫu ban đêm thật, đúng góc camera thật, độ phân giải do nhóm kiểm soát), đây là chi phí hợp lý và nên làm, không nên chờ xin dataset.

**Ưu tiên nội dung chụp**, xếp theo mức độ lấp khoảng trống ở mục F:
1. Ban đêm dưới đèn cổng bãi và đèn pha xe (khoảng trống lớn nhất, không có nguồn nào thay thế).
2. Biển xe máy 2 dòng cận cảnh, đặc biệt **biển có số phụ sau seri** (dạng `59-X1`), vì đây đúng lỗi hệ thống đang mắc.
3. Trong hầm/nhà xe có mái che, ánh sáng đèn huỳnh quang.
4. Biển bẩn, biển cong, biển bị che một phần.

**Bắt buộc tuân thủ** phần quyền riêng tư đã ghi ở mục G của [[2026-07-30-parking-vehicle-plate-datasets]] và trong CLAUDE.md: kiểm soát truy cập ảnh thô, đặt thời hạn xoá, tránh lọt mặt người, xin phép đơn vị quản lý bãi xe.

### G2. Sinh dữ liệu tổng hợp biển số VN

**Công cụ có sẵn:** [NNDam/Vietnamese-License-Plate-Generator](https://github.com/NNDam/Vietnamese-License-Plate-Generator). Sinh 2 kiểu template (rectangle tức biển dài 1 dòng, và square tức biển vuông 2 dòng), kèm font riêng `MyFont-Regular_ver3.otf`, thư mục ảnh nền, xuất nhãn định dạng YOLO. Tập ký tự và template khai báo ở đầu `synthesis_plate.py` nên sửa được. **Repo không có file LICENSE**, tức là mặc định giữ toàn quyền tác giả, nên chỉ dùng nội bộ cho đồ án, không phát hành lại code hay dữ liệu sinh ra từ nó mà không hỏi tác giả.

**Cảnh báo quan trọng dựa trên số liệu của chính nhóm:** topkek đã có sẵn 5.547 ảnh sinh tổng hợp trong tổng 12.190, và accuracy vẫn chỉ 50,9%. Nghĩa là **thêm dữ liệu tổng hợp theo cách cũ gần như chắc chắn không cải thiện gì** vì nó không mô phỏng được đúng thứ đang thiếu: ảnh nhỏ, mờ, loá đèn. Nếu vẫn làm tổng hợp thì phải mô phỏng đúng suy giảm chất lượng:
- Hạ giải theo đúng phân bố kích thước đo được trên tập test thật (trung vị 46x30px), rồi phóng lại, để mô phỏng mất chi tiết.
- Thêm nhoè chuyển động, nhiễu cảm biến, nén JPEG mạnh.
- Mô phỏng loá phản quang: vùng sáng bão hoà cục bộ trên nền biển, đúng với đặc điểm màng phản quang và chữ dập nổi cao (1,7 ± 0,1) mm theo QCVN 08:2024/BCA (chi tiết ở note [[quy-dinh-bien-so-xe-vn]] mục 4).
- Biến dạng phối cảnh theo góc chụp chéo thật của camera cổng.

**Về đúng quy chuẩn QCVN 08:2024/BCA:** các thông số đã tra được và ghi ở note [[quy-dinh-bien-so-xe-vn]] mục 4 gồm kích thước biển (dài 520x110, ngắn 330x165, mô tô 190x140 mm), khoảng cách ký tự (ô tô 10 mm, riêng số "1" là 19 mm và 28 mm giữa hai số "1"; mô tô dòng trên 5 mm, dòng dưới 10 mm), 4 góc bo tròn, màu theo toạ độ CIE. **Kích thước chi tiết từng chữ/số nằm trong phụ lục bản vẽ kỹ thuật và chưa tra được dưới dạng bảng**, nên bộ sinh tổng hợp sẽ chỉ đúng quy chuẩn ở mức bố cục và khoảng cách, không đúng tuyệt đối ở mức hình dạng nét chữ. Cần ghi nhận giới hạn này trong báo cáo thay vì khẳng định "sinh đúng chuẩn".

**Thứ tự ưu tiên đề xuất:** tự thu thập ban đêm (G1) > pretrain trên RodoSol/CCPD (mục E3, E4) > hợp nhất nhiều khung hình (E5) > sinh tổng hợp có mô phỏng suy giảm (G2). Sinh tổng hợp xếp cuối vì đã có bằng chứng nội bộ là không hiệu quả với cách làm hiện tại.

---

## H. Những điều chưa xác minh được (đừng viết vào báo cáo như sự thật)

1. Độ phân giải thật của `license-plate-ocr-hugcj`. Phải tải về đo, chưa có số.
2. Tỉ lệ biển 1 dòng / 2 dòng của cả 3 bản trong nhóm A1. Đếm được qua prefix tên file sau khi tải.
3. `PlateBaza*.jpg` là ảnh gì, có phải biển Việt Nam không. Tìm "PlateBaza" trên web không ra nguồn nào.
4. License thật của `license-plate-ocr-hugcj`. Ba bản của cùng dữ liệu ghi ba license khác nhau.
5. Bảng ánh xạ lớp số sang ký tự của `viet-nam-ocr-plate` (32 lớp) và của các bộ `0-26`. Suy đoán có nhưng không có căn cứ.
6. Việt Nam có nằm trong GLPD hay không, và HF repo của GLPD có tải được không (trả 401).
7. Tỉ lệ ngày/đêm của UFPR-ALPR.
8. Nội dung thật của 2 bộ Google Drive trong repo `winter2897` (số ảnh, tên lớp, license).
9. MAPR 2018 có còn được lưu giữ ở UIT hay không. Chỉ biết chắc là chưa từng public.

---

**Feeds into:** Chương "Dữ liệu" (bảng inventory lần 2, phần license và gap analysis) và Chương "Nhận dạng ký tự / OCR" (Nhật, W4 và phần cải tiến ở W7-W9): lập luận nút thắt độ phân giải kèm tham chiếu UFPR-SR-Plates và LPLC, kế hoạch pretrain trên RodoSol-ALPR/CCPD, kế hoạch tự thu thập dữ liệu ban đêm. Ảnh hưởng phụ tới Chương "Triển khai edge" (hợp nhất nhiều khung hình khi xe qua cổng).
