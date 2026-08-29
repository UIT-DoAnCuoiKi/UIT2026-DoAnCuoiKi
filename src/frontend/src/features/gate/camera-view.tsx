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
