import { useState, type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { useSessionDetail } from "@/api/generated/sessions/sessions";
import { StatusChip } from "@/components/status-chip";
import { SurfaceCard } from "@/components/surface-card";
import { Button } from "@/components/ui/button";
import { DisputePanel } from "./dispute-panel";
import { fetchImageObjectUrl } from "@/lib/image-blob";
import { formatPlate, formatVnd, formatDateTime, formatDuration } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-[13px] text-muted">{label}</dt>
      <dd className="tnum text-sm font-medium">{children}</dd>
    </div>
  );
}

function Evidence({ imageId }: { imageId?: number | null }) {
  const [url, setUrl] = useState<string | null>(null);
  if (!imageId) return <span className="text-muted">Không có ảnh</span>;
  if (!url)
    return (
      <Button variant="outline" size="sm" onClick={async () => setUrl(await fetchImageObjectUrl(imageId))}>
        Xem ảnh bằng chứng
      </Button>
    );
  return <img src={url} alt="Ảnh bằng chứng" className="max-h-48 rounded-[var(--radius-control)]" />;
}

export function SessionDetailPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const { data, isLoading, refetch } = useSessionDetail(sessionId);

  if (isLoading) return <EmptyState title="Đang tải..." />;
  if (!data) return <EmptyState title="Không tìm thấy phiên" />;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="tnum text-lg font-semibold">{formatPlate(data.plate_text)}</h1>
        <StatusChip kind="session" value={data.status} />
      </div>
      <SurfaceCard variant="white">
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Field label="Nhóm xe">{data.vehicle_group ?? "—"}</Field>
          <Field label="Loại xe">{data.vehicle_type ?? "—"}</Field>
          <Field label="Giờ vào">{formatDateTime(data.entry_time)}</Field>
          <Field label="Giờ ra">{formatDateTime(data.exit_time)}</Field>
          <Field label="Thời lượng">{formatDuration(data.entry_time, data.exit_time)}</Field>
          <Field label="Phí">{formatVnd(data.fee_amount)}</Field>
          <Field label="Khớp">{data.match_flag ?? "—"}</Field>
          <Field label="Cảnh báo">{data.warning ?? "—"}</Field>
        </dl>
      </SurfaceCard>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SurfaceCard variant="white" className="space-y-2">
          <p className="text-sm font-semibold">Ảnh vào</p>
          {data.entry_reading && (
            <StatusChip kind="review" value={data.entry_reading.review_state ?? "confident"} />
          )}
          <Evidence imageId={data.entry_reading?.image_asset_id} />
        </SurfaceCard>
        <SurfaceCard variant="white" className="space-y-2">
          <p className="text-sm font-semibold">Ảnh ra</p>
          {data.exit_reading && (
            <StatusChip kind="review" value={data.exit_reading.review_state ?? "confident"} />
          )}
          <Evidence imageId={data.exit_reading?.image_asset_id} />
        </SurfaceCard>
      </div>

      <p className="text-[13px] text-muted">
        Việc truy cập ảnh bằng chứng được hệ thống ghi lại (audit). Dữ liệu tự xóa sau 30 ngày kể từ khi
        xe ra.
      </p>

      <SurfaceCard variant="surface">
        <DisputePanel sessionId={sessionId} onChanged={() => refetch()} />
      </SurfaceCard>
    </div>
  );
}
