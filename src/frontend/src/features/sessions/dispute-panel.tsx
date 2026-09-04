import { useState } from "react";
import { toast } from "sonner";
import { useDisputeSession, useResolveSession } from "@/api/generated/sessions/sessions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function DisputePanel({ sessionId, onChanged }: { sessionId: number; onChanged: () => void }) {
  const dispute = useDisputeSession();
  const resolve = useResolveSession();
  const [fee, setFee] = useState("");

  return (
    <div className="space-y-3 border-t border-line pt-4">
      <p className="text-sm font-semibold">Xử lý tranh chấp</p>
      <Button
        variant="outline"
        onClick={async () => {
          await dispute.mutateAsync({ sessionId });
          toast.success("Đã chuyển tranh chấp");
          onChanged();
        }}
      >
        Đánh dấu tranh chấp
      </Button>
      <div className="flex items-end gap-2">
        <div className="space-y-1.5">
          <Label htmlFor="fee">Phí nhập tay</Label>
          <Input
            id="fee"
            className="tnum w-40"
            inputMode="numeric"
            value={fee}
            onChange={(e) => setFee(e.target.value.replace(/\D/g, ""))}
          />
        </div>
        <Button
          variant="destructive"
          disabled={!fee}
          onClick={async () => {
            await resolve.mutateAsync({ sessionId, data: { fee_amount: Number(fee) } });
            toast.success("Đã chốt phí");
            onChanged();
          }}
        >
          Chốt phí và giải quyết
        </Button>
      </div>
    </div>
  );
}
