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
            <Button className="h-10" onClick={onRequestPermission} disabled={status === "requesting"}>
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
