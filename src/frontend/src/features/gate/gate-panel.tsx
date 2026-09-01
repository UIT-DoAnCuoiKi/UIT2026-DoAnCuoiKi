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
    cancel: () => decisionRef.current?.cancel(),
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
