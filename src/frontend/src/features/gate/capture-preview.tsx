import { useEffect, useState } from "react";
import { fetchImageObjectUrl } from "@/lib/image-blob";

// Ảnh khung hình đã chụp cho màn Trạm cổng. Ưu tiên object URL cục bộ (đúng khung
// nhân viên vừa gửi model, không cần gọi lại server). Nếu chỉ có image_asset_id
// (capture đến từ WS/edge) thì tải ảnh đã mã hoá qua /images/{id} (có audit).
export function CapturePreview({
  localUrl,
  imageAssetId,
  fit = "cover",
}: {
  localUrl?: string | null;
  imageAssetId?: number | null;
  fit?: "cover" | "contain";
}) {
  const [fetched, setFetched] = useState<string | null>(null);

  useEffect(() => {
    if (localUrl || !imageAssetId) {
      setFetched(null);
      return;
    }
    let active = true;
    let url: string | null = null;
    fetchImageObjectUrl(imageAssetId)
      .then((u) => {
        if (!active) {
          URL.revokeObjectURL(u);
          return;
        }
        url = u;
        setFetched(u);
      })
      .catch(() => {});
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [localUrl, imageAssetId]);

  const src = localUrl ?? fetched;
  if (!src) {
    return (
      <div className="flex h-full w-full items-center justify-center rounded-[var(--radius-control)] border border-dashed border-line bg-surface text-[13px] text-muted">
        Không có ảnh
      </div>
    );
  }
  return (
    <img
      src={src}
      alt="Khung hình đã chụp"
      className={`h-full w-full rounded-[var(--radius-control)] border border-line ${
        fit === "contain" ? "object-contain" : "object-cover"
      }`}
    />
  );
}
