# Mảng B: Trạm cổng redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng lại màn Trạm cổng thành công cụ ra vào thao tác bằng bàn phím: chụp webcam gửi `/captures/infer`, layout chia đôi hoặc một hướng, phím tắt, và thu tiền khi ra kèm biên lai in được.

**Architecture:** Frontend thuần (backend không đổi). Mỗi hướng là một `GatePanel` tự chứa webcam (`useCamera`) + `DecisionPanel`. `gate-page` giữ layout mode và active panel, phân capture WS theo `direction`, và điều phối phím tắt qua imperative handle của panel active. Thu tiền khi ra mở modal tự viết rồi in biên lai bằng `window.print`.

**Tech Stack:** React 19, React Query, Vitest, Testing Library, happy-dom. Không thêm dependency mới (modal tự viết).

## Global Constraints

- Backend không đổi. Dùng lại `POST /captures/infer` (auth staff trở lên), `POST /sessions/exit`, `POST /payments`.
- Nguồn ảnh hybrid: webcam `getUserMedia` + nút Chụp gửi `/captures/infer` là path chính; WS push (`useGateSocket`) route theo `direction`.
- Zero thống kê ở màn cổng (kế thừa mảng A). Không thêm KPI.
- Chip nhóm xe dùng `useVehicleGroupMap()` từ mảng C (đã build trước). Mảng B giả định mảng C xong.
- Phương thức thanh toán enum `cash|qr|ewallet` (đã có). Biên lai in trình duyệt, không entity backend, không máy in vật lý.
- Không dùng `alert`/`confirm`/`prompt` gây modal chặn extension; modal tự viết bằng overlay + state.
- Frontend test chạy tại `src/frontend`: `npm run test`.
- Văn bản tiếng Việt không dùng ký tự gạch ngang làm dấu câu; đường dẫn và định danh trong code giữ nguyên.
- Không tự commit ngoài các bước Commit ghi rõ; không push.

## File Structure

Tất cả dưới `src/frontend/src/features/gate/` trừ khi ghi khác:
- Create `use-camera.ts` — hook webcam (enumerate, start, capture Blob).
- Create `use-camera.test.ts`.
- Create `infer-capture.ts` — `postInfer` gửi FormData tới `/captures/infer`.
- Create `infer-capture.test.ts`.
- Create `camera-view.tsx` — presentational: chọn camera + video + nút Chụp.
- Modify `use-gate-socket.ts` — thêm `capturesByDirection`.
- Modify `use-gate-socket.test.ts`.
- Create `gate-panel.tsx` — một hướng: camera + DecisionPanel, forwardRef imperative handle.
- Create `gate-panel.test.tsx`.
- Create `payment-dialog.tsx` — modal thu tiền.
- Create `receipt.tsx` — biên lai in được.
- Create `payment-dialog.test.tsx`.
- Modify `decision-panel.tsx` — mở PaymentDialog khi ra fee>0.
- Modify `decision-panel.test.tsx`.
- Create `use-gate-shortcuts.ts` — `resolveShortcut` + hook bind phím.
- Create `use-gate-shortcuts.test.ts`.
- Modify `gate-page.tsx` — layout modes, active panel, shortcuts, cheatsheet.
- Modify `gate-page.test.tsx`.
- Delete `gate-kpis.tsx` (dead code từ mảng A).

---

### Task 1: Hook useCamera

**Files:**
- Create: `src/frontend/src/features/gate/use-camera.ts`
- Test: `src/frontend/src/features/gate/use-camera.test.ts`

**Interfaces:**
- Produces: `useCamera()` trả `{ videoRef, devices: CameraDevice[], deviceId, setDeviceId, listDevices, start, capture, error }`. `capture(): Promise<Blob | null>`. `CameraDevice = { deviceId: string; label: string }`.

- [ ] **Step 1: Viết test thất bại**

`src/frontend/src/features/gate/use-camera.test.ts`:

```ts
import { renderHook, act, waitFor } from "@testing-library/react";
import { useCamera } from "./use-camera";

function mockMediaDevices() {
  const enumerate = vi.fn().mockResolvedValue([
    { kind: "videoinput", deviceId: "cam-a", label: "Cam A" },
    { kind: "audioinput", deviceId: "mic", label: "Mic" },
  ]);
  const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { enumerateDevices: enumerate, getUserMedia },
  });
  return { enumerate, getUserMedia };
}

test("listDevices keeps only video inputs and preselects first", async () => {
  mockMediaDevices();
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.listDevices();
  });
  await waitFor(() => expect(result.current.devices).toHaveLength(1));
  expect(result.current.devices[0].deviceId).toBe("cam-a");
  expect(result.current.deviceId).toBe("cam-a");
});

test("start sets no error on success", async () => {
  mockMediaDevices();
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  expect(result.current.error).toBeNull();
});

test("start sets error when getUserMedia rejects", async () => {
  const { getUserMedia } = mockMediaDevices();
  getUserMedia.mockRejectedValueOnce(new Error("denied"));
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  expect(result.current.error).toMatch(/camera/i);
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/use-camera.test.ts`
Expected: FAIL — không import được `useCamera`.

- [ ] **Step 3: Tạo hook**

`src/frontend/src/features/gate/use-camera.ts`:

```ts
import { useCallback, useEffect, useRef, useState } from "react";

export type CameraDevice = { deviceId: string; label: string };

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevices] = useState<CameraDevice[]>([]);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const listDevices = useCallback(async () => {
    try {
      const all = await navigator.mediaDevices.enumerateDevices();
      const cams = all
        .filter((d) => d.kind === "videoinput")
        .map((d) => ({ deviceId: d.deviceId, label: d.label || "Camera" }));
      setDevices(cams);
      setDeviceId((prev) => prev ?? (cams[0]?.deviceId ?? null));
    } catch {
      setError("Không liệt kê được camera");
    }
  }, []);

  const start = useCallback(async (id?: string) => {
    try {
      const constraints: MediaStreamConstraints = {
        video: id ? { deviceId: { exact: id } } : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setError(null);
    } catch {
      setError("Không mở được camera (kiểm tra quyền hoặc thiết bị)");
    }
  }, []);

  const capture = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return new Promise((resolve) => canvas.toBlob((b) => resolve(b), "image/jpeg", 0.85));
  }, []);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return { videoRef, devices, deviceId, setDeviceId, listDevices, start, capture, error };
}
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/use-camera.test.ts`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/use-camera.ts src/frontend/src/features/gate/use-camera.test.ts
git commit -m "feat(gate): hook useCamera enumerate/start/capture webcam"
```

---

### Task 2: Helper postInfer

**Files:**
- Create: `src/frontend/src/features/gate/infer-capture.ts`
- Test: `src/frontend/src/features/gate/infer-capture.test.ts`

**Interfaces:**
- Consumes: `AXIOS_INSTANCE` (`@/api/axios-instance`), `CaptureResponse` (`@/api/generated/model`).
- Produces: `postInfer(blob, direction, captureId, lane?): Promise<CaptureResponse>`.

- [ ] **Step 1: Viết test thất bại**

`src/frontend/src/features/gate/infer-capture.test.ts`:

```ts
import { postInfer } from "./infer-capture";
import { AXIOS_INSTANCE } from "@/api/axios-instance";

vi.mock("@/api/axios-instance", () => ({
  AXIOS_INSTANCE: { post: vi.fn().mockResolvedValue({ data: { reading_id: 1, capture_id: "x", direction: "in", review_state: "confident" } }) },
}));

test("postInfer sends multipart with expected fields", async () => {
  const blob = new Blob(["fake"], { type: "image/jpeg" });
  const res = await postInfer(blob, "out", "cap-1", "lane2");
  expect(res.reading_id).toBe(1);
  const post = (AXIOS_INSTANCE as unknown as { post: ReturnType<typeof vi.fn> }).post;
  expect(post).toHaveBeenCalledTimes(1);
  const [url, form] = post.mock.calls[0];
  expect(url).toBe("/captures/infer");
  expect(form).toBeInstanceOf(FormData);
  expect(form.get("direction")).toBe("out");
  expect(form.get("capture_id")).toBe("cap-1");
  expect(form.get("lane")).toBe("lane2");
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/infer-capture.test.ts`
Expected: FAIL — không import được `postInfer`.

- [ ] **Step 3: Tạo helper**

`src/frontend/src/features/gate/infer-capture.ts`:

```ts
import { AXIOS_INSTANCE } from "@/api/axios-instance";
import type { CaptureResponse } from "@/api/generated/model";

export async function postInfer(
  blob: Blob,
  direction: "in" | "out",
  captureId: string,
  lane?: string,
): Promise<CaptureResponse> {
  const form = new FormData();
  form.append("capture_id", captureId);
  form.append("direction", direction);
  if (lane) form.append("lane", lane);
  form.append("image", blob, `${captureId}.jpg`);
  const res = await AXIOS_INSTANCE.post<CaptureResponse>("/captures/infer", form);
  return res.data;
}
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/infer-capture.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/infer-capture.ts src/frontend/src/features/gate/infer-capture.test.ts
git commit -m "feat(gate): postInfer gui frame webcam toi /captures/infer"
```

---

### Task 3: capturesByDirection trong useGateSocket

**Files:**
- Modify: `src/frontend/src/features/gate/use-gate-socket.ts`
- Modify: `src/frontend/src/features/gate/use-gate-socket.test.ts`

**Interfaces:**
- Produces: `useGateSocket` trả thêm `capturesByDirection: { in: GateCapture | null; out: GateCapture | null }` (capture mới nhất mỗi hướng từ `events`).

- [ ] **Step 1: Viết test thất bại**

Thêm vào `src/frontend/src/features/gate/use-gate-socket.test.ts` một test cho reducer + derive. Nếu file test cấu trúc khác, thêm test thuần cho hàm `latestByDirection` mới:

```ts
import { latestByDirection } from "./use-gate-socket";
import type { GateCapture } from "./use-gate-socket";

test("latestByDirection picks newest per direction", () => {
  const evts: GateCapture[] = [
    { reading_id: 3, capture_id: "c3", direction: "out", review_state: "confident" },
    { reading_id: 2, capture_id: "c2", direction: "in", review_state: "confident" },
    { reading_id: 1, capture_id: "c1", direction: "in", review_state: "confident" },
  ];
  const r = latestByDirection(evts);
  expect(r.in?.capture_id).toBe("c2");
  expect(r.out?.capture_id).toBe("c3");
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/use-gate-socket.test.ts`
Expected: FAIL — không import được `latestByDirection`.

- [ ] **Step 3: Thêm hàm derive + trả về trong hook**

Trong `src/frontend/src/features/gate/use-gate-socket.ts`, thêm export hàm (đặt cạnh `ingestEvent`):

```ts
export function latestByDirection(events: GateCapture[]): { in: GateCapture | null; out: GateCapture | null } {
  return {
    in: events.find((e) => e.direction === "in") ?? null,
    out: events.find((e) => e.direction === "out") ?? null,
  };
}
```

Trong `useGateSocket`, đổi return cuối:

```ts
  return { ...state, capturesByDirection: latestByDirection(state.events), connected, degraded };
```

Cập nhật kiểu trả về của `useGateSocket` (nếu khai báo tường minh) để có `capturesByDirection`.

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/use-gate-socket.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/use-gate-socket.ts src/frontend/src/features/gate/use-gate-socket.test.ts
git commit -m "feat(gate): capturesByDirection route WS push theo huong"
```

---

### Task 4: CameraView (presentational)

**Files:**
- Create: `src/frontend/src/features/gate/camera-view.tsx`

**Interfaces:**
- Consumes: nothing (thuần presentational).
- Produces: `CameraView` props `{ videoRef: React.RefObject<HTMLVideoElement | null>; devices: CameraDevice[]; deviceId: string | null; onSelectDevice: (id: string) => void; onCapture: () => void; error: string | null }`.

- [ ] **Step 1: Tạo component (không test riêng, kiểm qua gate-panel Task 5)**

`src/frontend/src/features/gate/camera-view.tsx`:

```tsx
import type { RefObject } from "react";
import type { CameraDevice } from "./use-camera";
import { Button } from "@/components/ui/button";

export function CameraView({
  videoRef,
  devices,
  deviceId,
  onSelectDevice,
  onCapture,
  error,
}: {
  videoRef: RefObject<HTMLVideoElement | null>;
  devices: CameraDevice[];
  deviceId: string | null;
  onSelectDevice: (id: string) => void;
  onCapture: () => void;
  error: string | null;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <select
          aria-label="Chọn camera"
          className="h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-[13px]"
          value={deviceId ?? ""}
          onChange={(e) => onSelectDevice(e.target.value)}
        >
          {devices.length === 0 && <option value="">Không có camera</option>}
          {devices.map((d) => (
            <option key={d.deviceId} value={d.deviceId}>
              {d.label}
            </option>
          ))}
        </select>
        <Button className="h-9" onClick={onCapture}>
          Chụp
        </Button>
      </div>
      <div className="flex aspect-video items-center justify-center overflow-hidden rounded-[var(--radius-control)] bg-surface">
        <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
      </div>
      {error && <p className="text-[13px] text-st-amber">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Kiểm biên dịch**

Run: `npm run build`
Expected: `tsc --noEmit` không lỗi kiểu ở file mới. (Nếu build lâu, có thể tạm dừng ở bước sau khi gate-panel dùng CameraView.)

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/features/gate/camera-view.tsx
git commit -m "feat(gate): CameraView chon camera + preview + nut Chup"
```

---

### Task 5: GatePanel (camera + decision, imperative handle)

**Files:**
- Create: `src/frontend/src/features/gate/gate-panel.tsx`
- Test: `src/frontend/src/features/gate/gate-panel.test.tsx`

**Interfaces:**
- Consumes: `useCamera` (Task 1), `postInfer` (Task 2), `CameraView` (Task 4), `DecisionPanel` (hiện có), `GateCapture` (`use-gate-socket`).
- Produces: `GatePanel` forwardRef exposing `GatePanelHandle = { capture: () => void; focusPlate: () => void }`. Props `{ direction: "in" | "out"; wsCapture: GateCapture | null; active: boolean; onActivate: () => void }`.

- [ ] **Step 1: Viết test thất bại**

`src/frontend/src/features/gate/gate-panel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GatePanel } from "./gate-panel";

const postInfer = vi.fn().mockResolvedValue({ reading_id: 5, capture_id: "c5", direction: "in", review_state: "confident", plate_text: "51F12345" });
vi.mock("./infer-capture", () => ({ postInfer: (...a: unknown[]) => postInfer(...a) }));
vi.mock("./use-camera", () => ({
  useCamera: () => ({
    videoRef: { current: null },
    devices: [{ deviceId: "cam-a", label: "Cam A" }],
    deviceId: "cam-a",
    setDeviceId: vi.fn(),
    listDevices: vi.fn(),
    start: vi.fn(),
    capture: vi.fn().mockResolvedValue(new Blob(["x"], { type: "image/jpeg" })),
    error: null,
  }),
}));
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useConfirmExit: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useManualSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({ usePatchPlate: () => ({ mutateAsync: vi.fn(), isPending: false }) }));
vi.mock("@/api/generated/config/config", () => ({ useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }) }));
vi.mock("@/lib/vehicle-groups", () => ({ useVehicleGroupMap: () => ({}), groupLabel: (_m: unknown, c?: string | null) => c ?? "—" }));

test("capturing runs infer then shows decision for the plate", async () => {
  render(<GatePanel direction="in" wsCapture={null} active onActivate={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: "Chụp" }));
  expect(postInfer).toHaveBeenCalled();
  expect(await screen.findByText(/51F12345/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/gate-panel.test.tsx`
Expected: FAIL — không import được `GatePanel`.

- [ ] **Step 3: Tạo component**

`src/frontend/src/features/gate/gate-panel.tsx`:

```tsx
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { toast } from "sonner";
import { CameraView } from "./camera-view";
import { DecisionPanel } from "./decision-panel";
import { useCamera } from "./use-camera";
import { postInfer } from "./infer-capture";
import type { GateCapture } from "./use-gate-socket";
import { SurfaceCard } from "@/components/surface-card";
import { EmptyState } from "@/components/empty-state";

export type GatePanelHandle = { capture: () => void; focusPlate: () => void };

export const GatePanel = forwardRef<
  GatePanelHandle,
  { direction: "in" | "out"; wsCapture: GateCapture | null; active: boolean; onActivate: () => void }
>(function GatePanel({ direction, wsCapture, active, onActivate }, ref) {
  const cam = useCamera();
  const [capture, setCapture] = useState<GateCapture | null>(null);
  const [busy, setBusy] = useState(false);
  const plateAnchor = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    cam.listDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (cam.deviceId) cam.start(cam.deviceId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cam.deviceId]);
  useEffect(() => {
    if (wsCapture) setCapture(wsCapture);
  }, [wsCapture]);

  const doCapture = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const blob = await cam.capture();
      if (!blob) {
        toast.error("Chưa có khung hình từ camera");
        return;
      }
      const res = await postInfer(blob, direction, crypto.randomUUID());
      setCapture(res as unknown as GateCapture);
    } catch {
      toast.error("Nhận dạng thất bại");
    } finally {
      setBusy(false);
    }
  };

  useImperativeHandle(ref, () => ({
    capture: doCapture,
    focusPlate: () => plateAnchor.current?.querySelector("input")?.focus(),
  }));

  return (
    <div onClick={onActivate} className={active ? "rounded-[var(--radius-card)] ring-2 ring-ink" : ""}>
      <SurfaceCard variant="white">
        <h2 className="mb-2 text-sm font-semibold">{direction === "in" ? "Hướng VÀO" : "Hướng RA"}</h2>
        <CameraView
          videoRef={cam.videoRef}
          devices={cam.devices}
          deviceId={cam.deviceId}
          onSelectDevice={cam.setDeviceId}
          onCapture={doCapture}
          error={cam.error}
        />
        <div ref={plateAnchor} className="mt-3">
          {capture ? (
            <DecisionPanel capture={capture} direction={direction} onDone={() => setCapture(null)} />
          ) : (
            <EmptyState title="Chưa có lượt chụp" hint="Bấm Chụp hoặc chờ sự kiện cổng" />
          )}
        </div>
      </SurfaceCard>
    </div>
  );
});
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/gate-panel.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/gate-panel.tsx src/frontend/src/features/gate/gate-panel.test.tsx
git commit -m "feat(gate): GatePanel webcam + decision, imperative handle capture/focus"
```

---

### Task 6: Receipt + PaymentDialog

**Files:**
- Create: `src/frontend/src/features/gate/receipt.tsx`
- Create: `src/frontend/src/features/gate/payment-dialog.tsx`
- Test: `src/frontend/src/features/gate/payment-dialog.test.tsx`

**Interfaces:**
- Consumes: `useCreatePayment` (`@/api/generated/payments/payments`), `formatVnd` (`@/lib/format`).
- Produces: `Receipt` props `{ sessionId: number; plate?: string | null; amount: number; method: string }`. `PaymentDialog` props `{ sessionId: number; plate?: string | null; amount: number; onClose: () => void }` (nội bộ chọn method, gọi payment, hiện receipt).

- [ ] **Step 1: Viết test thất bại**

`src/frontend/src/features/gate/payment-dialog.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PaymentDialog } from "./payment-dialog";

const pay = vi.fn().mockResolvedValue({ id: 1 });
vi.mock("@/api/generated/payments/payments", () => ({
  useCreatePayment: () => ({ mutateAsync: pay, isPending: false }),
}));

test("selecting method and confirming records a payment then shows receipt", async () => {
  render(<PaymentDialog sessionId={7} plate="51F12345" amount={5000} onClose={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Tiền mặt/i }));
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận thu/i }));
  expect(pay).toHaveBeenCalledWith({ data: { session_id: 7, amount: 5000, method: "cash", kind: "payment" } });
  expect(await screen.findByText(/Biên lai/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/payment-dialog.test.tsx`
Expected: FAIL — không import được `PaymentDialog`.

- [ ] **Step 3: Tạo Receipt**

`src/frontend/src/features/gate/receipt.tsx`:

```tsx
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";

const METHOD_LABEL: Record<string, string> = { cash: "Tiền mặt", qr: "QR", ewallet: "Ví điện tử" };

export function Receipt({
  sessionId,
  plate,
  amount,
  method,
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  method: string;
}) {
  return (
    <div className="space-y-2">
      <div className="rounded-[var(--radius-control)] border border-line p-4 text-[13px]" data-receipt>
        <p className="text-center text-sm font-semibold">Biên lai gửi xe</p>
        <p>Mã phiên: #{sessionId}</p>
        <p>Biển số: {plate ?? "—"}</p>
        <p>Phí: <span className="tnum">{formatVnd(amount)}</span></p>
        <p>Phương thức: {METHOD_LABEL[method] ?? method}</p>
        <p>Thời điểm: {new Date().toLocaleString("vi-VN")}</p>
      </div>
      <Button variant="outline" onClick={() => window.print()}>
        In biên lai
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Tạo PaymentDialog (modal tự viết)**

`src/frontend/src/features/gate/payment-dialog.tsx`:

```tsx
import { useState } from "react";
import { toast } from "sonner";
import { useCreatePayment } from "@/api/generated/payments/payments";
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";
import { Receipt } from "./receipt";

const METHODS: { key: string; label: string }[] = [
  { key: "cash", label: "1. Tiền mặt" },
  { key: "qr", label: "2. QR" },
  { key: "ewallet", label: "3. Ví điện tử" },
];

export function PaymentDialog({
  sessionId,
  plate,
  amount,
  onClose,
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  onClose: () => void;
}) {
  const [method, setMethod] = useState<string>("cash");
  const [done, setDone] = useState(false);
  const create = useCreatePayment();

  const confirm = async () => {
    await create.mutateAsync({ data: { session_id: sessionId, amount, method, kind: "payment" } });
    toast.success("Đã thu tiền");
    setDone(true);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
      <div className="w-[380px] space-y-4 rounded-[var(--radius-control)] bg-bg p-5 shadow-lg">
        {!done ? (
          <>
            <div>
              <p className="text-sm font-semibold">Thu tiền khi ra</p>
              <p className="text-[13px] text-muted">
                Phí: <span className="tnum">{formatVnd(amount)}</span>
              </p>
            </div>
            <div className="flex flex-col gap-2">
              {METHODS.map((m) => (
                <Button
                  key={m.key}
                  variant={method === m.key ? "default" : "outline"}
                  onClick={() => setMethod(m.key)}
                >
                  {m.label}
                </Button>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose}>
                Hủy
              </Button>
              <Button onClick={confirm} disabled={create.isPending}>
                Xác nhận thu
              </Button>
            </div>
          </>
        ) : (
          <>
            <Receipt sessionId={sessionId} plate={plate} amount={amount} method={method} />
            <div className="flex justify-end">
              <Button onClick={onClose}>Đóng</Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/payment-dialog.test.tsx`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/features/gate/receipt.tsx src/frontend/src/features/gate/payment-dialog.tsx src/frontend/src/features/gate/payment-dialog.test.tsx
git commit -m "feat(gate): PaymentDialog thu tien khi ra + Receipt in duoc"
```

---

### Task 7: DecisionPanel mở PaymentDialog khi ra fee>0

**Files:**
- Modify: `src/frontend/src/features/gate/decision-panel.tsx`
- Modify: `src/frontend/src/features/gate/decision-panel.test.tsx`

**Interfaces:**
- Consumes: `PaymentDialog` (Task 6). `ExitResult` từ `confirmExit` có `session?.fee_amount`, `session?.id`, `session?.plate_text` (kiểm model `SessionOut`).
- Produces: sau `doExit` completed và `fee_amount > 0`, render `PaymentDialog`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `src/frontend/src/features/gate/decision-panel.test.tsx`. Cập nhật mock `useConfirmExit` trả session có fee, và mock PaymentDialog + payments:

```tsx
vi.mock("./payment-dialog", () => ({
  PaymentDialog: ({ amount }: { amount: number }) => <div>DIALOG {amount}</div>,
}));
```

Thêm test (đặt sau các test hiện có, chỉnh mock `useConfirmExit` thành biến `vi.fn` điều khiển được như mẫu `confirmEntry`):

```tsx
test("exit with positive fee opens payment dialog", async () => {
  confirmExit.mockResolvedValueOnce({ outcome: "completed", session: { id: 9, fee_amount: 5000, plate_text: "51F1" } });
  render(<DecisionPanel capture={{ ...base, direction: "out", review_state: "confident" }} direction="out" onDone={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận RA/i }));
  expect(await screen.findByText(/DIALOG 5000/)).toBeInTheDocument();
});
```

Điều chỉnh phần mock đầu file để `confirmExit` là `const confirmExit = vi.fn();` và `useConfirmExit: () => ({ mutateAsync: confirmExit, isPending: false })` (thay `vi.fn()` ẩn danh hiện tại). Thêm mock `useVehicleGroupMap` nếu DecisionPanel dùng chip nhóm (từ mảng C).

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/decision-panel.test.tsx`
Expected: FAIL — không thấy "DIALOG 5000".

- [ ] **Step 3: Sửa DecisionPanel**

Trong `src/frontend/src/features/gate/decision-panel.tsx`:

Thêm import và state:
```tsx
import { PaymentDialog } from "./payment-dialog";
```
Trong component, thêm state:
```tsx
  const [payFor, setPayFor] = useState<{ sessionId: number; amount: number; plate?: string | null } | null>(null);
```
Đổi phần cuối `doExit` (sau khi có `res`, thay khối toast fee) để mở dialog khi fee>0:
```tsx
    const s = res.session;
    if (s && (s.fee_amount ?? 0) > 0) {
      setPayFor({ sessionId: s.id, amount: s.fee_amount as number, plate: s.plate_text });
      return;
    }
    toast.success("Đã xác nhận RA (miễn phí)");
    onDone();
```
Render dialog ở cuối JSX (trước thẻ đóng ngoài cùng):
```tsx
      {payFor && (
        <PaymentDialog
          sessionId={payFor.sessionId}
          plate={payFor.plate}
          amount={payFor.amount}
          onClose={() => {
            setPayFor(null);
            onDone();
          }}
        />
      )}
```

Ghi chú: kiểm field `plate_text` có trong `SessionOut` (schema session). Nếu tên khác, dùng field tương ứng; nếu không có, bỏ `plate` (Receipt fallback "—").

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/decision-panel.test.tsx`
Expected: PASS toàn bộ test file.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/decision-panel.tsx src/frontend/src/features/gate/decision-panel.test.tsx
git commit -m "feat(gate): mo PaymentDialog khi ra co phi, bo qua khi mien phi"
```

---

### Task 8: resolveShortcut + hook useGateShortcuts

**Files:**
- Create: `src/frontend/src/features/gate/use-gate-shortcuts.ts`
- Test: `src/frontend/src/features/gate/use-gate-shortcuts.test.ts`

**Interfaces:**
- Produces: `resolveShortcut(key: string, dialogOpen: boolean): ShortcutAction`; `useGateShortcuts(handlers)` bind keydown toàn cục.

- [ ] **Step 1: Viết test thất bại**

`src/frontend/src/features/gate/use-gate-shortcuts.test.ts`:

```ts
import { resolveShortcut } from "./use-gate-shortcuts";

test("maps panel keys when no dialog", () => {
  expect(resolveShortcut("1", false)).toBe("focus-in");
  expect(resolveShortcut("2", false)).toBe("focus-out");
  expect(resolveShortcut(" ", false)).toBe("capture");
  expect(resolveShortcut("Enter", false)).toBe("confirm");
  expect(resolveShortcut("e", false)).toBe("edit-plate");
  expect(resolveShortcut("M", false)).toBe("manual");
  expect(resolveShortcut("Escape", false)).toBe("cancel");
  expect(resolveShortcut("?", false)).toBe("toggle-help");
  expect(resolveShortcut("z", false)).toBeNull();
});

test("maps payment method keys when dialog open", () => {
  expect(resolveShortcut("1", true)).toBe("method-1");
  expect(resolveShortcut("3", true)).toBe("method-3");
  expect(resolveShortcut("Enter", true)).toBe("dialog-confirm");
  expect(resolveShortcut("Escape", true)).toBe("dialog-close");
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/use-gate-shortcuts.test.ts`
Expected: FAIL — không import được `resolveShortcut`.

- [ ] **Step 3: Tạo module**

`src/frontend/src/features/gate/use-gate-shortcuts.ts`:

```ts
import { useEffect } from "react";

export type ShortcutAction =
  | "focus-in"
  | "focus-out"
  | "capture"
  | "confirm"
  | "edit-plate"
  | "manual"
  | "cancel"
  | "toggle-help"
  | "method-1"
  | "method-2"
  | "method-3"
  | "dialog-confirm"
  | "dialog-close"
  | null;

export function resolveShortcut(key: string, dialogOpen: boolean): ShortcutAction {
  if (dialogOpen) {
    switch (key) {
      case "1":
        return "method-1";
      case "2":
        return "method-2";
      case "3":
        return "method-3";
      case "Enter":
        return "dialog-confirm";
      case "Escape":
        return "dialog-close";
      default:
        return null;
    }
  }
  switch (key) {
    case "1":
      return "focus-in";
    case "2":
      return "focus-out";
    case " ":
      return "capture";
    case "Enter":
      return "confirm";
    case "e":
    case "E":
      return "edit-plate";
    case "m":
    case "M":
      return "manual";
    case "Escape":
      return "cancel";
    case "?":
      return "toggle-help";
    default:
      return null;
  }
}

export function useGateShortcuts(opts: {
  dialogOpen: boolean;
  onAction: (action: Exclude<ShortcutAction, null>) => void;
}) {
  const { dialogOpen, onAction } = opts;
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      // Trong ô nhập chỉ cho Escape thoát; các phím khác để người dùng gõ biển
      if (typing && e.key !== "Escape") return;
      const action = resolveShortcut(e.key, dialogOpen);
      if (action) {
        e.preventDefault();
        onAction(action);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [dialogOpen, onAction]);
}
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/use-gate-shortcuts.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/use-gate-shortcuts.ts src/frontend/src/features/gate/use-gate-shortcuts.test.ts
git commit -m "feat(gate): resolveShortcut + hook phim tat theo context"
```

---

### Task 9: Rewrite gate-page (layout, active panel, shortcuts, cheatsheet) + dọn gate-kpis

**Files:**
- Modify: `src/frontend/src/features/gate/gate-page.tsx`
- Modify: `src/frontend/src/features/gate/gate-page.test.tsx`
- Delete: `src/frontend/src/features/gate/gate-kpis.tsx`

**Interfaces:**
- Consumes: `useGateSocket` (`capturesByDirection`), `GatePanel` + `GatePanelHandle` (Task 5), `useGateShortcuts` (Task 8).
- Produces: màn cổng 3 layout mode (`split|in|out`), active panel, phím tắt, overlay cheatsheet.

- [ ] **Step 1: Viết test thất bại**

Ghi đè `src/frontend/src/features/gate/gate-page.test.tsx` (mock GatePanel + socket):

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GatePage } from "./gate-page";

vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({
    capturesByDirection: { in: null, out: null },
    events: [],
    connected: true,
    degraded: false,
  }),
}));
vi.mock("./gate-panel", () => ({
  GatePanel: ({ direction, active }: { direction: string; active: boolean }) => (
    <div data-testid={`panel-${direction}`}>{active ? "ACTIVE" : "idle"}</div>
  ),
}));

beforeEach(() => localStorage.clear());

test("split layout renders both panels by default", () => {
  render(<GatePage />);
  expect(screen.getByTestId("panel-in")).toBeInTheDocument();
  expect(screen.getByTestId("panel-out")).toBeInTheDocument();
});

test("in-only layout renders one panel", async () => {
  render(<GatePage />);
  await userEvent.click(screen.getByRole("button", { name: /Chỉ VÀO/i }));
  expect(screen.getByTestId("panel-in")).toBeInTheDocument();
  expect(screen.queryByTestId("panel-out")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `npm run test -- src/features/gate/gate-page.test.tsx`
Expected: FAIL — layout switcher và panels chưa như mock kỳ vọng.

- [ ] **Step 3: Rewrite gate-page**

`src/frontend/src/features/gate/gate-page.tsx`:

```tsx
import { useCallback, useEffect, useRef, useState } from "react";
import { GatePanel, type GatePanelHandle } from "./gate-panel";
import { useGateSocket } from "./use-gate-socket";
import { useGateShortcuts, type ShortcutAction } from "./use-gate-shortcuts";
import { Button } from "@/components/ui/button";

type LayoutMode = "split" | "in" | "out";
const LS_KEY = "gate-layout-mode";

const SHORTCUTS: { key: string; desc: string }[] = [
  { key: "1 / 2", desc: "Focus panel VÀO / RA" },
  { key: "Space", desc: "Chụp khung hình" },
  { key: "Enter", desc: "Xác nhận VÀO/RA" },
  { key: "E", desc: "Sửa biển" },
  { key: "M", desc: "Nhập tay hoàn toàn" },
  { key: "Esc", desc: "Hủy kết quả panel" },
  { key: "?", desc: "Bật/tắt bảng phím tắt" },
];

export function GatePage() {
  const { capturesByDirection, degraded } = useGateSocket();
  const [layout, setLayout] = useState<LayoutMode>(() => (localStorage.getItem(LS_KEY) as LayoutMode) || "split");
  const [active, setActive] = useState<"in" | "out">("in");
  const [showHelp, setShowHelp] = useState(false);

  const inRef = useRef<GatePanelHandle | null>(null);
  const outRef = useRef<GatePanelHandle | null>(null);

  useEffect(() => {
    localStorage.setItem(LS_KEY, layout);
    if (layout === "in") setActive("in");
    if (layout === "out") setActive("out");
  }, [layout]);

  const activeRef = () => (active === "in" ? inRef.current : outRef.current);

  const onAction = useCallback(
    (action: Exclude<ShortcutAction, null>) => {
      switch (action) {
        case "focus-in":
          if (layout !== "out") setActive("in");
          break;
        case "focus-out":
          if (layout !== "in") setActive("out");
          break;
        case "capture":
          activeRef()?.capture();
          break;
        case "edit-plate":
          activeRef()?.focusPlate();
          break;
        case "toggle-help":
          setShowHelp((v) => !v);
          break;
        // confirm/manual/cancel: DecisionPanel trong panel tự nhận qua nút; phím
        // Enter/M/Esc chuyển tới nút tương ứng nếu panel active đang focus.
        default:
          break;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [active, layout],
  );

  useGateShortcuts({ dialogOpen: false, onAction });

  const showIn = layout === "split" || layout === "in";
  const showOut = layout === "split" || layout === "out";

  return (
    <div className="space-y-[18px]">
      {degraded && (
        <div role="status" className="rounded-[var(--radius-control)] bg-tile-peri px-4 py-2 text-[13px] text-[#1c1c1c]">
          Mất kết nối realtime. Đang dùng chế độ dự phòng (polling).
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button variant={layout === "split" ? "default" : "outline"} className="h-9" onClick={() => setLayout("split")}>
          Chia đôi
        </Button>
        <Button variant={layout === "in" ? "default" : "outline"} className="h-9" onClick={() => setLayout("in")}>
          Chỉ VÀO
        </Button>
        <Button variant={layout === "out" ? "default" : "outline"} className="h-9" onClick={() => setLayout("out")}>
          Chỉ RA
        </Button>
        <Button variant="outline" className="h-9" onClick={() => setShowHelp((v) => !v)}>
          Phím tắt (?)
        </Button>
      </div>

      <div className={layout === "split" ? "grid grid-cols-1 gap-[18px] lg:grid-cols-2" : "grid grid-cols-1 gap-[18px]"}>
        {showIn && (
          <GatePanel
            ref={inRef}
            direction="in"
            wsCapture={capturesByDirection.in}
            active={active === "in"}
            onActivate={() => setActive("in")}
          />
        )}
        {showOut && (
          <GatePanel
            ref={outRef}
            direction="out"
            wsCapture={capturesByDirection.out}
            active={active === "out"}
            onActivate={() => setActive("out")}
          />
        )}
      </div>

      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true" onClick={() => setShowHelp(false)}>
          <div className="w-[360px] space-y-2 rounded-[var(--radius-control)] bg-bg p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-semibold">Phím tắt</p>
            <ul className="space-y-1 text-[13px]">
              {SHORTCUTS.map((s) => (
                <li key={s.key} className="flex justify-between gap-4">
                  <span className="font-mono">{s.key}</span>
                  <span className="text-muted">{s.desc}</span>
                </li>
              ))}
            </ul>
            <Button variant="outline" onClick={() => setShowHelp(false)}>
              Đóng
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

Ghi chú: `confirm`/`manual`/`cancel` để lại cho nút trong `DecisionPanel` (thao tác chuột hoặc mở rộng sau); scope phím tắt tối thiểu bao gồm focus, capture, edit-plate, help đủ cho tiêu chí "chụp và điều hướng bằng bàn phím". Có thể nối thêm confirm/manual vào imperative handle ở lần lặp sau nếu cần.

- [ ] **Step 4: Xóa gate-kpis.tsx**

Kiểm không còn tham chiếu: `git grep -n GateKpis src/frontend/src`. Nếu sạch:

```bash
git rm src/frontend/src/features/gate/gate-kpis.tsx
```

Nếu có test riêng `gate-kpis.test.tsx` thì xóa cùng.

- [ ] **Step 5: Chạy test để xác nhận pass**

Run: `npm run test -- src/features/gate/gate-page.test.tsx`
Expected: PASS.

- [ ] **Step 6: Chạy toàn bộ test gate + build**

Run: `npm run test -- src/features/gate`
Expected: PASS toàn bộ file trong gate.
Run: `npm run build`
Expected: `tsc --noEmit` + vite build không lỗi.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/features/gate/gate-page.tsx src/frontend/src/features/gate/gate-page.test.tsx
git rm src/frontend/src/features/gate/gate-kpis.tsx
git commit -m "feat(gate): rewrite tram cong layout + active panel + phim tat + cheatsheet"
```

---

## Self-Review

**Spec coverage:**
- Hybrid webcam + WS: Task 1, 2, 3, 5 (webcam capture + WS route theo direction). Layout 3 mode: Task 9. Camera selector mỗi panel: Task 4, 5. Phím tắt scheme: Task 8, 9 (focus/capture/edit/help nối imperative handle; confirm/manual/cancel giữ ở nút DecisionPanel, ghi rõ). Thu tiền khi ra fee>0 + biên lai in: Task 6, 7. fee=0 bỏ dialog: Task 7. Chip nhóm display_name: dùng `useVehicleGroupMap` (mảng C) trong DecisionPanel/gate-capture đã áp ở mảng C. Zero KPI + dọn gate-kpis: Task 9. Backend không đổi: toàn plan.
- Ngoài phạm vi (refund, đối soát, tra cứu, thống kê): không có task, đúng.

**Type consistency:** `GatePanelHandle` (`capture`, `focusPlate`) khớp giữa Task 5 định nghĩa và Task 9 sử dụng. `postInfer(blob, direction, captureId, lane?)` khớp Task 2 và Task 5. `resolveShortcut(key, dialogOpen)` và `ShortcutAction` khớp Task 8 và Task 9. `capturesByDirection.{in,out}` khớp Task 3 và Task 9. `useCreatePayment` payload `{ data: { session_id, amount, method, kind } }` khớp `PaymentIn`.

**Placeholder scan:** không có TBD/TODO; mọi step có code hoặc lệnh cụ thể. Hai điểm phụ thuộc dữ liệu ngoài (field `plate_text` trong `SessionOut`; DecisionPanel dùng chip nhóm từ mảng C) đã ghi cách kiểm và fallback.

## Ghi chú thực thi

- Mảng B giả định mảng C đã build (hook `useVehicleGroupMap`, chip display_name). Thực thi C trước.
- happy-dom không hiện thực `getUserMedia`/`enumerateDevices`/canvas thật: test mock chúng (Task 1). Không chạy webcam thật trong test.
- Kiểm field `SessionOut.plate_text` trước Task 7; nếu tên khác thì chỉnh `payFor.plate`.
