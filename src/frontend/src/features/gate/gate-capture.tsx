import { useEffect, useState } from "react";
import type { GateCapture } from "./use-gate-socket";
import { fetchImageObjectUrl } from "@/lib/image-blob";
import { SurfaceCard } from "@/components/surface-card";
import { useVehicleGroupMap, groupLabel } from "@/lib/vehicle-groups";

function Chip({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <span className="rounded-full border border-line bg-bg px-2.5 py-1 text-[13px] text-ink">
      {label}: {value}
    </span>
  );
}

export function GateCaptureView({ capture }: { capture: GateCapture | null }) {
  const groupMap = useVehicleGroupMap();
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    if (capture?.image_asset_id) {
      fetchImageObjectUrl(capture.image_asset_id)
        .then((u) => {
          url = u;
          setImgUrl(u);
        })
        .catch(() => setImgUrl(null));
    } else {
      setImgUrl(null);
    }
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [capture?.image_asset_id]);

  return (
    <SurfaceCard variant="white" className="space-y-3">
      <div className="flex aspect-video items-center justify-center overflow-hidden rounded-[var(--radius-control)] bg-surface">
        {imgUrl ? (
          <img src={imgUrl} alt="Khung camera" className="h-full w-full object-cover" />
        ) : (
          <span className="text-muted">Chờ ảnh</span>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <Chip label="Loại xe" value={capture?.vehicle_type} />
        <Chip label="Nhóm phí" value={capture?.vehicle_group ? groupLabel(groupMap, capture.vehicle_group) : null} />
        <Chip label="Màu biển" value={capture?.color} />
      </div>
    </SurfaceCard>
  );
}
