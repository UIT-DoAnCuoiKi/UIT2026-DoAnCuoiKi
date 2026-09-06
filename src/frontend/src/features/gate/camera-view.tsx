import { useRef, type RefObject } from "react";
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
  onUpload,
  error,
  // Tải ảnh thay camera thật chỉ dành cho test/demo (ảnh đi thẳng vào pipeline
  // nhận dạng như ảnh chụp thật) — ẩn khỏi vận hành thật trừ khi bật dev_mode
  // trong Cấu hình, tránh ai đó thay ảnh gốc bằng ảnh tuỳ ý.
  allowUpload = false,
}: {
  videoRef: RefObject<HTMLVideoElement | null>;
  devices: CameraDevice[];
  deviceId: string | null;
  status: CameraStatus;
  onSelectDevice: (id: string) => void;
  onCapture: () => void;
  onRequestPermission: () => void;
  onManual: () => void;
  onUpload: (file: File) => void;
  error: string | null;
  allowUpload?: boolean;
}) {
  const streaming = status === "streaming";
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pickFile = () => fileInputRef.current?.click();
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // cho chọn lại đúng file cũ lần sau vẫn bắn onChange
    if (file) onUpload(file);
  };
  const fileInput = allowUpload && (
    <input
      ref={fileInputRef}
      type="file"
      accept="image/*"
      hidden
      onChange={handleFileChange}
      aria-label="Tải ảnh lên"
    />
  );

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden rounded-[var(--radius-control)] border border-line bg-surface">
      {fileInput}
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
            {allowUpload && (
              <Button variant="outline" className="h-8 shrink-0 px-2 text-[12px]" onClick={pickFile}>
                Tải ảnh
              </Button>
            )}
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
            {allowUpload && (
              <Button variant="outline" className="h-9" onClick={pickFile}>
                Tải ảnh lên
              </Button>
            )}
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
