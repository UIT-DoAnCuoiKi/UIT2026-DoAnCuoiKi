import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useConfirmEntry, useConfirmExit, useManualSession } from "@/api/generated/sessions/sessions";
import { usePatchPlate } from "@/api/generated/readings/readings";
import { useGetToggles } from "@/api/generated/config/config";
import type { GateCapture } from "./use-gate-socket";
import { PlateField } from "@/components/plate-field";
import { StatusChip } from "@/components/status-chip";
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";

export function DecisionPanel({
  capture,
  direction,
  onDone,
}: {
  capture: GateCapture;
  direction: "in" | "out";
  onDone: () => void;
}) {
  const { data: toggles } = useGetToggles();
  const forceManual = toggles ? !toggles.read_plate : false;
  const state = forceManual ? "manual" : capture.review_state;

  const [plate, setPlate] = useState(capture.plate_text ?? "");
  useEffect(() => setPlate(capture.plate_text ?? ""), [capture.reading_id, capture.plate_text]);

  const confirmEntry = useConfirmEntry();
  const confirmExit = useConfirmExit();
  const manual = useManualSession();
  const patchPlate = usePatchPlate();
  const [candidates, setCandidates] = useState<{ id: number; plate_text?: string | null }[]>([]);

  const savePlate = async () => {
    if (!plate.trim()) return;
    await patchPlate.mutateAsync({ readingId: capture.reading_id, data: { plate_text: plate.trim() } });
    toast.success("Đã cập nhật biển số");
  };

  const doEntry = async () => {
    await confirmEntry.mutateAsync({ data: { reading_id: capture.reading_id } });
    toast.success("Đã xác nhận VÀO");
    onDone();
  };

  const doExit = async (sessionId?: number) => {
    const res = await confirmExit.mutateAsync({
      data: { reading_id: capture.reading_id, ...(sessionId ? { session_id: sessionId } : {}) },
    });
    if (res.candidates && res.candidates.length > 0 && !sessionId) {
      setCandidates(res.candidates);
      return;
    }
    const fee = res.session?.fee_amount;
    toast.success(fee != null ? `Ra: phí ${formatVnd(fee)}` : "Đã xác nhận RA");
    onDone();
  };

  const doManual = async () => {
    await manual.mutateAsync({
      data: {
        action: direction === "in" ? "entry" : "exit",
        plate_text: plate.trim() || undefined,
        vehicle_group: capture.vehicle_group ?? undefined,
      },
    });
    toast.success("Đã ghi nhận nhập tay");
    onDone();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <StatusChip kind="review" value={state} />
        {capture.duplicate && (
          <span className="text-[13px] text-st-amber">Cảnh báo: biển trùng phiên trong bãi</span>
        )}
      </div>

      {capture.plate_valid === false && (
        <p className="text-[13px] text-st-amber">Cảnh báo: biển sai định dạng (vẫn cho xác nhận)</p>
      )}

      <PlateField value={plate} onChange={setPlate} size="lg" highlight={state === "needs_review"} />

      {state === "needs_review" && (
        <Button variant="outline" onClick={savePlate}>
          Lưu biển đã sửa
        </Button>
      )}

      {candidates.length > 0 ? (
        <div className="space-y-2">
          <p className="text-sm font-medium">Chọn phiên để nối</p>
          {candidates.map((c) => (
            <Button
              key={c.id}
              variant="outline"
              className="w-full justify-start"
              onClick={() => doExit(c.id)}
            >
              #{c.id} — {c.plate_text ?? "?"}
            </Button>
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {state !== "manual" && direction === "in" && (
            <Button className="h-11 min-w-[44px]" onClick={doEntry}>
              Xác nhận VÀO
            </Button>
          )}
          {state !== "manual" && direction === "out" && (
            <Button className="h-11 min-w-[44px]" onClick={() => doExit()}>
              Xác nhận RA
            </Button>
          )}
        </div>
      )}

      <div className="border-t border-line pt-3">
        <Button variant="secondary" className="h-11" onClick={doManual}>
          Nhập tay hoàn toàn
        </Button>
      </div>
    </div>
  );
}
