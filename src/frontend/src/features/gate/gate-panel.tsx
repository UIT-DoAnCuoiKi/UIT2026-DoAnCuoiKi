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
