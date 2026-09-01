# Gate flow UX + correctness pass — design

Date: 2026-08-30
Branch: feat/duc-dashboard-backend
Scope: `src/frontend/src/features/gate/*` (+ small `app-shell` / keyboard wiring). No new backend endpoints.

## Problem

The gate (in/out) screen accreted features while basic input hygiene was skipped. Observed gaps:

1. No camera-connect / permission request when no stream exists; a black `<video>` and a silent "Không có camera" select.
2. A wrong recognition cannot be re-run, and plate correction is gated to `needs_review` only (`decision-panel.tsx:113`); vehicle type/color are display-only.
3. Plate / vehicle type / plate color rendered as 13px pills, too small to read at a glance.
4. Layout does not fit the viewport: two large camera panels dominate, the decision block sits below the fold, whole page scrolls.
5. Empty data still submits "Xác nhận VÀO" silently, no validation feedback.
6. Payment opens a modal dialog, a heavy context switch mid-flow.

## Goal

Optimize the screen for the real task: move vehicles through fast (target ~5 s/vehicle, UI is not the bottleneck), with correct in/out logic and full validation. One vehicle = one screen, no page scroll, keyboard-reachable. Camera is a reference thumbnail, not the star. Payment is inline.

Target device: responsive, must fit viewport height on desktop, tablet, and small kiosk.

## Operator loop (the thing being optimized)

```
Chụp (Space) → glance plate/result → Enter to confirm
  entry: done
  exit with fee: pick method (1/2/3) → Enter → receipt inline → done
```

Everything in that loop is on-screen and keyboard-driven. No modal, no scroll to reach an action.

## Backend semantics this design must respect

Verified in `src/backend/app/routers/sessions.py`:

- `confirm_entry`: plate optional. With plate → `in_lot`, `match_flag=exact`. Without plate → session created as `pending_manual`, `match_flag=None` (`sessions.py:60,80`). Plateless entry is a legitimate path, not an error.
- `confirm_exit`: needs a valid exit reading; `find_match` returns `outcome="suggest"` with candidates, or a match to complete. Fee computed on complete; missing price rule → 422 (`sessions.py:119`).
- `manual_session`: entry requires BOTH `plate_text` and `vehicle_group`, else 422 (`sessions.py:197`); exit requires `session_id`, else 422 (`sessions.py:215`).
- `PlatePatch` accepts `plate_text` only (`schemas/session.py:33`). No inline patch for vehicle_group/type/color.

## Design

### A. Camera connection state (issue 1)

`use-camera` exposes an explicit `status`: `idle | requesting | streaming | denied | no-device | error`.

- On mount, request permission once (`getUserMedia`) so device labels populate, then `listDevices`.
- `CameraView` renders the `<video>` only when `status === "streaming"`. Otherwise a placeholder card:
  - `no-device`: "Không tìm thấy camera" + `Kết nối lại` (retries list + start).
  - `denied` / `error`: message + `Cấp quyền camera` (retries `getUserMedia`).
  - `requesting`: spinner.
  - All placeholder states also expose the `Nhập tay` fallback so work never blocks on hardware.
- Device `select` shows only when devices exist.

### B. Correct + re-recognize (issue 2)

- Plate is always editable and `Lưu biển` is always available (remove the `needs_review`-only gate). Save calls `PATCH` plate; button disabled when plate empty or unchanged.
- New `Nhận lại (R)` action: re-capture a frame and re-run inference for this direction, replacing the current result. Guarded by `busy`.
- Vehicle type / group / color correction: not inline (backend patch is plate-only). Correction path is `Nhận lại` or `Nhập tay`. Documented in UI copy.

### C. Readability (issue 3)

Recognition result becomes one `Kết quả nhận dạng` block, replacing the 13px pills:

- Plate: large mono (keep `PlateField size="lg"` for edit; show large text when read-only).
- Type / Nhóm phí / Màu biển: labeled rows, value >=15px, label muted above. Màu biển shows a real color swatch next to the text.
- Warnings (invalid format, duplicate-in-lot) shown as amber inline lines, not hidden.

### D. Layout — fit viewport, invert visual weight (issue 4)

- `GatePage` root: `h-full flex flex-col`. Toolbar row fixed at top; panels region `flex-1 min-h-0`.
- Each `GatePanel`: `flex flex-col`, panel-contained scroll only (`min-h-0` + inner `overflow-auto` on the result region, never the page).
- Camera capped (`~30–40%` of panel height, `object-cover`), collapsible so it never pushes actions off-screen.
- Action bar pinned at panel bottom, always visible.
- Responsive: `lg` → split 2-col; below → single column. `Chỉ VÀO/RA` fills width. `app-shell` main is already `min-h-0 flex-1 overflow-auto`; gate page stops overflowing it (its own regions scroll instead of the page).

### E. Validation and correct logic (issue 5)

Default primary action (Enter / big confirm button):

- **Entry, plate present**: confirm normally.
- **Entry, plate empty**: primary confirm is disabled with helper text ("Cần biển số để xác nhận VÀO"). A distinct, deliberate secondary action `Vào không biển (phiên chờ)` maps to the backend `pending_manual` path. No silent empty submit; the plateless path stays available but is explicit and labeled.
- **Exit**: requires a target — a plate match or a chosen candidate. If neither, block with guidance ("Chọn phiên để nối hoặc dùng Nhập tay").
- **Manual entry**: requires `plate_text` AND `vehicle_group`; the manual UI includes a `vehicle_group` selector (default from capture when present) and validates both before submit. Fixes the latent 422 when `capture.vehicle_group` is null.
- **Manual exit**: requires a `session_id` (candidate chosen).
- **Payment**: `amount > 0`, method selected (default `cash`); confirm guarded by pending.
- **Plate save**: non-empty, changed.
- Every mutation guarded by a `busy`/pending flag to prevent double submit.
- Warn-but-allow preserved for invalid plate format and duplicate-in-lot (existing intent), shown as visible warnings.

### F. Payment inline (issue 6)

Remove the `PaymentDialog` modal. On exit-with-fee, the panel action bar swaps in place to a pay row within the same panel:

- Amount large.
- Method chips `1 Tiền mặt / 2 QR / 3 Ví`.
- `Thu & in (Enter)` confirms, then `Receipt` renders inline; `Đóng` / auto-reset returns the panel to idle.
- No overlay, no focus trap, no context switch.

### G. Keyboard wired for real (speed)

Today `Enter` / `M` / `Esc` reach the `default` branch and no-op (`gate-page.tsx:57`). Wire them:

- Extend `GatePanelHandle` with `confirm()`, `manual()`, `cancel()`, and `payMethod(n)`.
- `GatePage.onAction` routes: `Enter`→confirm/pay, `M`→manual, `Esc`→cancel, `R`→re-recognize, `1/2/3`→payment method, existing `Space`/`E`/`1`/`2`(panel focus) kept. Resolve the `1/2` collision: digits select payment method only while a pay row is open; otherwise `1/2` focus panels (current behavior).

## Out of scope

- Inline editing of vehicle type/group/color (needs backend `PlatePatch` extension).
- Any new backend endpoint or schema change.
- Changes outside the gate feature except `app-shell` height wiring and shared keyboard hook.

## Testing

- `use-camera`: status transitions (granted, denied, no-device); placeholder renders per state.
- `DecisionPanel`: confirm disabled on empty plate (entry); `Vào không biển` present and calls entry path; manual entry requires group (no 422 with null group); save-plate always available; exit blocked without target.
- Payment inline: renders in-panel, confirms, shows receipt; double-submit guarded.
- Keyboard: `Enter` confirms, `M` manual, `Esc` cancels, `R` re-recognizes, `1/2/3` pick method while pay row open.
- Layout: panels use height-fit classes; result region scrolls, page does not (class assertions).

## Success criteria

- A clean read completes in `Space, Enter` (entry) or `Space, Enter, <digit>, Enter` (paid exit), no mouse, no scroll.
- No camera → clear connect/permission prompt, work still possible via manual.
- Empty plate never confirms silently; plateless entry only via the explicit labeled action.
- One vehicle fits one viewport at desktop, tablet, and small kiosk widths.
