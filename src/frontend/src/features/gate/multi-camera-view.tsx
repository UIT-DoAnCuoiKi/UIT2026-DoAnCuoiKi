import { useRef } from "react";
import type { CameraSlot } from "./use-cameras";
import type { LaneCameraOut } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { cameraRoleLabel } from "@/lib/labels";

// Bản nhiều camera của CameraView: mỗi camera cấu hình cho làn (LaneCameraOut)
// chiếm 1 ô. Camera RTSP không phát được trực tiếp trong trình duyệt (xem
// lanes-tab.tsx) nên chỉ hiện trạng thái, không cố mở stream.
function Tile({
  cam,
  slot,
  onRequestPermission,
  onUploadForRole,
  allowUpload,
}: {
  cam: LaneCameraOut;
  slot?: CameraSlot;
  onRequestPermission: (role: string) => void;
  onUploadForRole: (role: string, file: File) => void;
  allowUpload: boolean;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const label = cameraRoleLabel(cam.role);

  if (cam.source_kind === "rtsp") {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-1 rounded-[var(--radius-control)] border border-line bg-surface p-2 text-center">
        <span className="text-[12px] font-medium text-ink">{label} · RTSP</span>
        <span className="text-[11px] text-muted">Chạy qua thiết bị biên, không xem trực tiếp ở đây</span>
      </div>
    );
  }

  const streaming = slot?.status === "streaming";
  return (
    <div className="relative h-full w-full overflow-hidden rounded-[var(--radius-control)] border border-line bg-surface">
      {allowUpload && (
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) onUploadForRole(cam.role, file);
          }}
          aria-label={`Tải ảnh ${label}`}
        />
      )}
      {streaming && slot ? (
        <>
          <video ref={slot.videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
          {/* Nút này phải có cả khi camera ĐANG chạy, giống CameraView (1 camera):
              thiếu nó thì máy có webcam cắm sẵn không còn cách nào tải ảnh mẫu để
              thử pipeline, vì ô camera không bao giờ rơi về nhánh "chưa kết nối". */}
          {allowUpload && (
            <Button
              variant="outline"
              className="absolute right-1 top-1 h-7 px-2 text-[11px]"
              onClick={() => fileInputRef.current?.click()}
            >
              Tải ảnh
            </Button>
          )}
          <span className="absolute bottom-1 left-1.5 rounded bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">
            {label}
          </span>
        </>
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-1.5 p-2 text-center">
          <span className="text-[12px] font-medium text-ink">{label}</span>
          <span className="text-[11px] text-muted">
            {slot?.status === "requesting" ? "Đang mở..." : "Chưa kết nối"}
          </span>
          <div className="flex flex-wrap justify-center gap-1">
            <Button variant="outline" className="h-7 px-2 text-[11px]" onClick={() => onRequestPermission(cam.role)}>
              Kết nối
            </Button>
            {allowUpload && (
              <Button variant="outline" className="h-7 px-2 text-[11px]" onClick={() => fileInputRef.current?.click()}>
                Tải ảnh
              </Button>
            )}
          </div>
          {slot?.error && <span className="text-[10px] text-st-amber">{slot.error}</span>}
        </div>
      )}
    </div>
  );
}

export function MultiCameraView({
  cameras,
  slots,
  onRequestPermission,
  onUploadForRole,
  allowUpload = false,
}: {
  cameras: LaneCameraOut[];
  slots: CameraSlot[];
  onRequestPermission: (role: string) => void;
  onUploadForRole: (role: string, file: File) => void;
  allowUpload?: boolean;
}) {
  const byRole = Object.fromEntries(slots.map((s) => [s.role, s]));
  return (
    <div className={`grid h-full w-full gap-1.5 ${cameras.length >= 2 ? "grid-cols-2" : "grid-cols-1"}`}>
      {cameras.map((cam) => (
        <Tile
          key={cam.id}
          cam={cam}
          slot={byRole[cam.role]}
          onRequestPermission={onRequestPermission}
          onUploadForRole={onUploadForRole}
          allowUpload={allowUpload}
        />
      ))}
    </div>
  );
}
