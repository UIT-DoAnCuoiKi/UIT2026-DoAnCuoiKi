import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";
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
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  method: string;
  onMethod: (key: string) => void;
  onConfirm: () => void;
  pending: boolean;
  paid: boolean;
}) {
  if (paid) {
    return (
      <div className="rounded-[var(--radius-control)] border border-line p-3">
        <Receipt sessionId={sessionId} plate={plate} amount={amount} method={method} />
      </div>
    );
  }
  return (
    <div className="space-y-3 rounded-[var(--radius-control)] border border-line p-3">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold">Thu tiền khi RA</p>
        <p className="tnum text-[22px] font-semibold">{formatVnd(amount)}</p>
      </div>
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
