import { CapturePreview } from "@/components/capture-preview";
import { cameraRoleLabel } from "@/lib/labels";

export type CameraImage = {
  role: string;
  imageAssetId: number;
  /** Chỉ ảnh chính (vừa chụp tại máy) mới có, dùng object URL cục bộ thay vì tải lại qua /images/{id}. */
  localUrl?: string | null;
};

// Ô hiển thị đủ ảnh của mọi camera trong 1 lượt (làn đa camera), chia đều
// không gian thay vì chỉ hiện ảnh chính rồi giấu ảnh phụ đi đâu không rõ.
// 2 camera (phổ biến nhất: trước + sau) thì đúng tỉ lệ 50/50.
export function CameraImageGrid({ images, fit = "cover" }: { images: CameraImage[]; fit?: "cover" | "contain" }) {
  return (
    <div className={`grid h-full w-full gap-1 ${images.length >= 2 ? "grid-cols-2" : "grid-cols-1"}`}>
      {images.map((img) => (
        <div
          key={img.imageAssetId}
          className="relative h-full w-full overflow-hidden rounded-[var(--radius-control)] border border-line"
        >
          <CapturePreview localUrl={img.localUrl} imageAssetId={img.imageAssetId} fit={fit} />
          <span className="absolute bottom-1 left-1.5 rounded bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">
            {cameraRoleLabel(img.role)}
          </span>
        </div>
      ))}
    </div>
  );
}
