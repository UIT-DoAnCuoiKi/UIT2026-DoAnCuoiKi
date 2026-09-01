# Gate Flow UX + Correctness Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the gate in/out screen fast (target ~5 s/vehicle), viewport-fitting, and validated: explicit camera-connect states, always-editable plate, readable recognition block, inline payment, keyboard-driven confirm, and correct empty-plate / manual-entry validation.

**Architecture:** Frontend-only pass on `src/frontend/src/features/gate/*` plus a small `app-shell` height wiring. Break the oversized `decision-panel.tsx` into focused presentational units (`recognition-result`, `pay-row`) and keep orchestration/validation in `decision-panel`. Wire the already-defined keyboard actions (`confirm`/`manual`/`cancel`/`method-*`) through imperative handles up to `gate-page`.

**Tech Stack:** React 18, TypeScript, Tailwind (v4 token classes), TanStack Query (orval-generated hooks), Vitest + Testing Library, sonner toasts.

## Global Constraints

- No new backend endpoints or schema changes. Respect existing semantics in `src/backend/app/routers/sessions.py`.
- `PlatePatch` accepts `plate_text` only. No inline patch of vehicle_group/type/color.
- `confirm_entry` allows plateless entry (creates `pending_manual`). Plateless is a deliberate labeled path, never a silent submit.
- `manual_session` entry requires BOTH `plate_text` and `vehicle_group` (else 422); manual exit requires `session_id`.
- Written UI copy: Vietnamese, no dash characters (`-`, `–`, `—`) as prose punctuation; keep only meaningful codes/plates.
- Test runner: `cd src/frontend && npx vitest run <path>`. Vitest globals (`test`, `expect`, `vi`, `beforeEach`) are configured in `src/test/setup.ts`; do not import them.
- One vehicle must fit one viewport height at desktop, tablet, and small kiosk widths; result region scrolls, page does not.

---

## File Structure

- `src/frontend/src/features/gate/use-camera.ts` (modify) — add `status` state machine + mount permission request.
- `src/frontend/src/features/gate/camera-view.tsx` (modify) — placeholder states, capped/collapsible video.
- `src/frontend/src/features/gate/plate-color.ts` (create) — color code to `{label, swatch}` map.
- `src/frontend/src/features/gate/recognition-result.tsx` (create) — readable type/group/color block + warnings.
- `src/frontend/src/features/gate/pay-row.tsx` (create) — inline payment row (replaces `PaymentDialog`).
- `src/frontend/src/features/gate/decision-panel.tsx` (rewrite) — validation, plate auto-save, plateless-entry action, manual+group selector, inline pay, imperative handle.
- `src/frontend/src/features/gate/gate-panel.tsx` (modify) — capped camera, flex-col fill, forward handle to `DecisionPanel`, pay-open bubbling.
- `src/frontend/src/features/gate/gate-page.tsx` (modify) — `h-full` flex layout, route keyboard actions, track pay-open for `dialogOpen`.
- `src/frontend/src/features/gate/payment-dialog.tsx` (delete) — replaced by `pay-row.tsx`.

---

## Task 1: Camera status state machine

**Files:**
- Modify: `src/frontend/src/features/gate/use-camera.ts`
- Test: `src/frontend/src/features/gate/use-camera.test.ts`

**Interfaces:**
- Produces: `useCamera()` returns everything it does today plus `status: "idle" | "requesting" | "streaming" | "denied" | "no-device" | "error"` and `requestPermission: () => Promise<void>`.

- [ ] **Step 1: Add failing tests**

Append to `src/frontend/src/features/gate/use-camera.test.ts`:

```ts
test("status is no-device when there are no video inputs", async () => {
  const { enumerate } = mockMediaDevices();
  enumerate.mockResolvedValueOnce([{ kind: "audioinput", deviceId: "mic", label: "Mic" }]);
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.listDevices();
  });
  await waitFor(() => expect(result.current.status).toBe("no-device"));
});

test("status becomes streaming after successful start", async () => {
  mockMediaDevices();
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  await waitFor(() => expect(result.current.status).toBe("streaming"));
});

test("status becomes denied when getUserMedia rejects with NotAllowedError", async () => {
  const { getUserMedia } = mockMediaDevices();
  getUserMedia.mockRejectedValueOnce(Object.assign(new Error("no"), { name: "NotAllowedError" }));
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  await waitFor(() => expect(result.current.status).toBe("denied"));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/frontend && npx vitest run src/features/gate/use-camera.test.ts`
Expected: FAIL, `result.current.status` is undefined.

- [ ] **Step 3: Implement status in the hook**

Replace the full contents of `src/frontend/src/features/gate/use-camera.ts` with:

```ts
import { useCallback, useEffect, useRef, useState } from "react";

export type CameraDevice = { deviceId: string; label: string };
export type CameraStatus = "idle" | "requesting" | "streaming" | "denied" | "no-device" | "error";

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevices] = useState<CameraDevice[]>([]);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<CameraStatus>("idle");

  const listDevices = useCallback(async () => {
    try {
      const all = await navigator.mediaDevices.enumerateDevices();
      const cams = all
        .filter((d) => d.kind === "videoinput")
        .map((d) => ({ deviceId: d.deviceId, label: d.label || "Camera" }));
      setDevices(cams);
      setDeviceId((prev) => prev ?? (cams[0]?.deviceId ?? null));
      setStatus((prev) => (cams.length === 0 ? "no-device" : prev === "streaming" ? prev : "idle"));
    } catch {
      setError("Không liệt kê được camera");
      setStatus("error");
    }
  }, []);

  const start = useCallback(async (id?: string) => {
    setStatus("requesting");
    try {
      const constraints: MediaStreamConstraints = {
        video: id ? { deviceId: { exact: id } } : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setError(null);
      setStatus("streaming");
    } catch (e) {
      const name = (e as { name?: string })?.name;
      const denied = name === "NotAllowedError" || name === "SecurityError";
      setError("Không mở được camera (kiểm tra quyền hoặc thiết bị)");
      setStatus(denied ? "denied" : "error");
    }
  }, []);

  const requestPermission = useCallback(async () => {
    await start();
    await listDevices();
  }, [start, listDevices]);

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

  return { videoRef, devices, deviceId, setDeviceId, listDevices, start, requestPermission, capture, error, status };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/frontend && npx vitest run src/features/gate/use-camera.test.ts`
Expected: PASS (all tests, including the three existing ones).

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/use-camera.ts src/frontend/src/features/gate/use-camera.test.ts
git commit -m "feat(gate): add camera status state machine and requestPermission"
```

---

## Task 2: Camera placeholder states and capped video

**Files:**
- Modify: `src/frontend/src/features/gate/camera-view.tsx`
- Test: `src/frontend/src/features/gate/camera-view.test.tsx` (create)

**Interfaces:**
- Consumes: `CameraStatus` from `./use-camera`.
- Produces: `CameraView` gains props `status: CameraStatus`, `onRequestPermission: () => void`, `onManual: () => void`. Renders `<video>` only when `status === "streaming"`; otherwise a placeholder with the correct button.

- [ ] **Step 1: Write the failing test**

Create `src/frontend/src/features/gate/camera-view.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CameraView } from "./camera-view";

const base = {
  videoRef: { current: null },
  devices: [],
  deviceId: null,
  onSelectDevice: () => {},
  onCapture: () => {},
  onManual: () => {},
  error: null,
};

test("no-device status shows connect button and hides video", () => {
  render(<CameraView {...base} status="no-device" onRequestPermission={() => {}} />);
  expect(screen.getByRole("button", { name: /Kết nối lại/i })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Chụp" })).not.toBeInTheDocument();
});

test("denied status calls onRequestPermission when granting", async () => {
  const onRequestPermission = vi.fn();
  render(<CameraView {...base} status="denied" onRequestPermission={onRequestPermission} />);
  await userEvent.click(screen.getByRole("button", { name: /Cấp quyền camera/i }));
  expect(onRequestPermission).toHaveBeenCalled();
});

test("streaming status shows capture button", () => {
  render(
    <CameraView
      {...base}
      status="streaming"
      devices={[{ deviceId: "cam-a", label: "Cam A" }]}
      deviceId="cam-a"
      onRequestPermission={() => {}}
    />,
  );
  expect(screen.getByRole("button", { name: "Chụp" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/camera-view.test.tsx`
Expected: FAIL, `Kết nối lại` button not found.

- [ ] **Step 3: Implement placeholder states**

Replace the full contents of `src/frontend/src/features/gate/camera-view.tsx` with:

```tsx
import type { RefObject } from "react";
import type { CameraDevice, CameraStatus } from "./use-camera";
import { Button } from "@/components/ui/button";

export function CameraView({
  videoRef,
  devices,
  deviceId,
  status,
  onSelectDevice,
  onCapture,
  onRequestPermission,
  onManual,
  error,
}: {
  videoRef: RefObject<HTMLVideoElement | null>;
  devices: CameraDevice[];
  deviceId: string | null;
  status: CameraStatus;
  onSelectDevice: (id: string) => void;
  onCapture: () => void;
  onRequestPermission: () => void;
  onManual: () => void;
  error: string | null;
}) {
  const streaming = status === "streaming";

  return (
    <div className="space-y-2">
      {streaming && (
        <div className="flex items-center gap-2">
          <select
            aria-label="Chọn camera"
            className="h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-[13px]"
            value={deviceId ?? ""}
            onChange={(e) => onSelectDevice(e.target.value)}
          >
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
      )}

      {streaming ? (
        <div className="flex aspect-video max-h-[34vh] items-center justify-center overflow-hidden rounded-[var(--radius-control)] bg-surface">
          <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
        </div>
      ) : (
        <div className="flex aspect-video max-h-[34vh] flex-col items-center justify-center gap-3 rounded-[var(--radius-control)] border border-dashed border-line bg-surface p-4 text-center">
          <p className="text-sm font-medium text-ink">
            {status === "requesting" && "Đang mở camera..."}
            {status === "no-device" && "Không tìm thấy camera"}
            {status === "denied" && "Chưa cấp quyền camera"}
            {(status === "error" || status === "idle") && "Camera chưa kết nối"}
          </p>
          <div className="flex gap-2">
            <Button className="h-10" onClick={onRequestPermission}>
              {status === "denied" ? "Cấp quyền camera" : "Kết nối lại"}
            </Button>
            <Button variant="outline" className="h-10" onClick={onManual}>
              Nhập tay
            </Button>
          </div>
        </div>
      )}

      {error && !streaming && <p className="text-[13px] text-st-amber">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/gate/camera-view.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/camera-view.tsx src/frontend/src/features/gate/camera-view.test.tsx
git commit -m "feat(gate): camera placeholder states and capped video height"
```

---

## Task 3: Plate color map

**Files:**
- Create: `src/frontend/src/features/gate/plate-color.ts`
- Test: `src/frontend/src/features/gate/plate-color.test.ts` (create)

**Interfaces:**
- Produces: `plateColor(value?: string | null): { label: string; swatch: string } | null`.

- [ ] **Step 1: Write the failing test**

Create `src/frontend/src/features/gate/plate-color.test.ts`:

```ts
import { plateColor } from "./plate-color";

test("maps known color code to Vietnamese label and swatch", () => {
  expect(plateColor("white")).toEqual({ label: "Trắng", swatch: "#ffffff" });
  expect(plateColor("YELLOW")).toEqual({ label: "Vàng", swatch: "#f4c400" });
});

test("returns null for empty", () => {
  expect(plateColor(null)).toBeNull();
  expect(plateColor("")).toBeNull();
});

test("unknown code falls back to raw label with transparent swatch", () => {
  expect(plateColor("teal")).toEqual({ label: "teal", swatch: "transparent" });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/plate-color.test.ts`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the map**

Create `src/frontend/src/features/gate/plate-color.ts`:

```ts
export type PlateColorInfo = { label: string; swatch: string };

const MAP: Record<string, PlateColorInfo> = {
  white: { label: "Trắng", swatch: "#ffffff" },
  yellow: { label: "Vàng", swatch: "#f4c400" },
  blue: { label: "Xanh", swatch: "#2e6fd6" },
  red: { label: "Đỏ", swatch: "#d24a3e" },
};

export function plateColor(value?: string | null): PlateColorInfo | null {
  if (!value) return null;
  return MAP[value.toLowerCase()] ?? { label: value, swatch: "transparent" };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/gate/plate-color.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/plate-color.ts src/frontend/src/features/gate/plate-color.test.ts
git commit -m "feat(gate): plate color to label and swatch map"
```

---

## Task 4: Recognition result block

**Files:**
- Create: `src/frontend/src/features/gate/recognition-result.tsx`
- Test: `src/frontend/src/features/gate/recognition-result.test.tsx` (create)

**Interfaces:**
- Consumes: `plateColor` from `./plate-color`; `groupLabel` from `@/lib/vehicle-groups`; `GateCapture` from `./use-gate-socket`.
- Produces: `RecognitionResult({ capture, groupMap })` — presentational; renders type/group/color rows (>=15px) with a color swatch, plus format/duplicate warnings.

- [ ] **Step 1: Write the failing test**

Create `src/frontend/src/features/gate/recognition-result.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { RecognitionResult } from "./recognition-result";
import type { GateCapture } from "./use-gate-socket";

vi.mock("@/lib/vehicle-groups", () => ({
  groupLabel: (_m: Record<string, string>, c?: string | null) => (c === "xe_may" ? "Xe máy" : c ?? "—"),
}));

const base: GateCapture = {
  reading_id: 1,
  capture_id: "c1",
  direction: "in",
  review_state: "confident",
  plate_text: "51F-123",
};

test("renders type, group label and color label", () => {
  render(
    <RecognitionResult
      capture={{ ...base, vehicle_type: "Xe tay ga", vehicle_group: "xe_may", color: "white" }}
      groupMap={{}}
    />,
  );
  expect(screen.getByText("Xe tay ga")).toBeInTheDocument();
  expect(screen.getByText("Xe máy")).toBeInTheDocument();
  expect(screen.getByText("Trắng")).toBeInTheDocument();
});

test("shows invalid-format and duplicate warnings", () => {
  render(<RecognitionResult capture={{ ...base, plate_valid: false, duplicate: true }} groupMap={{}} />);
  expect(screen.getByText(/sai định dạng/i)).toBeInTheDocument();
  expect(screen.getByText(/trùng phiên/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/recognition-result.test.tsx`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the component**

Create `src/frontend/src/features/gate/recognition-result.tsx`:

```tsx
import type { GateCapture } from "./use-gate-socket";
import { groupLabel } from "@/lib/vehicle-groups";
import { plateColor } from "./plate-color";

export function RecognitionResult({
  capture,
  groupMap,
}: {
  capture: GateCapture;
  groupMap: Record<string, string>;
}) {
  const color = plateColor(capture.color);
  return (
    <div className="space-y-2">
      <dl className="grid grid-cols-3 gap-x-4 gap-y-1">
        <div>
          <dt className="text-[13px] text-muted">Loại xe</dt>
          <dd className="text-[16px] font-medium text-ink">{capture.vehicle_type ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-[13px] text-muted">Nhóm phí</dt>
          <dd className="text-[16px] font-medium text-ink">
            {capture.vehicle_group ? groupLabel(groupMap, capture.vehicle_group) : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-[13px] text-muted">Màu biển</dt>
          <dd className="flex items-center gap-2 text-[16px] font-medium text-ink">
            {color && (
              <span
                className="inline-block h-4 w-4 shrink-0 rounded-full border border-line"
                style={{ background: color.swatch }}
              />
            )}
            {color?.label ?? "—"}
          </dd>
        </div>
      </dl>
      {capture.plate_valid === false && (
        <p className="text-[13px] text-st-amber">Cảnh báo: biển sai định dạng (vẫn cho xác nhận)</p>
      )}
      {capture.duplicate && (
        <p className="text-[13px] text-st-amber">Cảnh báo: biển trùng phiên trong bãi</p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/gate/recognition-result.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/recognition-result.tsx src/frontend/src/features/gate/recognition-result.test.tsx
git commit -m "feat(gate): readable recognition result block with color swatch"
```

---

## Task 5: Inline pay row (replaces modal)

**Files:**
- Create: `src/frontend/src/features/gate/pay-row.tsx`
- Test: `src/frontend/src/features/gate/pay-row.test.tsx` (create)

**Interfaces:**
- Consumes: `Receipt` from `./receipt`; `formatVnd` from `@/lib/format`.
- Produces: `PAY_METHODS: { key: string; label: string }[]` (exported, order `cash`, `qr`, `ewallet`) and `PayRow` — presentational:
  ```ts
  PayRow(props: {
    sessionId: number;
    plate?: string | null;
    amount: number;
    method: string;
    onMethod: (key: string) => void;
    onConfirm: () => void;
    pending: boolean;
    paid: boolean;
  })
  ```

- [ ] **Step 1: Write the failing test**

Create `src/frontend/src/features/gate/pay-row.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PayRow } from "./pay-row";

vi.mock("./receipt", () => ({
  Receipt: ({ amount }: { amount: number }) => <div>RECEIPT {amount}</div>,
}));

const base = {
  sessionId: 9,
  plate: "51F1",
  amount: 5000,
  method: "cash",
  onMethod: () => {},
  onConfirm: () => {},
  pending: false,
  paid: false,
};

test("renders amount and method buttons, fires confirm", async () => {
  const onConfirm = vi.fn();
  render(<PayRow {...base} onConfirm={onConfirm} />);
  expect(screen.getByText(/5[.,]?000/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Thu & in/i }));
  expect(onConfirm).toHaveBeenCalled();
});

test("shows receipt when paid", () => {
  render(<PayRow {...base} paid />);
  expect(screen.getByText(/RECEIPT 5000/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/pay-row.test.tsx`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the component**

Create `src/frontend/src/features/gate/pay-row.tsx`:

```tsx
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";
import { Receipt } from "./receipt";

export const PAY_METHODS: { key: string; label: string }[] = [
  { key: "cash", label: "Tiền mặt" },
  { key: "qr", label: "QR" },
  { key: "ewallet", label: "Ví điện tử" },
];

export function PayRow({
  sessionId,
  plate,
  amount,
  method,
  onMethod,
  onConfirm,
  pending,
  paid,
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  method: string;
  onMethod: (key: string) => void;
  onConfirm: () => void;
  pending: boolean;
  paid: boolean;
}) {
  if (paid) {
    return (
      <div className="rounded-[var(--radius-control)] border border-line p-3">
        <Receipt sessionId={sessionId} plate={plate} amount={amount} method={method} />
      </div>
    );
  }
  return (
    <div className="space-y-3 rounded-[var(--radius-control)] border border-line p-3">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold">Thu tiền khi RA</p>
        <p className="tnum text-[22px] font-semibold">{formatVnd(amount)}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {PAY_METHODS.map((m, i) => (
          <Button
            key={m.key}
            variant={method === m.key ? "default" : "outline"}
            className="h-11"
            onClick={() => onMethod(m.key)}
          >
            {i + 1} {m.label}
          </Button>
        ))}
      </div>
      <Button className="h-11 w-full" onClick={onConfirm} disabled={pending}>
        Thu & in (Enter)
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/gate/pay-row.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/gate/pay-row.tsx src/frontend/src/features/gate/pay-row.test.tsx
git commit -m "feat(gate): inline pay row component"
```

---

## Task 6: DecisionPanel rewrite (validation, auto-save, plateless, manual+group, inline pay, handle)

**Files:**
- Rewrite: `src/frontend/src/features/gate/decision-panel.tsx`
- Test: `src/frontend/src/features/gate/decision-panel.test.tsx` (rewrite)
- Delete: `src/frontend/src/features/gate/payment-dialog.tsx` and `src/frontend/src/features/gate/payment-dialog.test.tsx`

**Interfaces:**
- Consumes: `useConfirmEntry`, `useConfirmExit`, `useManualSession` from `@/api/generated/sessions/sessions`; `usePatchPlate` from `@/api/generated/readings/readings`; `useCreatePayment` from `@/api/generated/payments/payments`; `useGetToggles` from `@/api/generated/config/config`; `useListVehicleGroups` from `@/api/generated/vehicle-groups/vehicle-groups`; `useVehicleGroupMap` from `@/lib/vehicle-groups`; `RecognitionResult`, `PayRow`, `PAY_METHODS`; `PlateField`, `StatusChip`, `Button`.
- Produces: `DecisionPanelHandle = { confirm(): void; manual(): void; cancel(): void; payMethod(n: number): void; focusPlate(): void }`. `DecisionPanel` is `forwardRef<DecisionPanelHandle, Props>` where
  ```ts
  Props = {
    capture: GateCapture;
    direction: "in" | "out";
    onDone: () => void;
    onRecapture: () => void;
    onPayOpenChange?: (open: boolean) => void;
  }
  ```

- [ ] **Step 1: Rewrite the test file**

Replace the full contents of `src/frontend/src/features/gate/decision-panel.test.tsx` with:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionPanel } from "./decision-panel";
import type { GateCapture } from "./use-gate-socket";

vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({ xe_may: "Xe máy" }),
  groupLabel: (m: Record<string, string>, c?: string | null) => (c ? (m[c] ?? c) : "—"),
}));

const confirmEntry = vi.fn().mockResolvedValue({ id: 1, status: "in_lot" });
const confirmExit = vi.fn();
const manualFn = vi.fn().mockResolvedValue({ id: 2 });
const patchFn = vi.fn().mockResolvedValue({});
const payFn = vi.fn().mockResolvedValue({});
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: confirmEntry, isPending: false }),
  useConfirmExit: () => ({ mutateAsync: confirmExit, isPending: false }),
  useManualSession: () => ({ mutateAsync: manualFn, isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({
  usePatchPlate: () => ({ mutateAsync: patchFn, isPending: false }),
}));
vi.mock("@/api/generated/payments/payments", () => ({
  useCreatePayment: () => ({ mutateAsync: payFn, isPending: false }),
}));
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }),
}));
vi.mock("@/api/generated/vehicle-groups/vehicle-groups", () => ({
  useListVehicleGroups: () => ({ data: [{ code: "xe_may", display_name: "Xe máy" }, { code: "o_to", display_name: "Ô tô" }] }),
}));

const base: GateCapture = {
  reading_id: 7,
  capture_id: "c1",
  direction: "in",
  review_state: "confident",
  plate_text: "51F-123",
};

const noop = () => {};

beforeEach(() => {
  confirmEntry.mockClear();
  confirmExit.mockClear();
  manualFn.mockClear();
  patchFn.mockClear();
  payFn.mockClear();
});

test("confident IN confirms entry", async () => {
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận VÀO/i }));
  expect(confirmEntry).toHaveBeenCalledWith({ data: { reading_id: 7 } });
});

test("edited plate is saved before confirming entry", async () => {
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={noop} />);
  const input = screen.getByLabelText("Biển số");
  await userEvent.clear(input);
  await userEvent.type(input, "51F-999");
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận VÀO/i }));
  expect(patchFn).toHaveBeenCalledWith({ readingId: 7, data: { plate_text: "51F-999" } });
  expect(confirmEntry).toHaveBeenCalled();
});

test("empty plate disables primary confirm and offers plateless entry", async () => {
  render(<DecisionPanel capture={{ ...base, plate_text: "" }} direction="in" onDone={noop} onRecapture={noop} />);
  expect(screen.getByRole("button", { name: /Xác nhận VÀO/i })).toBeDisabled();
  const plateless = screen.getByRole("button", { name: /Vào không biển/i });
  await userEvent.click(plateless);
  expect(confirmEntry).toHaveBeenCalledWith({ data: { reading_id: 7 } });
  expect(patchFn).not.toHaveBeenCalled();
});

test("manual entry requires a vehicle group before submit", async () => {
  render(<DecisionPanel capture={{ ...base, vehicle_group: null }} direction="in" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Nhập tay/i }));
  const submit = screen.getByRole("button", { name: /Ghi nhận nhập tay/i });
  expect(submit).toBeDisabled();
  await userEvent.selectOptions(screen.getByLabelText("Nhóm phí"), "o_to");
  expect(submit).toBeEnabled();
  await userEvent.click(submit);
  expect(manualFn).toHaveBeenCalledWith({ data: { action: "entry", plate_text: "51F-123", vehicle_group: "o_to" } });
});

test("re-recognize button calls onRecapture", async () => {
  const onRecapture = vi.fn();
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={onRecapture} />);
  await userEvent.click(screen.getByRole("button", { name: /Nhận lại/i }));
  expect(onRecapture).toHaveBeenCalled();
});

test("exit with fee shows inline pay row, no modal", async () => {
  confirmExit.mockResolvedValueOnce({ outcome: "completed", session: { id: 9, fee_amount: 5000, plate_text: "51F1" } });
  render(<DecisionPanel capture={{ ...base, review_state: "confident" }} direction="out" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận RA/i }));
  expect(await screen.findByText(/Thu tiền khi RA/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Thu & in/i }));
  expect(payFn).toHaveBeenCalledWith({ data: { session_id: 9, amount: 5000, method: "cash", kind: "payment" } });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/decision-panel.test.tsx`
Expected: FAIL (new props/labels/behaviors not present).

- [ ] **Step 3: Rewrite DecisionPanel**

Replace the full contents of `src/frontend/src/features/gate/decision-panel.tsx` with:

```tsx
import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { toast } from "sonner";
import { useConfirmEntry, useConfirmExit, useManualSession } from "@/api/generated/sessions/sessions";
import { usePatchPlate } from "@/api/generated/readings/readings";
import { useCreatePayment } from "@/api/generated/payments/payments";
import { useGetToggles } from "@/api/generated/config/config";
import { useListVehicleGroups } from "@/api/generated/vehicle-groups/vehicle-groups";
import type { GateCapture } from "./use-gate-socket";
import { PlateField } from "@/components/plate-field";
import { StatusChip } from "@/components/status-chip";
import { Button } from "@/components/ui/button";
import { RecognitionResult } from "./recognition-result";
import { PayRow, PAY_METHODS } from "./pay-row";
import { useVehicleGroupMap } from "@/lib/vehicle-groups";

export type DecisionPanelHandle = {
  confirm: () => void;
  manual: () => void;
  cancel: () => void;
  payMethod: (n: number) => void;
  focusPlate: () => void;
};

type Props = {
  capture: GateCapture;
  direction: "in" | "out";
  onDone: () => void;
  onRecapture: () => void;
  onPayOpenChange?: (open: boolean) => void;
};

export const DecisionPanel = forwardRef<DecisionPanelHandle, Props>(function DecisionPanel(
  { capture, direction, onDone, onRecapture, onPayOpenChange },
  ref,
) {
  const { data: toggles } = useGetToggles();
  const forceManual = toggles ? !toggles.read_plate : false;
  const state = forceManual ? "manual" : capture.review_state;
  const groupMap = useVehicleGroupMap();
  const { data: groups } = useListVehicleGroups();

  const [plate, setPlate] = useState(capture.plate_text ?? "");
  useEffect(() => setPlate(capture.plate_text ?? ""), [capture.reading_id, capture.plate_text]);

  const [group, setGroup] = useState(capture.vehicle_group ?? "");
  useEffect(() => setGroup(capture.vehicle_group ?? ""), [capture.reading_id, capture.vehicle_group]);

  const [manualOpen, setManualOpen] = useState(state === "manual");
  useEffect(() => setManualOpen(state === "manual"), [state, capture.reading_id]);

  const confirmEntry = useConfirmEntry();
  const confirmExit = useConfirmExit();
  const manual = useManualSession();
  const patchPlate = usePatchPlate();
  const createPayment = useCreatePayment();

  const [candidates, setCandidates] = useState<{ id: number; plate_text?: string | null }[]>([]);
  const [payFor, setPayFor] = useState<{ sessionId: number; amount: number; plate?: string | null } | null>(null);
  const [method, setMethod] = useState("cash");
  const [paid, setPaid] = useState(false);

  useEffect(() => {
    onPayOpenChange?.(payFor !== null);
  }, [payFor, onPayOpenChange]);

  const busy =
    confirmEntry.isPending ||
    confirmExit.isPending ||
    manual.isPending ||
    patchPlate.isPending ||
    createPayment.isPending;
  const plateTrim = plate.trim();
  const plateChanged = plateTrim !== (capture.plate_text ?? "").trim();

  const ensurePlateSaved = async () => {
    if (plateTrim && plateChanged) {
      await patchPlate.mutateAsync({ readingId: capture.reading_id, data: { plate_text: plateTrim } });
    }
  };

  const savePlate = async () => {
    if (!plateTrim || !plateChanged || busy) return;
    await patchPlate.mutateAsync({ readingId: capture.reading_id, data: { plate_text: plateTrim } });
    toast.success("Đã cập nhật biển số");
  };

  const doEntry = async (allowPlateless = false) => {
    if (busy) return;
    if (!plateTrim && !allowPlateless) return;
    if (plateTrim) await ensurePlateSaved();
    await confirmEntry.mutateAsync({ data: { reading_id: capture.reading_id } });
    toast.success(plateTrim ? "Đã xác nhận VÀO" : "Đã tạo phiên chờ (vào không biển)");
    onDone();
  };

  const doExit = async (sessionId?: number) => {
    if (busy) return;
    if (plateTrim) await ensurePlateSaved();
    const res = await confirmExit.mutateAsync({
      data: { reading_id: capture.reading_id, ...(sessionId ? { session_id: sessionId } : {}) },
    });
    if (res.candidates && res.candidates.length > 0 && !sessionId) {
      setCandidates(res.candidates);
      return;
    }
    const s = res.session;
    if (!s) {
      toast.error("Không tìm thấy phiên phù hợp. Chọn phiên hoặc dùng Nhập tay.");
      return;
    }
    if ((s.fee_amount ?? 0) > 0) {
      setPayFor({ sessionId: s.id, amount: s.fee_amount as number, plate: s.plate_text });
      return;
    }
    toast.success("Đã xác nhận RA (miễn phí)");
    onDone();
  };

  const doManualEntry = async () => {
    if (busy) return;
    if (!plateTrim || !group) {
      toast.error("Nhập tay cần biển số và nhóm phí");
      return;
    }
    await manual.mutateAsync({ data: { action: "entry", plate_text: plateTrim, vehicle_group: group } });
    toast.success("Đã ghi nhận nhập tay");
    onDone();
  };

  const confirmPay = async () => {
    if (!payFor || createPayment.isPending) return;
    await createPayment.mutateAsync({
      data: { session_id: payFor.sessionId, amount: payFor.amount, method, kind: "payment" },
    });
    toast.success("Đã thu tiền");
    setPaid(true);
  };

  const primaryConfirm = () => (direction === "in" ? doEntry(false) : doExit());

  useImperativeHandle(ref, () => ({
    confirm: () => {
      if (payFor) {
        if (paid) onDone();
        else confirmPay();
      } else {
        primaryConfirm();
      }
    },
    manual: () => setManualOpen(true),
    cancel: () => {
      if (payFor) {
        if (!paid) setPayFor(null);
      } else if (candidates.length) {
        setCandidates([]);
      } else {
        onDone();
      }
    },
    payMethod: (n) => {
      const m = PAY_METHODS[n - 1];
      if (m) setMethod(m.key);
    },
    focusPlate: () => document.getElementById("plate")?.focus(),
  }));

  const entryDisabled = busy || !plateTrim;
  const exitDisabled = busy;

  if (payFor) {
    return (
      <PayRow
        sessionId={payFor.sessionId}
        plate={payFor.plate}
        amount={payFor.amount}
        method={method}
        onMethod={setMethod}
        onConfirm={paid ? onDone : confirmPay}
        pending={createPayment.isPending}
        paid={paid}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <StatusChip kind="review" value={state} />
        <Button variant="outline" className="h-9" onClick={onRecapture} disabled={busy}>
          Nhận lại
        </Button>
      </div>

      <PlateField value={plate} onChange={setPlate} size="lg" highlight={state === "needs_review"} />

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" className="h-9" onClick={savePlate} disabled={!plateTrim || !plateChanged || busy}>
          Lưu biển
        </Button>
      </div>

      <RecognitionResult capture={capture} groupMap={groupMap} />

      {candidates.length > 0 ? (
        <div className="space-y-2">
          <p className="text-sm font-medium">Chọn phiên để nối</p>
          {candidates.map((c) => (
            <Button
              key={c.id}
              variant="outline"
              className="w-full justify-start"
              onClick={() => doExit(c.id)}
            >
              #{c.id} — {c.plate_text ?? "?"}
            </Button>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {direction === "in" ? (
            <div className="flex flex-wrap gap-2">
              <Button className="h-11 min-w-[44px]" onClick={() => doEntry(false)} disabled={entryDisabled}>
                Xác nhận VÀO
              </Button>
              {!plateTrim && (
                <Button variant="outline" className="h-11" onClick={() => doEntry(true)} disabled={busy}>
                  Vào không biển (phiên chờ)
                </Button>
              )}
            </div>
          ) : (
            <Button className="h-11 min-w-[44px]" onClick={() => doExit()} disabled={exitDisabled}>
              Xác nhận RA
            </Button>
          )}
          {entryDisabled && direction === "in" && (
            <p className="text-[13px] text-muted">Cần biển số để xác nhận VÀO, hoặc dùng "Vào không biển".</p>
          )}
        </div>
      )}

      {manualOpen && direction === "in" && (
        <div className="space-y-2 border-t border-line pt-3">
          <p className="text-sm font-medium">Nhập tay hoàn toàn</p>
          <label className="block text-[13px] text-muted" htmlFor="manual-group">
            Nhóm phí
          </label>
          <select
            id="manual-group"
            aria-label="Nhóm phí"
            className="h-10 w-full rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
            value={group}
            onChange={(e) => setGroup(e.target.value)}
          >
            <option value="">Chọn nhóm phí</option>
            {(groups ?? []).map((g) => (
              <option key={g.code} value={g.code}>
                {g.display_name}
              </option>
            ))}
          </select>
          <Button className="h-11" onClick={doManualEntry} disabled={busy || !plateTrim || !group}>
            Ghi nhận nhập tay
          </Button>
        </div>
      )}

      {manualOpen && direction === "out" && (
        <p className="border-t border-line pt-3 text-[13px] text-muted">
          Nhập tay RA: chọn phiên trong danh sách để nối.
        </p>
      )}

      {!manualOpen && (
        <div className="border-t border-line pt-3">
          <Button variant="secondary" className="h-11" onClick={() => setManualOpen(true)}>
            Nhập tay
          </Button>
        </div>
      )}
    </div>
  );
});
```

- [ ] **Step 4: Delete the modal payment component**

```bash
git rm src/frontend/src/features/gate/payment-dialog.tsx src/frontend/src/features/gate/payment-dialog.test.tsx
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd src/frontend && npx vitest run src/features/gate/decision-panel.test.tsx`
Expected: PASS (all 7 tests).

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/features/gate/decision-panel.tsx src/frontend/src/features/gate/decision-panel.test.tsx
git commit -m "feat(gate): validated decision panel with auto-save, plateless entry, manual group, inline pay"
```

---

## Task 7: GatePanel + GatePage layout and keyboard wiring

**Files:**
- Modify: `src/frontend/src/features/gate/gate-panel.tsx`
- Modify: `src/frontend/src/features/gate/gate-page.tsx`
- Modify: `src/frontend/src/features/gate/gate-panel.test.tsx`
- Modify: `src/frontend/src/features/gate/gate-page.test.tsx`
- Modify: `src/frontend/src/components/app-shell.tsx`

**Interfaces:**
- Consumes: `DecisionPanelHandle` from `./decision-panel`; `CameraView` new props from Task 2; `useCamera` `status`/`requestPermission` from Task 1.
- Produces: `GatePanelHandle = { capture(): void; focusPlate(): void; confirm(): void; manual(): void; cancel(): void; payMethod(n: number): void }`. `GatePanel` gains prop `onPayOpenChange?: (open: boolean) => void`.

- [ ] **Step 1: Update GatePanel test**

Replace the full contents of `src/frontend/src/features/gate/gate-panel.test.tsx` with:

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
    status: "streaming",
    setDeviceId: vi.fn(),
    listDevices: vi.fn(),
    start: vi.fn(),
    requestPermission: vi.fn(),
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
vi.mock("@/api/generated/payments/payments", () => ({ useCreatePayment: () => ({ mutateAsync: vi.fn(), isPending: false }) }));
vi.mock("@/api/generated/config/config", () => ({ useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }) }));
vi.mock("@/api/generated/vehicle-groups/vehicle-groups", () => ({ useListVehicleGroups: () => ({ data: [] }) }));
vi.mock("@/lib/vehicle-groups", () => ({ useVehicleGroupMap: () => ({}), groupLabel: (_m: unknown, c?: string | null) => c ?? "—" }));

test("capturing runs infer then shows decision for the plate", async () => {
  render(<GatePanel direction="in" wsCapture={null} active onActivate={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: "Chụp" }));
  expect(postInfer).toHaveBeenCalled();
  expect(await screen.findByDisplayValue(/51F12345/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/gate-panel.test.tsx`
Expected: FAIL (GatePanel does not yet pass `status`/`onRecapture`; `useCreatePayment` import missing in DecisionPanel is satisfied by Task 6, but GatePanel still references old CameraView props).

- [ ] **Step 3: Rewrite GatePanel**

Replace the full contents of `src/frontend/src/features/gate/gate-panel.tsx` with:

```tsx
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { toast } from "sonner";
import { CameraView } from "./camera-view";
import { DecisionPanel, type DecisionPanelHandle } from "./decision-panel";
import { useCamera } from "./use-camera";
import { postInfer } from "./infer-capture";
import type { GateCapture } from "./use-gate-socket";
import { SurfaceCard } from "@/components/surface-card";
import { EmptyState } from "@/components/empty-state";

export type GatePanelHandle = {
  capture: () => void;
  focusPlate: () => void;
  confirm: () => void;
  manual: () => void;
  cancel: () => void;
  payMethod: (n: number) => void;
};

export const GatePanel = forwardRef<
  GatePanelHandle,
  {
    direction: "in" | "out";
    wsCapture: GateCapture | null;
    active: boolean;
    onActivate: () => void;
    onPayOpenChange?: (open: boolean) => void;
  }
>(function GatePanel({ direction, wsCapture, active, onActivate, onPayOpenChange }, ref) {
  const cam = useCamera();
  const [capture, setCapture] = useState<GateCapture | null>(null);
  const [busy, setBusy] = useState(false);
  const decisionRef = useRef<DecisionPanelHandle | null>(null);

  useEffect(() => {
    cam.requestPermission();
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
    focusPlate: () => decisionRef.current?.focusPlate(),
    confirm: () => decisionRef.current?.confirm(),
    manual: () => decisionRef.current?.manual(),
    cancel: () => {
      if (decisionRef.current) decisionRef.current.cancel();
    },
    payMethod: (n) => decisionRef.current?.payMethod(n),
  }));

  return (
    <div
      onClick={onActivate}
      className={active ? "h-full rounded-[var(--radius-card)] ring-2 ring-ink" : "h-full"}
    >
      <SurfaceCard variant="white" className="flex h-full flex-col">
        <h2 className="mb-2 text-sm font-semibold">{direction === "in" ? "Hướng VÀO" : "Hướng RA"}</h2>
        <CameraView
          videoRef={cam.videoRef}
          devices={cam.devices}
          deviceId={cam.deviceId}
          status={cam.status}
          onSelectDevice={cam.setDeviceId}
          onCapture={doCapture}
          onRequestPermission={cam.requestPermission}
          onManual={() => decisionRef.current?.manual()}
          error={cam.error}
        />
        <div className="mt-3 min-h-0 flex-1 overflow-auto">
          {capture ? (
            <DecisionPanel
              ref={decisionRef}
              capture={capture}
              direction={direction}
              onDone={() => setCapture(null)}
              onRecapture={doCapture}
              onPayOpenChange={onPayOpenChange}
            />
          ) : (
            <EmptyState title="Chưa có lượt chụp" hint="Bấm Chụp hoặc chờ sự kiện cổng" />
          )}
        </div>
      </SurfaceCard>
    </div>
  );
});
```

- [ ] **Step 4: Run GatePanel test to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/gate/gate-panel.test.tsx`
Expected: PASS.

- [ ] **Step 5: Update GatePage test**

Replace the full contents of `src/frontend/src/features/gate/gate-page.test.tsx` with:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GatePage } from "./gate-page";

const confirm = vi.fn();
vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({
    capturesByDirection: { in: null, out: null },
    events: [],
    connected: true,
    degraded: false,
  }),
}));
vi.mock("./gate-panel", async () => {
  const { forwardRef, useImperativeHandle } = await import("react");
  return {
    GatePanel: forwardRef(function GP(
      { direction, active }: { direction: string; active: boolean },
      ref: unknown,
    ) {
      useImperativeHandle(ref as never, () => ({
        capture: () => {},
        focusPlate: () => {},
        confirm,
        manual: () => {},
        cancel: () => {},
        payMethod: () => {},
      }));
      return <div data-testid={`panel-${direction}`}>{active ? "ACTIVE" : "idle"}</div>;
    }),
  };
});

beforeEach(() => {
  localStorage.clear();
  confirm.mockClear();
});

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

test("Enter key routes confirm to the active panel", async () => {
  render(<GatePage />);
  await userEvent.keyboard("{Enter}");
  expect(confirm).toHaveBeenCalled();
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd src/frontend && npx vitest run src/features/gate/gate-page.test.tsx`
Expected: FAIL, `confirm` not called (Enter is not wired).

- [ ] **Step 7: Rewrite GatePage**

Replace the full contents of `src/frontend/src/features/gate/gate-page.tsx` with:

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
  { key: "Enter", desc: "Xác nhận VÀO/RA hoặc thu tiền" },
  { key: "E", desc: "Sửa biển" },
  { key: "M", desc: "Nhập tay" },
  { key: "Esc", desc: "Hủy kết quả panel" },
  { key: "1/2/3", desc: "Chọn phương thức khi thu tiền" },
  { key: "?", desc: "Bật/tắt bảng phím tắt" },
];

export function GatePage() {
  const { capturesByDirection, degraded } = useGateSocket();
  const [layout, setLayout] = useState<LayoutMode>(() => (localStorage.getItem(LS_KEY) as LayoutMode) || "split");
  const [active, setActive] = useState<"in" | "out">("in");
  const [showHelp, setShowHelp] = useState(false);
  const [payOpen, setPayOpen] = useState<{ in: boolean; out: boolean }>({ in: false, out: false });

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
        case "confirm":
        case "dialog-confirm":
          activeRef()?.confirm();
          break;
        case "manual":
          activeRef()?.manual();
          break;
        case "cancel":
        case "dialog-close":
          activeRef()?.cancel();
          break;
        case "method-1":
          activeRef()?.payMethod(1);
          break;
        case "method-2":
          activeRef()?.payMethod(2);
          break;
        case "method-3":
          activeRef()?.payMethod(3);
          break;
        case "toggle-help":
          setShowHelp((v) => !v);
          break;
        default:
          break;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [active, layout],
  );

  useGateShortcuts({ dialogOpen: payOpen[active], onAction });

  const showIn = layout === "split" || layout === "in";
  const showOut = layout === "split" || layout === "out";

  return (
    <div className="flex h-full flex-col gap-[14px]">
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

      <div
        className={
          layout === "split"
            ? "grid min-h-0 flex-1 grid-cols-1 gap-[14px] lg:grid-cols-2"
            : "grid min-h-0 flex-1 grid-cols-1 gap-[14px]"
        }
      >
        {showIn && (
          <GatePanel
            ref={inRef}
            direction="in"
            wsCapture={capturesByDirection.in}
            active={active === "in"}
            onActivate={() => setActive("in")}
            onPayOpenChange={(open) => setPayOpen((p) => ({ ...p, in: open }))}
          />
        )}
        {showOut && (
          <GatePanel
            ref={outRef}
            direction="out"
            wsCapture={capturesByDirection.out}
            active={active === "out"}
            onActivate={() => setActive("out")}
            onPayOpenChange={(open) => setPayOpen((p) => ({ ...p, out: open }))}
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

- [ ] **Step 8: Ensure the page can fill viewport height**

The gate page uses `h-full`, so `app-shell`'s `<main>` must give it a height. Verify `src/frontend/src/components/app-shell.tsx` line 21 reads:

```tsx
        <main className="min-h-0 flex-1 overflow-auto p-6">
```

Change it to constrain page scrolling to panels (the gate page manages its own internal scroll):

```tsx
        <main className="min-h-0 flex-1 overflow-hidden p-6">
```

Note: other routes (sessions, config) render inside this main. Confirm they still scroll by checking those pages wrap their own scroll or are short. If any long page needs scroll, this is acceptable because those pages use `space-y` lists shorter than the viewport in tests; the gate page is the height-critical one. If a regression appears, revert this single line and instead wrap only the gate page in a bounded container. Keep the change minimal.

- [ ] **Step 9: Run the gate test suite to verify it passes**

Run: `cd src/frontend && npx vitest run src/features/gate/`
Expected: PASS (all gate tests, including page/panel/decision/camera/pay/plate-color).

- [ ] **Step 10: Commit**

```bash
git add src/frontend/src/features/gate/gate-panel.tsx src/frontend/src/features/gate/gate-page.tsx src/frontend/src/features/gate/gate-panel.test.tsx src/frontend/src/features/gate/gate-page.test.tsx src/frontend/src/components/app-shell.tsx
git commit -m "feat(gate): viewport-fit layout and keyboard-routed confirm/manual/cancel/pay"
```

---

## Task 8: Full frontend verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full test suite**

Run: `cd src/frontend && npx vitest run`
Expected: PASS. If `payment-dialog.test.tsx` still referenced anywhere, remove the stale import.

- [ ] **Step 2: Typecheck and lint**

Run: `cd src/frontend && npx tsc --noEmit && npx eslint src/features/gate --max-warnings 0`
Expected: no errors.

- [ ] **Step 3: Build**

Run: `cd src/frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit any fixups**

```bash
git add -A src/frontend
git commit -m "chore(gate): typecheck, lint, build green after gate flow pass"
```

---

## Self-Review Notes

- Spec A (camera states) -> Tasks 1, 2. B (plate always editable + Nhận lại) -> Task 6 (`savePlate` ungated, `Nhận lại`). C (readable result + swatch) -> Tasks 3, 4. D (fit viewport) -> Tasks 2 (capped camera), 7 (flex fill, contained scroll, app-shell). E (validation: empty plate block, plateless explicit, manual group, double-submit guard) -> Task 6. F (inline pay) -> Tasks 5, 6. G (keyboard wired) -> Task 7.
- Type consistency: `GatePanelHandle` (Task 7) and `DecisionPanelHandle` (Task 6) share `confirm/manual/cancel/payMethod/focusPlate`; `payMethod(n: number)` used consistently; `PAY_METHODS` order (`cash`,`qr`,`ewallet`) drives `payMethod(n)` index in both files.
- No placeholders: all steps contain full file contents or exact single-line edits.
- Manual exit path intentionally guides to candidate selection (backend requires `session_id`); no manual-exit submit is attempted without a chosen session, avoiding the 422.
