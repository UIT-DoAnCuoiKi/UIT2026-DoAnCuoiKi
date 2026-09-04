import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";

const METHOD_LABEL: Record<string, string> = { cash: "Tiền mặt", qr: "QR", ewallet: "Ví điện tử" };

export function Receipt({
  sessionId,
  plate,
  amount,
  method,
}: {
  sessionId: number;
  plate?: string | null;
  amount: number;
  method: string;
}) {
  return (
    <div className="space-y-2">
      <div className="rounded-[var(--radius-control)] border border-line p-4 text-[13px]" data-receipt>
        <p className="text-center text-sm font-semibold">Biên lai gửi xe</p>
        <p>Mã phiên: #{sessionId}</p>
        <p>Biển số: {plate ?? "—"}</p>
        <p>Phí: <span className="tnum">{formatVnd(amount)}</span></p>
        <p>Phương thức: {METHOD_LABEL[method] ?? method}</p>
        <p>Thời điểm: {new Date().toLocaleString("vi-VN")}</p>
      </div>
      <Button variant="outline" onClick={() => window.print()}>
        In phiếu
      </Button>
    </div>
  );
}
