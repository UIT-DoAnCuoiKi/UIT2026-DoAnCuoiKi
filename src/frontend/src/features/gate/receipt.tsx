import { Button } from "@/components/ui/button";
import { formatDateTime, formatMinutes, formatVnd } from "@/lib/format";
import { paymentMethodLabel } from "@/lib/labels";

export function Receipt({
  sessionId,
  plate,
  amount,
  method,
  entryTime,
  exitTime,
  minutes,
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  method: string;
  /** Giờ vào và thời lượng gửi: khách cần đối chiếu, trước đây phiếu không có. */
  entryTime?: string | null;
  exitTime?: string | null;
  minutes?: number | null;
}) {
  return (
    <div className="space-y-2">
      <div className="rounded-[var(--radius-control)] border border-line p-4 text-[13px]" data-receipt>
        <p className="text-center text-sm font-semibold">Biên lai gửi xe</p>
        <p>Mã phiên: #{sessionId}</p>
        <p>Biển số: {plate ?? "—"}</p>
        {entryTime && <p>Giờ vào: <span className="tnum">{formatDateTime(entryTime)}</span></p>}
        <p>Giờ ra: <span className="tnum">{formatDateTime(exitTime ?? new Date().toISOString())}</span></p>
        {minutes != null && <p>Thời lượng: <span className="tnum">{formatMinutes(minutes)}</span></p>}
        <p>Phí: <span className="tnum">{formatVnd(amount)}</span></p>
        <p>Phương thức: {paymentMethodLabel(method)}</p>
      </div>
      <Button variant="outline" onClick={() => window.print()}>
        In phiếu
      </Button>
    </div>
  );
}
