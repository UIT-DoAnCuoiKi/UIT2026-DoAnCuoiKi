import { Button } from "@/components/ui/button";
import { formatDateTime, formatMinutes, formatPlate, formatVnd } from "@/lib/format";
import { Receipt } from "./receipt";

export const PAY_METHODS: { key: string; label: string }[] = [
  { key: "cash", label: "Tiền mặt" },
  { key: "qr", label: "QR" },
  { key: "ewallet", label: "Ví điện tử" },
];

export function PayRow({
  sessionId,
  plate,
  amount,
  method,
  onMethod,
  onConfirm,
  pending,
  paid,
  entryTime,
  exitTime,
  minutes,
  explanation,
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  method: string;
  onMethod: (key: string) => void;
  onConfirm: () => void;
  pending: boolean;
  paid: boolean;
  /** Căn cứ để nhân viên đối chiếu trước khi thu, không chỉ mỗi con số tiền. */
  entryTime?: string | null;
  exitTime?: string | null;
  minutes?: number | null;
  explanation?: string | null;
}) {
  if (paid) {
    return (
      <div className="rounded-[var(--radius-control)] border border-line p-3">
        <Receipt
          sessionId={sessionId}
          plate={plate}
          amount={amount}
          method={method}
          entryTime={entryTime}
          exitTime={exitTime}
          minutes={minutes}
        />
      </div>
    );
  }
  return (
    <div className="space-y-3 rounded-[var(--radius-control)] border border-line p-3">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold">Thu tiền khi RA</p>
        <p className="tnum text-[22px] font-semibold">{formatVnd(amount)}</p>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[13px] sm:grid-cols-4">
        <div>
          <span className="block text-[12px] text-muted">Biển số</span>
          <span className="tnum font-medium text-ink">{formatPlate(plate)}</span>
        </div>
        <div>
          <span className="block text-[12px] text-muted">Giờ vào</span>
          <span className="tnum">{formatDateTime(entryTime)}</span>
        </div>
        <div>
          <span className="block text-[12px] text-muted">Giờ ra</span>
          <span className="tnum">{formatDateTime(exitTime)}</span>
        </div>
        <div>
          <span className="block text-[12px] text-muted">Thời lượng</span>
          <span className="tnum">{formatMinutes(minutes)}</span>
        </div>
      </div>
      {explanation && <p className="text-[12px] text-muted">{explanation}</p>}
      <div className="flex flex-wrap gap-2">
        {PAY_METHODS.map((m, i) => (
          <Button
            key={m.key}
            variant={method === m.key ? "default" : "outline"}
            className="h-11"
            onClick={() => onMethod(m.key)}
          >
            {i + 1} {m.label}
          </Button>
        ))}
      </div>
      <Button className="h-11 w-full" onClick={onConfirm} disabled={pending}>
        Thu & in (Enter)
      </Button>
    </div>
  );
}
