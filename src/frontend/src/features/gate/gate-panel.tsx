import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { toast } from "sonner";
import { CameraView } from "./camera-view";
import { CapturePreview } from "./capture-preview";
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
  reset: () => void;
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
    wide?: boolean;
  }
>(function GatePanel({ direction, wsCapture, active, onActivate, onPayOpenChange, wide = false }, ref) {
  const cam = useCamera();
  const [capture, setCapture] = useState<GateCapture | null>(null);
  const [busy, setBusy] = useState(false);
  const decisionRef = useRef<DecisionPanelHandle | null>(null);

  // Giữ object URL của khung hình cục bộ; thu hồi khi thay/đóng để tránh rò bộ nhớ.
  const localUrlRef = useRef<string | null>(null);
  const setCaptureWithUrl = (next: GateCapture | null, localUrl?: string) => {
    if (localUrlRef.current) URL.revokeObjectURL(localUrlRef.current);
    localUrlRef.current = localUrl ?? null;
    setCapture(next);
  };

  useEffect(() => {
    cam.requestPermission();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (cam.deviceId) cam.start(cam.deviceId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cam.deviceId]);
  useEffect(() => {
    if (wsCapture) setCaptureWithUrl(wsCapture);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsCapture]);
  useEffect(
    () => () => {
      if (localUrlRef.current) URL.revokeObjectURL(localUrlRef.current);
    },
    [],
  );

  const doCapture = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const blob = await cam.capture();
      if (!blob) {
        toast.error("Chưa có khung hình từ camera");
        return;
      }
      const localUrl = URL.createObjectURL(blob);
      const res = await postInfer(blob, direction, crypto.randomUUID());
      setCaptureWithUrl({ ...(res as unknown as GateCapture), local_image_url: localUrl }, localUrl);
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
    reset: () => decisionRef.current?.reset(),
    cancel: () => decisionRef.current?.cancel(),
    payMethod: (n) => decisionRef.current?.payMethod(n),
  }));

  const figureClass = wide
    ? "relative m-0 min-h-0 h-full overflow-hidden"
    : "relative m-0 aspect-video max-h-[24dvh] overflow-hidden";

  const cameraFigure = (
    <figure className={figureClass}>
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
    </figure>
  );

  const captureFigure = (
    <figure className={figureClass}>
      <CapturePreview localUrl={capture?.local_image_url} imageAssetId={capture?.image_asset_id} />
      {capture && (
        <figcaption className="absolute bottom-1.5 left-2 rounded bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">
          Ảnh đã chụp
        </figcaption>
      )}
    </figure>
  );

  const decisionArea = capture ? (
    <DecisionPanel
      ref={decisionRef}
      capture={capture}
      direction={direction}
      onDone={() => setCaptureWithUrl(null)}
      onRecapture={doCapture}
      onPayOpenChange={onPayOpenChange}
    />
  ) : (
    <EmptyState title="Chưa có lượt chụp" hint="Bấm Chụp hoặc chờ sự kiện cổng" />
  );

  return (
    <div
      onClick={onActivate}
      className={active ? "h-full rounded-[var(--radius-card)] ring-2 ring-ink" : "h-full"}
    >
      <SurfaceCard variant="white" className="flex h-full flex-col gap-3 overflow-hidden">
        <h2 className="text-sm font-semibold">{direction === "in" ? "Hướng VÀO" : "Hướng RA"}</h2>

        {wide ? (
          // Một hướng: cột trái 50% chứa hai khung ảnh xếp dọc, cột phải là bảng điều khiển.
          <div className="grid min-h-0 flex-1 grid-rows-1 grid-cols-2 gap-3">
            <div className="grid min-h-0 grid-rows-2 gap-2">
              {cameraFigure}
              {captureFigure}
            </div>
            <div className="min-h-0 overflow-auto">{decisionArea}</div>
          </div>
        ) : (
          // Chia đôi: hàng media (camera trái, ảnh chụp phải) ở trên, bảng điều khiển ở dưới.
          <>
            <div className="grid shrink-0 grid-cols-2 gap-2">
              {cameraFigure}
              {captureFigure}
            </div>
            <div className="min-h-0 flex-1 overflow-auto">{decisionArea}</div>
          </>
        )}
      </SurfaceCard>
    </div>
  );
});
