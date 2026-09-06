import { CapturePreview } from "@/components/capture-preview";
import { CameraImageGrid, type CameraImage } from "@/components/camera-image-grid";
import { StatusChip } from "@/components/status-chip";
import { formatDateTime, formatPlate } from "@/lib/format";

// Hai ảnh bằng chứng đặt cạnh nhau để đối chiếu (thường là lúc VÀO và lúc RA).
// Trước đây bố cục này chỉ có ở trang chi tiết phiên, còn màn Trạm cổng lúc cho
// xe ra chỉ thấy ảnh vừa chụp nên nhân viên không có gì để so trước khi thu tiền.
export type EvidenceSide = {
  title: string;
  imageAssetId?: number | null;
  /** Ảnh vừa chụp tại máy: dùng thẳng object URL, khỏi tải lại qua /images/{id}. */
  localUrl?: string | null;
  plateCropAssetId?: number | null;
  plateText?: string | null;
  reviewState?: string | null;
  at?: string | null;
  lane?: string | null;
  // Ảnh của mọi camera đã lưu cho lượt này (làn đa camera); rỗng/undefined thì
  // chỉ có 1 ảnh chính, hiện như trước — không đổi hành vi màn hình đơn camera.
  images?: { role: string; image_asset_id: number; is_primary: boolean }[];
};

function Side({ side }: { side: EvidenceSide }) {
  const cameraImages: CameraImage[] =
    side.images && side.images.length > 1
      ? side.images.map((img) => ({
          role: img.role,
          imageAssetId: img.image_asset_id,
          localUrl: img.is_primary ? side.localUrl : null,
        }))
      : [];

  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] font-medium text-ink">{side.title}</span>
        {side.reviewState && <StatusChip kind="review" value={side.reviewState} />}
      </div>

      <div className="h-32">
        {cameraImages.length > 0 ? (
          <CameraImageGrid images={cameraImages} fit="contain" />
        ) : (
          <CapturePreview localUrl={side.localUrl} imageAssetId={side.imageAssetId} fit="contain" />
        )}
      </div>

      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-[12px] text-muted">
        <span className="tnum font-medium text-ink">{formatPlate(side.plateText)}</span>
        <span className="tnum">{formatDateTime(side.at)}</span>
        {side.lane && <span>làn {side.lane}</span>}
      </div>

      {side.plateCropAssetId != null && (
        <div className="h-12">
          <CapturePreview imageAssetId={side.plateCropAssetId} fit="contain" />
        </div>
      )}
    </div>
  );
}

export function EvidencePair({ left, right }: { left: EvidenceSide; right: EvidenceSide }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <Side side={left} />
      <Side side={right} />
    </div>
  );
}
