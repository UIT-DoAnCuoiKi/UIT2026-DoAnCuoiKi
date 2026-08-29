import { useState } from "react";
import { toast } from "sonner";
import { useCreatePayment } from "@/api/generated/payments/payments";
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";
import { Receipt } from "./receipt";

const METHODS: { key: string; label: string }[] = [
  { key: "cash", label: "1. Tiền mặt" },
  { key: "qr", label: "2. QR" },
  { key: "ewallet", label: "3. Ví điện tử" },
];

export function PaymentDialog({
  sessionId,
  plate,
  amount,
  onClose,
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  onClose: () => void;
}) {
  const [method, setMethod] = useState<string>("cash");
  const [done, setDone] = useState(false);
  const create = useCreatePayment();

  const confirm = async () => {
    await create.mutateAsync({ data: { session_id: sessionId, amount, method, kind: "payment" } });
    toast.success("Đã thu tiền");
    setDone(true);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true">
      <div className="w-[380px] space-y-4 rounded-[var(--radius-control)] bg-bg p-5 shadow-lg">
        {!done ? (
          <>
            <div>
              <p className="text-sm font-semibold">Thu tiền khi ra</p>
              <p className="text-[13px] text-muted">
                Phí: <span className="tnum">{formatVnd(amount)}</span>
              </p>
            </div>
            <div className="flex flex-col gap-2">
              {METHODS.map((m) => (
                <Button
                  key={m.key}
                  variant={method === m.key ? "default" : "outline"}
                  onClick={() => setMethod(m.key)}
                >
                  {m.label}
                </Button>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose}>
                Hủy
              </Button>
              <Button onClick={confirm} disabled={create.isPending}>
                Xác nhận thu
              </Button>
            </div>
          </>
        ) : (
          <>
            <Receipt sessionId={sessionId} plate={plate} amount={amount} method={method} />
            <div className="flex justify-end">
              <Button onClick={onClose}>Đóng</Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
