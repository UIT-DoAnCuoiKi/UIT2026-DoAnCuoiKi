import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { Code39 } from "./code39";
import { usePrintOnly } from "./use-print-only";

// Phiếu in khi xe vào. Trước đây lượt ra chỉ khớp bằng biển số, nên ai lái xe ra
// cũng được; phiếu cho khách một mã gắn với đúng phiên để xuất trình lúc lấy xe.
export function Ticket({
  code,
  plate,
  entryTime,
  vehicleLabel,
  onDone,
}: {
  code: string;
  plate?: string | null;
  entryTime?: string | null;
  vehicleLabel?: string | null;
  onDone: () => void;
}) {
  const { ref, print } = usePrintOnly();
  return (
    <div className="space-y-3">
      <div ref={ref} className="rounded-[var(--radius-control)] border border-line p-4 text-[13px]" data-ticket>
        <p className="text-center text-sm font-semibold">Phiếu gửi xe</p>
        <p className="mt-2 text-center text-xl font-bold tracking-[0.08em] tnum">{code}</p>
        <div className="mx-auto mt-1 max-w-[320px]">
          <Code39 value={code} />
        </div>
        <p className="mt-2">Biển số: {plate ?? "—"}</p>
        {entryTime && (
          <p>
            Giờ vào: <span className="tnum">{formatDateTime(entryTime)}</span>
          </p>
        )}
        {vehicleLabel && <p>Loại xe: {vehicleLabel}</p>}
        <p className="mt-2 text-[12px] text-muted">Xuất trình phiếu này khi lấy xe.</p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={print}>
          In phiếu
        </Button>
        <Button onClick={onDone}>Xong</Button>
      </div>
    </div>
  );
}
