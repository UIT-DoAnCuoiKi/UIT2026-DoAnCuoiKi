import { useEffect, useState, type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { useSessionDetail, useUpdateSession } from "@/api/generated/sessions/sessions";
import { StatusChip } from "@/components/status-chip";
import { SurfaceCard } from "@/components/surface-card";
import { CameraImageGrid } from "@/components/camera-image-grid";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DisputePanel } from "./dispute-panel";
import { fetchImageObjectUrl } from "@/lib/image-blob";
import { formatPlate, formatVnd, formatDateTime, formatDuration } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";
import { useVehicleGroupMap, groupLabel } from "@/lib/vehicle-groups";
import { vehicleTypeLabel, matchFlagLabel, VEHICLE_TYPE_OPTIONS } from "@/lib/labels";
import { plateColor, PLATE_COLOR_OPTIONS } from "@/features/gate/plate-color";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-[13px] text-muted">{label}</dt>
      <dd className="tnum text-sm font-medium">{children}</dd>
    </div>
  );
}

// Ảnh bằng chứng hiện luôn khi mở phiên (không cần bấm). Mỗi lần tải vẫn được
// backend ghi audit. Giữ chỗ bằng skeleton để tránh nhảy layout (CLS).
// `size`: "main" cho ảnh xe (to, để nhân viên đối chiếu), "crop" cho ảnh biển
// đã xử lý màu (nhỏ, chỉ để tham khảo thêm).
function Evidence({ imageId, size = "main" }: { imageId?: number | null; size?: "main" | "crop" }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!imageId) return;
    let alive = true;
    let objUrl: string | null = null;
    setUrl(null);
    setFailed(false);
    fetchImageObjectUrl(imageId)
      .then((u) => {
        objUrl = u;
        if (alive) setUrl(u);
        else URL.revokeObjectURL(u);
      })
      .catch(() => {
        if (alive) setFailed(true);
      });
    return () => {
      alive = false;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [imageId]);

  const boxClass = size === "main" ? "h-64 sm:h-80" : "h-24";
  if (!imageId)
    return (
      <div className={`flex ${boxClass} w-full items-center justify-center rounded-[var(--radius-control)] bg-faint text-[13px] text-muted`}>
        Không có ảnh
      </div>
    );
  if (failed)
    return (
      <div className={`flex ${boxClass} w-full items-center justify-center rounded-[var(--radius-control)] bg-faint text-[13px] text-muted`}>
        Không tải được ảnh
      </div>
    );
  if (!url) return <Skeleton className={`${boxClass} w-full`} />;
  return (
    <div className={`${boxClass} w-full overflow-hidden rounded-[var(--radius-control)] bg-faint`}>
      <img src={url} alt="Ảnh bằng chứng" className="h-full w-full object-contain" />
    </div>
  );
}

function EditClassification({
  sessionId,
  vehicleType,
  color,
  onSaved,
}: {
  sessionId: number;
  vehicleType?: string | null;
  color?: string | null;
  onSaved: () => void;
}) {
  const update = useUpdateSession();
  const [vType, setVType] = useState(vehicleType ?? "");
  const [c, setC] = useState(color ?? "");
  useEffect(() => setVType(vehicleType ?? ""), [vehicleType]);
  useEffect(() => setC(color ?? ""), [color]);
  const dirty = vType !== (vehicleType ?? "") || c !== (color ?? "");
  const save = async () => {
    if (!dirty || update.isPending) return;
    try {
      await update.mutateAsync({ sessionId, data: { vehicle_type: vType || null, color: c || null } });
      toast.success("Đã cập nhật phân loại");
      onSaved();
    } catch {
      toast.error("Cập nhật thất bại");
    }
  };
  return (
    <SurfaceCard variant="white" className="space-y-3">
      <p className="text-sm font-semibold">Chỉnh phân loại</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="edit-vtype" className="mb-1 block text-[12px] text-muted">
            Loại xe
          </label>
          <select
            id="edit-vtype"
            aria-label="Loại xe"
            className="h-9 w-full rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
            value={vType}
            onChange={(e) => setVType(e.target.value)}
          >
            <option value="">—</option>
            {VEHICLE_TYPE_OPTIONS.map((o) => (
              <option key={o.code} value={o.code}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="edit-color" className="mb-1 block text-[12px] text-muted">
            Màu biển
          </label>
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block h-4 w-4 shrink-0 rounded-full border border-line"
              style={{ background: plateColor(c)?.swatch ?? "transparent" }}
            />
            <select
              id="edit-color"
              aria-label="Màu biển"
              className="h-9 w-full rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
              value={c}
              onChange={(e) => setC(e.target.value)}
            >
              <option value="">—</option>
              {PLATE_COLOR_OPTIONS.map((o) => (
                <option key={o.code} value={o.code}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
      <div className="flex justify-end">
        <Button variant="outline" className="h-9" onClick={save} disabled={!dirty || update.isPending}>
          {update.isPending ? "Đang lưu" : "Lưu phân loại"}
        </Button>
      </div>
    </SurfaceCard>
  );
}

export function SessionDetailPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const { data, isLoading, refetch } = useSessionDetail(sessionId);
  const groupMap = useVehicleGroupMap();

  if (isLoading) return <EmptyState title="Đang tải..." />;
  if (!data) return <EmptyState title="Không tìm thấy phiên" />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <h1 className="tnum text-lg font-semibold">{formatPlate(data.plate_text)}</h1>
        <StatusChip kind="session" value={data.status} />
        {/* Giống dòng đầu phiếu thu ở Trạm cổng: giờ vào luôn hiện, còn giờ ra
            hay thời lượng đang đậu thì tuỳ trạng thái — trước đây phải kéo
            xuống bảng dữ liệu bên dưới mới thấy, không có ngay ở đầu trang. */}
        <span className="text-[13px] text-muted">
          Giờ vào: <span className="tnum font-medium text-ink">{formatDateTime(data.entry_time)}</span>
        </span>
        {data.exit_time ? (
          <span className="text-[13px] text-muted">
            Giờ ra: <span className="tnum font-medium text-ink">{formatDateTime(data.exit_time)}</span>
          </span>
        ) : (
          <span className="text-[13px] text-muted">
            Đã đậu: <span className="tnum font-medium text-ink">{formatDuration(data.entry_time, new Date().toISOString())}</span>
          </span>
        )}
      </div>

      {/* Ảnh là căn cứ đối chiếu chính, đưa lên đầu trang thay vì nằm dưới các
          bảng dữ liệu: trái là lúc VÀO, phải là lúc RA, nhân viên nhìn 1 lần
          là so sánh được ngay, không phải cuộn xuống mới thấy ảnh. */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SurfaceCard variant="white" className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold">Lúc VÀO</p>
            {data.entry_reading && (
              <StatusChip kind="review" value={data.entry_reading.review_state ?? "confident"} />
            )}
          </div>
          <p className="tnum text-[13px] text-muted">{formatDateTime(data.entry_time)}</p>
          {data.entry_reading?.images && data.entry_reading.images.length > 1 ? (
            <div className="h-64 sm:h-80">
              <CameraImageGrid
                images={data.entry_reading.images.map((img) => ({ role: img.role, imageAssetId: img.image_asset_id }))}
              />
            </div>
          ) : (
            <Evidence imageId={data.entry_reading?.image_asset_id} />
          )}
          {data.entry_reading?.plate_crop_asset_id != null && (
            <div className="space-y-1">
              <p className="text-[13px] text-muted">Biển đã xử lý màu</p>
              <Evidence imageId={data.entry_reading.plate_crop_asset_id} size="crop" />
            </div>
          )}
        </SurfaceCard>
        <SurfaceCard variant="white" className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold">Lúc RA</p>
            {data.exit_reading && (
              <StatusChip kind="review" value={data.exit_reading.review_state ?? "confident"} />
            )}
          </div>
          <p className="tnum text-[13px] text-muted">{formatDateTime(data.exit_time)}</p>
          {data.exit_reading?.images && data.exit_reading.images.length > 1 ? (
            <div className="h-64 sm:h-80">
              <CameraImageGrid
                images={data.exit_reading.images.map((img) => ({ role: img.role, imageAssetId: img.image_asset_id }))}
              />
            </div>
          ) : (
            <Evidence imageId={data.exit_reading?.image_asset_id} />
          )}
          {data.exit_reading?.plate_crop_asset_id != null && (
            <div className="space-y-1">
              <p className="text-[13px] text-muted">Biển đã xử lý màu</p>
              <Evidence imageId={data.exit_reading.plate_crop_asset_id} size="crop" />
            </div>
          )}
        </SurfaceCard>
      </div>

      <SurfaceCard variant="white">
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Field label="Nhóm xe">{groupLabel(groupMap, data.vehicle_group)}</Field>
          <Field label="Loại xe">{vehicleTypeLabel(data.vehicle_type)}</Field>
          <Field label="Màu biển">
            {(() => {
              const c = plateColor(data.color);
              return c ? (
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="inline-block h-3.5 w-3.5 shrink-0 rounded-full border border-line"
                    style={{ background: c.swatch }}
                  />
                  {c.label}
                </span>
              ) : (
                "—"
              );
            })()}
          </Field>
          <Field label="Giờ vào">{formatDateTime(data.entry_time)}</Field>
          <Field label="Giờ ra">{formatDateTime(data.exit_time)}</Field>
          <Field label="Thời lượng">{formatDuration(data.entry_time, data.exit_time)}</Field>
          <Field label="Phí">{formatVnd(data.fee_amount)}</Field>
          <Field label="Khớp">{matchFlagLabel(data.match_flag)}</Field>
          <Field label="Cảnh báo">{data.warning ?? "—"}</Field>
          <Field label="Nhân viên vào">{data.created_by_name ?? "—"}</Field>
          <Field label="Nhân viên ra">{data.closed_by_name ?? "—"}</Field>
          {/* Dữ liệu đã có sẵn trên PlateReading.lane từ trước, chỉ chưa lộ ra
              màn này — không tra được xe vào/ra ở làn nào để đối chiếu camera. */}
          <Field label="Làn vào">{data.entry_reading?.lane ?? "—"}</Field>
          <Field label="Làn ra">{data.exit_reading?.lane ?? "—"}</Field>
          <Field label="Bãi">{data.lot_name ?? "—"}</Field>
          <Field label="Khu">{data.zone_name ?? "—"}</Field>
        </dl>
      </SurfaceCard>

      <EditClassification
        sessionId={sessionId}
        vehicleType={data.vehicle_type}
        color={data.color}
        onSaved={() => refetch()}
      />

      <SurfaceCard variant="white" className="space-y-2">
        <p className="text-sm font-semibold">Thanh toán</p>
        {data.payments && data.payments.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted">
                <th className="py-1">Số tiền</th>
                <th>Phương thức</th>
                <th>Loại</th>
                <th>Nhân viên</th>
                <th>Giờ</th>
              </tr>
            </thead>
            <tbody>
              {data.payments.map((p) => (
                <tr key={p.id} className="tnum">
                  <td className="py-1">{formatVnd(p.amount)}</td>
                  <td>{p.method}</td>
                  <td>{p.kind}</td>
                  <td>{p.staff_name ?? "—"}</td>
                  <td>{formatDateTime(p.paid_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-muted">Chưa có thanh toán</p>
        )}
      </SurfaceCard>

      {data.fee_rule_snapshot && (
        <SurfaceCard variant="white" className="space-y-1">
          <p className="text-sm font-semibold">Cách tính phí</p>
          <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-3">
            {Object.entries(data.fee_rule_snapshot).map(([k, v]) => (
              <div key={k}>
                <dt className="text-[13px] text-muted">{k}</dt>
                <dd className="tnum">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </SurfaceCard>
      )}

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
