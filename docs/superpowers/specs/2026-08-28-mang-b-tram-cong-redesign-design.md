# Mảng B: Trạm cổng redesign (webcam capture, layout, phím tắt, thu tiền khi ra)

* **Ngày:** 2026-08-28
* **Người phụ trách:** Lê Quang Hoài Đức (25410034)
* **Trạng thái:** Draft v1 (chờ review file, rồi writing-plans)
* **Thuộc:** SPEC 3 của roadmap `docs/superpowers/specs/2026-08-25-frontend-redesign-roadmap-design.md` (mảng B, thứ tự #3 sau A và C).
* **Tài liệu liên quan:**
  * `docs/superpowers/specs/2026-08-28-mang-c-loai-xe-gia-design.md` (mảng C, cung cấp `useVehicleGroupMap()` + hợp đồng dữ liệu ở mục 10)
  * `docs/superpowers/specs/2026-08-25-mang-a-phan-quyen-3-tang-design.md` (mảng A, đã bỏ KPI khỏi màn cổng)

## 1. Mục tiêu

Dựng lại màn Trạm cổng thành công cụ vận hành ra vào nhanh, thao tác được hoàn toàn bằng bàn phím, tối ưu cho một nhân viên xử lý cả vào và ra song song. Thêm chụp ảnh từ webcam qua `getUserMedia` gửi `POST /captures/infer` (path demo trên PC), giữ song song luồng WS push từ edge. Thu tiền khi ra ngay tại màn cổng với biên lai in được. Zero thống kê (kế thừa mảng A).

## 2. Quyết định đã chốt (brainstorm)

* **Nguồn ảnh hybrid:** mỗi panel có webcam (`getUserMedia`) + nút Chụp gửi `POST /captures/infer` là path chính; WS edge push vẫn nhận, route theo `direction` (in vào panel VÀO, out vào panel RA). Giữ được cả hai deployment.
* **Layout 3 chế độ:** chia đôi (VÀO song song RA), chỉ VÀO, chỉ RA. Chọn được, lưu localStorage. Mỗi panel có bộ chọn camera riêng (hỗ trợ 2 webcam ở chế độ chia đôi).
* **Phím tắt** (đã duyệt): xem mục 5.
* **Thu tiền khi ra:** fee > 0 mở dialog thu tiền (phương thức `cash|qr|ewallet` đã có); fee = 0 (grace/miễn/vé tháng) bỏ dialog, xác nhận ra luôn.
* **Biên lai:** panel HTML in được qua `window.print`, không có entity biên lai backend, không máy in vật lý.

## 3. Kiến trúc

Màn cổng dựng quanh capture theo panel. State ở `gate-page.tsx`:
* `layoutMode: "split" | "in" | "out"` (lưu localStorage).
* `activePanel: "in" | "out"` (cho phím tắt ở chế độ chia đôi).

Mỗi panel là `GatePanel` tự chứa: chọn camera, video preview, nút Chụp, `DecisionPanel`. Gate-page route capture (webcam hoặc WS) theo `direction` về panel khớp.

## 4. Components (files, `src/frontend/src/features/gate/`)

| File | Trạng thái | Vai trò |
|---|---|---|
| `gate-page.tsx` | rewrite | Layout switcher; giữ `activePanel`; render 1 hoặc 2 `GatePanel`; overlay cheatsheet phím tắt |
| `gate-panel.tsx` | new | Một hướng đầy đủ: `CameraView` + `DecisionPanel`. Props: `direction: "in"|"out"`, `capture: CaptureResponse|null`, `active: boolean`, `onActivate: () => void`, `onCaptured: (c) => void` |
| `use-camera.ts` | new | Hook quản `MediaStream`, `navigator.mediaDevices.enumerateDevices` (lọc videoinput), `deviceId` chọn, `capture(): Promise<Blob>` vẽ frame ra canvas rồi `canvas.toBlob` (image/jpeg). Cleanup stop tracks khi unmount hoặc đổi device |
| `camera-view.tsx` | new | Selector camera (dropdown deviceId) + `<video autoplay muted playsinline>` preview + nút Chụp. Nhận `useCamera` state |
| `infer-capture.ts` | new | `postInfer(blob: Blob, direction: "in"|"out", captureId: string, lane?: string): Promise<CaptureResponse>` dùng `AXIOS_INSTANCE.post("/captures/infer", FormData)`. FormData fields: `capture_id`, `direction`, `lane?`, `image` (Blob). Token Bearer tự gắn qua interceptor |
| `decision-panel.tsx` | mở rộng | Giữ logic hiện có (review_state, sửa biển, confirm entry/exit, candidates, nhập tay). Thêm: khi `doExit` trả `outcome=completed` và `fee_amount > 0` mở `PaymentDialog`. Chip nhóm xe dùng `useVehicleGroupMap()` (mảng C) hiển thị display_name |
| `payment-dialog.tsx` | new | Modal chọn phương thức (`cash|qr|ewallet`, phím 1/2/3), `POST /payments {session_id, amount, method, kind:"payment"}`, mở `Receipt`. Đóng bằng Esc |
| `receipt.tsx` | new | Biên lai HTML in được: biển số, giờ vào, giờ ra, thời lượng, phí, phương thức, mã phiên. Nút In gọi `window.print()` |
| `use-gate-shortcuts.ts` | new | Bind scheme phím (mục 5) theo `activePanel` và context (dialog mở hay không). Bỏ qua khi focus trong input trừ phím dành riêng |
| `use-gate-socket.ts` | sửa | Giữ WS + polling. Trả thêm cách lấy capture mới nhất theo `direction` để gate-page phân về panel (ví dụ `capturesByDirection: { in: GateCapture|null, out: GateCapture|null }`) |
| `gate-kpis.tsx` | xóa | Dead code từ mảng A (đã bỏ render), dọn cùng test liên quan nếu có |

## 5. Phím tắt

**Toàn cục**

| Phím | Hành động |
|---|---|
| `1` / `2` | Focus panel VÀO / RA (chế độ chia đôi); panel active viền nổi |
| `?` | Bật/tắt overlay bảng phím tắt |

**Panel đang focus**

| Phím | Hành động |
|---|---|
| `Space` | Chụp khung hình hiện tại gửi `/captures/infer` |
| `Enter` | Xác nhận (VÀO nếu panel vào, RA nếu panel ra) |
| `E` | Nhảy vào ô sửa biển |
| `M` | Nhập tay hoàn toàn |
| `Esc` | Hủy/xóa kết quả panel hiện tại |

**Dialog thu tiền khi ra (modal, context riêng)**

| Phím | Hành động |
|---|---|
| `1`/`2`/`3` | Chọn phương thức: tiền mặt / QR / ví |
| `Enter` | Xác nhận thu tiền + hiện biên lai |
| `Esc` | Đóng dialog |

`1`/`2` là contextual: dialog thu tiền mở thì chọn phương thức, ngoài dialog thì focus panel.

## 6. Luồng capture webcam

1. Chọn camera mỗi panel (`enumerateDevices`, lọc `videoinput`).
2. Preview `getUserMedia({ video: { deviceId } })`.
3. `Space` hoặc nút Chụp: `useCamera.capture()` grab frame ra canvas, `toBlob` (image/jpeg).
4. `postInfer(blob, panel.direction, uuid())` gửi `/captures/infer`.
5. `CaptureResponse` đẩy vào panel qua `onCaptured`; `DecisionPanel` điều khiển xác nhận.

Lỗi camera (không quyền, không thiết bị): panel hiện thông báo và vẫn cho nút "Nhập tay hoàn toàn" (đường lùi bất biến từ spec sản phẩm).

## 7. WS routing

`useGateSocket` giữ WS push + polling fallback (không đổi cơ chế). Gate-page phân capture theo `direction`: capture `direction=in` về panel VÀO, `direction=out` về panel RA. Panel hiển thị capture mới nhất cho hướng đó (webcam hoặc WS, cái mới hơn theo thứ tự nhận).

## 8. Luồng thu tiền khi ra

1. `DecisionPanel.doExit` gọi `POST /sessions/exit` trả `ExitResult`.
2. `outcome=suggest` (nhiều ứng viên): giữ UI chọn phiên hiện có.
3. `outcome=completed`:
   * `session.fee_amount > 0`: mở `PaymentDialog(session_id, amount=fee_amount)`. Chọn phương thức, `POST /payments {session_id, amount, method, kind:"payment"}` (service tự nối ca trực đang mở), rồi mở `Receipt` in được.
   * `session.fee_amount == 0`: bỏ dialog, toast "Đã xác nhận RA (miễn phí)".
4. `outcome=disputed`: giữ UI tranh chấp hiện có.

Refund và điều chỉnh ngoài phạm vi (mảng F).

## 9. Backend

Không đổi. Dùng lại:
* `POST /captures/infer` (auth `get_current_user`, staff trở lên; nhận `capture_id`, `direction`, `lane?`, `image`).
* `POST /sessions/exit` trả `ExitResult` (fee tính sẵn qua `compute_fee`).
* `POST /payments` (`record_payment` tự nối ca trực đang mở).

Không thêm endpoint, không đổi schema.

## 10. Testing

Frontend vitest (`src/frontend`):
* `use-camera`: mock `navigator.mediaDevices.getUserMedia` và `enumerateDevices`; `capture()` trả Blob.
* `infer-capture`: `postInfer` gửi FormData đúng field, trả `CaptureResponse` (mock axios).
* `payment-dialog`: chọn phương thức bằng phím 1/2/3, gọi `POST /payments` đúng payload, mở receipt.
* `use-gate-shortcuts`: map phím sang hành động theo active panel và context dialog.
* `gate-page`: render đúng theo `layoutMode` (split 2 panel, in/out 1 panel); `1`/`2` đổi active panel.
* `receipt`: render đủ trường, nút In gọi `window.print` (mock).

Không có test backend mới (backend không đổi).

## 11. Tiêu chí chấp nhận

* Một nhân viên vận hành được cả VÀO và RA ở chế độ chia đôi, chụp và xác nhận hoàn toàn bằng bàn phím, không cần chuột.
* Chụp từ webcam gửi `/captures/infer` và nhận kết quả nhận dạng; ô sửa biển luôn hiện; nút nhập tay hoàn toàn luôn có.
* Khi ra fee > 0 thu tiền được (chọn phương thức), in được biên lai; fee = 0 xác nhận ra không cần thu.
* Chip nhóm xe hiển thị display_name (không lộ code gạch dưới), dùng lookup mảng C.
* Màn cổng không lộ KPI, doanh thu, lưu lượng.
* Layout chuyển được giữa chia đôi, chỉ vào, chỉ ra; lựa chọn được nhớ.
* Toàn bộ suite test frontend pass.

## 12. Ngoài phạm vi mảng B

* Refund, điều chỉnh, đối soát cuối ca (mảng F).
* Tra cứu partial biển số (mảng D).
* Thống kê (mảng E).
* Nhiều camera vật lý thật, đầu đọc QR, máy in vé vật lý (chỉ mô phỏng webcam/WS + biên lai in trình duyệt).
* Giá theo khung giờ (backlog mảng C).
