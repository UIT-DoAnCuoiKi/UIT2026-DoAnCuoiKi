import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { toast } from "sonner";
import { useConfirmEntry, useConfirmExit, useManualSession } from "@/api/generated/sessions/sessions";
import { usePatchPlate } from "@/api/generated/readings/readings";
import { useCreatePayment } from "@/api/generated/payments/payments";
import { useGetToggles } from "@/api/generated/config/config";
import { useListVehicleGroups } from "@/api/generated/vehicle-groups/vehicle-groups";
import type { GateCapture } from "./use-gate-socket";
import { PlateField } from "@/components/plate-field";
import { StatusChip } from "@/components/status-chip";
import { Button } from "@/components/ui/button";
import { RecognitionResult } from "./recognition-result";
import { PayRow, PAY_METHODS } from "./pay-row";
import { useVehicleGroupMap } from "@/lib/vehicle-groups";

export type DecisionPanelHandle = {
  confirm: () => void;
  manual: () => void;
  cancel: () => void;
  payMethod: (n: number) => void;
  focusPlate: () => void;
};

type Props = {
  capture: GateCapture;
  direction: "in" | "out";
  onDone: () => void;
  onRecapture: () => void;
  onPayOpenChange?: (open: boolean) => void;
};

export const DecisionPanel = forwardRef<DecisionPanelHandle, Props>(function DecisionPanel(
  { capture, direction, onDone, onRecapture, onPayOpenChange },
  ref,
) {
  const { data: toggles } = useGetToggles();
  const forceManual = toggles ? !toggles.read_plate : false;
  const state = forceManual ? "manual" : capture.review_state;
  const groupMap = useVehicleGroupMap();
  const { data: groups } = useListVehicleGroups();

  const [plate, setPlate] = useState(capture.plate_text ?? "");
  useEffect(() => setPlate(capture.plate_text ?? ""), [capture.reading_id, capture.plate_text]);

  const [group, setGroup] = useState(capture.vehicle_group ?? "");
  useEffect(() => setGroup(capture.vehicle_group ?? ""), [capture.reading_id, capture.vehicle_group]);

  const [manualOpen, setManualOpen] = useState(state === "manual");
  useEffect(() => setManualOpen(state === "manual"), [state, capture.reading_id]);

  const confirmEntry = useConfirmEntry();
  const confirmExit = useConfirmExit();
  const manual = useManualSession();
  const patchPlate = usePatchPlate();
  const createPayment = useCreatePayment();

  const [candidates, setCandidates] = useState<{ id: number; plate_text?: string | null }[]>([]);
  const [payFor, setPayFor] = useState<{ sessionId: number; amount: number; plate?: string | null } | null>(null);
  const [method, setMethod] = useState("cash");
  const [paid, setPaid] = useState(false);

  // Synchronous in-flight latch: React Query isPending flips only after a
  // re-render, leaving a one-tick window where two rapid Enter/click events
  // both pass the busy check. This prevents a duplicate entry/exit/payment.
  const inFlight = useRef(false);

  useEffect(() => {
    setCandidates([]);
    setPayFor(null);
    setPaid(false);
    setMethod("cash");
  }, [capture.reading_id]);

  useEffect(() => {
    onPayOpenChange?.(payFor !== null);
  }, [payFor, onPayOpenChange]);

  const busy =
    confirmEntry.isPending ||
    confirmExit.isPending ||
    manual.isPending ||
    patchPlate.isPending ||
    createPayment.isPending;
  const plateTrim = plate.trim();
  const plateChanged = plateTrim !== (capture.plate_text ?? "").trim();

  const ensurePlateSaved = async () => {
    if (plateTrim && plateChanged) {
      await patchPlate.mutateAsync({ readingId: capture.reading_id, data: { plate_text: plateTrim } });
    }
  };

  const savePlate = async () => {
    if (!plateTrim || !plateChanged || busy) return;
    await patchPlate.mutateAsync({ readingId: capture.reading_id, data: { plate_text: plateTrim } });
    toast.success("Đã cập nhật biển số");
  };

  const doEntry = async (allowPlateless = false) => {
    if (busy || inFlight.current) return;
    if (!plateTrim && !allowPlateless) return;
    inFlight.current = true;
    try {
      if (plateTrim) await ensurePlateSaved();
      await confirmEntry.mutateAsync({ data: { reading_id: capture.reading_id } });
      toast.success(plateTrim ? "Đã xác nhận VÀO" : "Đã tạo phiên chờ (vào không biển)");
      onDone();
    } catch {
      toast.error("Xác nhận VÀO thất bại");
    } finally {
      inFlight.current = false;
    }
  };

  const doExit = async (sessionId?: number) => {
    if (busy || inFlight.current) return;
    inFlight.current = true;
    try {
      if (plateTrim) await ensurePlateSaved();
      const res = await confirmExit.mutateAsync({
        data: { reading_id: capture.reading_id, ...(sessionId ? { session_id: sessionId } : {}) },
      });
      if (res.candidates && res.candidates.length > 0 && !sessionId) {
        setCandidates(res.candidates);
        return;
      }
      const s = res.session;
      if (!s) {
        toast.error("Không tìm thấy phiên phù hợp. Chọn phiên hoặc dùng Nhập tay.");
        return;
      }
      if ((s.fee_amount ?? 0) > 0) {
        setPayFor({ sessionId: s.id, amount: s.fee_amount as number, plate: s.plate_text });
        return;
      }
      toast.success("Đã xác nhận RA (miễn phí)");
      onDone();
    } catch {
      toast.error("Xác nhận RA thất bại");
    } finally {
      inFlight.current = false;
    }
  };

  const doManualEntry = async () => {
    if (busy || inFlight.current) return;
    if (!plateTrim || !group) {
      toast.error("Nhập tay cần biển số và nhóm phí");
      return;
    }
    inFlight.current = true;
    try {
      await manual.mutateAsync({
        data: { action: "entry", plate_text: plateTrim, vehicle_group: group, reading_id: capture.reading_id },
      });
      toast.success("Đã ghi nhận nhập tay");
      onDone();
    } catch {
      toast.error("Nhập tay thất bại");
    } finally {
      inFlight.current = false;
    }
  };

  const confirmPay = async () => {
    if (!payFor || createPayment.isPending || inFlight.current) return;
    inFlight.current = true;
    try {
      await createPayment.mutateAsync({
        data: { session_id: payFor.sessionId, amount: payFor.amount, method, kind: "payment" },
      });
      toast.success("Đã thu tiền");
      setPaid(true);
    } catch {
      toast.error("Thu tiền thất bại");
    } finally {
      inFlight.current = false;
    }
  };

  const primaryConfirm = () => (direction === "in" ? doEntry(false) : doExit());

  useImperativeHandle(ref, () => ({
    confirm: () => {
      if (payFor) {
        if (paid) onDone();
        else confirmPay();
      } else {
        primaryConfirm();
      }
    },
    manual: () => setManualOpen(true),
    cancel: () => {
      if (payFor) {
        if (!paid) setPayFor(null);
      } else if (candidates.length) {
        setCandidates([]);
      } else {
        onDone();
      }
    },
    payMethod: (n) => {
      const m = PAY_METHODS[n - 1];
      if (m) setMethod(m.key);
    },
    focusPlate: () => document.getElementById("plate")?.focus(),
  }));

  const entryDisabled = busy || !plateTrim;
  const exitDisabled = busy;

  if (payFor) {
    return (
      <PayRow
        sessionId={payFor.sessionId}
        plate={payFor.plate}
        amount={payFor.amount}
        method={method}
        onMethod={setMethod}
        onConfirm={paid ? onDone : confirmPay}
        pending={createPayment.isPending}
        paid={paid}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <StatusChip kind="review" value={state} />
        <Button variant="outline" className="h-9" onClick={onRecapture} disabled={busy}>
          Nhận lại
        </Button>
      </div>

      <PlateField value={plate} onChange={setPlate} size="lg" highlight={state === "needs_review"} />

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" className="h-9" onClick={savePlate} disabled={!plateTrim || !plateChanged || busy}>
          Lưu biển
        </Button>
      </div>

      <RecognitionResult capture={capture} groupMap={groupMap} />

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
        <div className="space-y-2">
          {direction === "in" ? (
            <div className="flex flex-wrap gap-2">
              <Button className="h-11 min-w-[44px]" onClick={() => doEntry(false)} disabled={entryDisabled}>
                Xác nhận VÀO
              </Button>
              {!plateTrim && (
                <Button variant="outline" className="h-11" onClick={() => doEntry(true)} disabled={busy}>
                  Vào không biển (phiên chờ)
                </Button>
              )}
            </div>
          ) : (
            <Button className="h-11 min-w-[44px]" onClick={() => doExit()} disabled={exitDisabled}>
              Xác nhận RA
            </Button>
          )}
          {!plateTrim && direction === "in" && (
            <p className="text-[13px] text-muted">Cần biển số để xác nhận VÀO, hoặc dùng "Vào không biển".</p>
          )}
        </div>
      )}

      {manualOpen && direction === "in" && (
        <div className="space-y-2 border-t border-line pt-3">
          <p className="text-sm font-medium">Nhập tay hoàn toàn</p>
          <label className="block text-[13px] text-muted" htmlFor="manual-group">
            Nhóm phí
          </label>
          <select
            id="manual-group"
            aria-label="Nhóm phí"
            className="h-10 w-full rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
            value={group}
            onChange={(e) => setGroup(e.target.value)}
          >
            <option value="">Chọn nhóm phí</option>
            {(groups ?? []).map((g) => (
              <option key={g.code} value={g.code}>
                {g.display_name}
              </option>
            ))}
          </select>
          <Button className="h-11" onClick={doManualEntry} disabled={busy || !plateTrim || !group}>
            Ghi nhận nhập tay
          </Button>
        </div>
      )}

      {manualOpen && direction === "out" && (
        <p className="border-t border-line pt-3 text-[13px] text-muted">
          Nhập tay RA: chọn phiên trong danh sách để nối.
        </p>
      )}

      {!manualOpen && (
        <div className="border-t border-line pt-3">
          <Button variant="secondary" className="h-11" onClick={() => setManualOpen(true)}>
            Nhập tay
          </Button>
        </div>
      )}
    </div>
  );
});
