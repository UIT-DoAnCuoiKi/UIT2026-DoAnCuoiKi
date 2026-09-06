import type { ExitPreview } from "@/api/generated/model";
import { EvidencePair } from "@/components/evidence-pair";
import { Button } from "@/components/ui/button";
import { formatDateTime, formatMinutes, formatVnd } from "@/lib/format";

// Màn xác minh trước khi cho xe RA: đặt ảnh lúc VÀO cạnh ảnh vừa chụp, kèm giờ
// vào / giờ ra / thời lượng / diễn giải phí. Trước đây nhân viên chỉ thấy đúng
// một con số tiền, không có căn cứ nào để biết phí đó tính cho xe nào, gửi bao lâu.

/** Diễn giải cách ra số tiền, dựng từ `fee_rule_snapshot` của backend. */
export function feeExplanation(snapshot?: Record<string, unknown> | null): string | null {
  if (!snapshot) return null;
  const mode = snapshot.mode as string | undefined;
  const unit = snapshot.unit_price as number | undefined;

  if (snapshot.exempt) return "Miễn phí (vé tháng hoặc danh sách trắng)";
  if (snapshot.free) return `Trong thời gian miễn phí (${snapshot.grace_minutes} phút đầu)`;
  if (mode === "flat" && unit != null) return `Giá trọn lượt ${formatVnd(unit)}`;
  if (mode === "block" && unit != null) {
    const blocks = snapshot.blocks as number | undefined;
    const per = snapshot.block_minutes as number | undefined;
    const base = `${blocks} block × ${formatVnd(unit)} (mỗi block ${per} phút)`;
    return snapshot.capped ? `${base} — đã chạm trần ${formatVnd(snapshot.daily_cap as number)}/ngày` : base;
  }
  return null;
}

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex min-w-0 flex-col">
      <span className="text-[12px] text-muted">{label}</span>
      <span className={`tnum text-sm ${strong ? "font-semibold text-ink" : "font-medium"}`}>{value}</span>
    </div>
  );
}

export function ExitReview({
  preview,
  exitLocalUrl,
  onConfirm,
  onCancel,
  busy,
}: {
  preview: ExitPreview;
  /** Ảnh vừa chụp tại máy (nếu có) để khỏi tải lại qua /images/{id}. */
  exitLocalUrl?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  const s = preview.session;
  const explanation = feeExplanation(preview.fee_rule_snapshot as Record<string, unknown> | null);

  return (
    <div className="space-y-3">
      <EvidencePair
        left={{
          title: "Lúc VÀO",
          imageAssetId: preview.entry_reading?.image_asset_id,
          plateCropAssetId: preview.entry_reading?.plate_crop_asset_id,
          plateText: preview.entry_reading?.plate_text ?? s?.plate_text,
          reviewState: preview.entry_reading?.review_state,
          at: preview.entry_reading?.created_at ?? s?.entry_time,
          lane: preview.entry_reading?.lane,
          images: preview.entry_reading?.images,
        }}
        right={{
          title: "Lúc RA (vừa chụp)",
          localUrl: exitLocalUrl,
          imageAssetId: preview.exit_reading?.image_asset_id,
          plateCropAssetId: preview.exit_reading?.plate_crop_asset_id,
          plateText: preview.exit_reading?.plate_text,
          reviewState: preview.exit_reading?.review_state,
          at: preview.exit_reading?.created_at,
          lane: preview.exit_reading?.lane,
          images: preview.exit_reading?.images,
        }}
      />

      <div className="grid grid-cols-2 gap-3 rounded-[var(--radius-control)] border border-line bg-surface px-3 py-2 sm:grid-cols-4">
        <Row label="Giờ vào" value={formatDateTime(s?.entry_time)} />
        <Row label="Giờ ra" value={formatDateTime(preview.exit_reading?.created_at)} />
        <Row label="Thời lượng" value={formatMinutes(preview.minutes)} />
        <Row
          label="Phí dự tính"
          value={preview.fee_amount != null ? formatVnd(preview.fee_amount) : "—"}
          strong
        />
      </div>

      {explanation && <p className="text-[12px] text-muted">{explanation}</p>}
      {preview.fee_error && (
        <p className="text-[13px] text-st-amber" role="status">
          Không tính được phí: {preview.fee_error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button className="h-11 min-w-[44px]" onClick={onConfirm} disabled={busy}>
          Xác nhận RA
        </Button>
        <Button variant="outline" className="h-11" onClick={onCancel} disabled={busy}>
          Huỷ
        </Button>
        <span className="text-[12px] text-muted">Phiên chỉ được đóng sau khi bấm xác nhận.</span>
      </div>
    </div>
  );
}
