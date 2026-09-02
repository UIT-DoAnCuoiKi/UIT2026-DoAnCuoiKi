import type { RefObject } from "react";
import type { CameraDevice, CameraStatus } from "./use-camera";
import { Button } from "@/components/ui/button";

// Ô camera trực tiếp lấp đầy nửa trái của hàng media. Khi đang stream, thanh
// điều khiển (chọn camera + Chụp) nổi lên trên video để không chiếm chiều cao.
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
    <div className="relative flex h-full w-full flex-col overflow-hidden rounded-[var(--radius-control)] border border-line bg-surface">
      {streaming ? (
        <>
          <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
          <div className="absolute inset-x-0 top-0 flex items-center gap-2 bg-gradient-to-b from-black/55 to-transparent p-2">
            <select
              aria-label="Chọn camera"
              className="h-8 min-w-0 flex-1 rounded-[var(--radius-control)] border border-line bg-bg/90 px-2 text-[12px]"
              value={deviceId ?? ""}
              onChange={(e) => onSelectDevice(e.target.value)}
            >
              {devices.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label}
                </option>
              ))}
            </select>
            <Button className="h-8 shrink-0 px-3" onClick={onCapture}>
              Chụp
            </Button>
          </div>
          <span className="absolute bottom-1.5 left-2 rounded bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">
            Trực tiếp
          </span>
        </>
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-4 text-center">
          <p className="text-sm font-medium text-ink">
            {status === "requesting" && "Đang mở camera..."}
            {status === "no-device" && "Không tìm thấy camera"}
            {status === "denied" && "Chưa cấp quyền camera"}
            {(status === "error" || status === "idle") && "Camera chưa kết nối"}
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button className="h-9" onClick={onRequestPermission} disabled={status === "requesting"}>
              {status === "denied" ? "Cấp quyền camera" : "Kết nối lại"}
            </Button>
            <Button variant="outline" className="h-9" onClick={onManual}>
              Nhập tay
            </Button>
          </div>
          {error && <p className="text-[13px] text-st-amber">{error}</p>}
        </div>
      )}
    </div>
  );
}
