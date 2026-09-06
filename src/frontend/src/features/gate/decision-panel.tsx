import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { toast } from "sonner";
import { useConfirmEntry, useConfirmExit, useManualSession, usePreviewExit } from "@/api/generated/sessions/sessions";
import type { ExitPreview } from "@/api/generated/model";
import { usePatchPlate } from "@/api/generated/readings/readings";
import { useCreatePayment } from "@/api/generated/payments/payments";
import { useGetToggles, useListPriceRules } from "@/api/generated/config/config";
import type { PlatePatch } from "@/api/generated/model";
import type { GateCapture } from "./use-gate-socket";
import { PlateField } from "@/components/plate-field";
import { StatusChip } from "@/components/status-chip";
import { Button } from "@/components/ui/button";
import { RecognitionResult } from "./recognition-result";
import { ExitReview, feeExplanation } from "./exit-review";
import { PayRow, PAY_METHODS } from "./pay-row";
import { VEHICLE_TYPE_OPTIONS, vehicleTypeLabel } from "@/lib/labels";
import { groupForVehicleType } from "@/lib/vehicle-groups";
import { formatVnd } from "@/lib/format";
import { PLATE_COLOR_OPTIONS, plateColor } from "./plate-color";

export type DecisionPanelHandle = {
  confirm: () => void;
  manual: () => void;
  reset: () => void;
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
  // Mỗi hướng một id riêng: 2 panel cùng mount, id trùng thì focus nhảy nhầm panel.
  const plateFieldId = `plate-${direction}`;
  const { data: toggles } = useGetToggles();
  const forceManual = toggles ? !toggles.read_plate : false;
  const state = forceManual ? "manual" : capture.review_state;
  const { data: priceRules } = useListPriceRules();

  const [plate, setPlate] = useState(capture.plate_text ?? "");
  useEffect(() => setPlate(capture.plate_text ?? ""), [capture.reading_id, capture.plate_text]);

  const [vType, setVType] = useState(capture.vehicle_type ?? "");
  useEffect(() => setVType(capture.vehicle_type ?? ""), [capture.reading_id, capture.vehicle_type]);

  // Loại xe và nhóm phí map 1-1: nhóm phí suy ra từ loại xe, không cần chọn tay.
  // Giá hiển thị theo bảng giá đang bật của nhóm tương ứng.
  const group = groupForVehicleType(vType);
  const activeRule = (priceRules ?? []).find((r) => r.vehicle_group === group && r.active);
  const priceText = !activeRule
    ? null
    : activeRule.mode === "block" && activeRule.block_minutes
      ? `${formatVnd(activeRule.unit_price)} / ${activeRule.block_minutes} phút`
      : `${formatVnd(activeRule.unit_price)} / lượt`;

  const [color, setColor] = useState(capture.color ?? "");
  useEffect(() => setColor(capture.color ?? ""), [capture.reading_id, capture.color]);

  const [manualOpen, setManualOpen] = useState(state === "manual");
  useEffect(() => setManualOpen(state === "manual"), [state, capture.reading_id]);

  const confirmEntry = useConfirmEntry();
  const confirmExit = useConfirmExit();
  const previewExit = usePreviewExit();
  const manual = useManualSession();
  const patchPlate = usePatchPlate();
  const createPayment = useCreatePayment();

  const [candidates, setCandidates] = useState<{ id: number; plate_text?: string | null }[]>([]);
  // Kết quả tính thử lượt RA: hiện đối chiếu ảnh vào/ra + phí dự tính, phiên chưa đóng.
  const [exitPreview, setExitPreview] = useState<ExitPreview | null>(null);
  const [dupBlocked, setDupBlocked] = useState(false);
  const [payFor, setPayFor] = useState<{
    sessionId: number;
    amount: number;
    plate?: string | null;
    entryTime?: string | null;
    exitTime?: string | null;
    minutes?: number | null;
    explanation?: string | null;
  } | null>(null);
  const [method, setMethod] = useState("cash");
  const [paid, setPaid] = useState(false);

  // Synchronous in-flight latch: React Query isPending flips only after a
  // re-render, leaving a one-tick window where two rapid Enter/click events
  // both pass the busy check. This prevents a duplicate entry/exit/payment.
  const inFlight = useRef(false);

  // Lượt mới thì dọn sạch mọi trạng thái của lượt trước, không để sót gì trên màn.
  useEffect(() => {
    setCandidates([]);
    setExitPreview(null);
    setDupBlocked(false);
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
    previewExit.isPending ||
    manual.isPending ||
    patchPlate.isPending ||
    createPayment.isPending;
  const plateTrim = plate.trim();
  const plateChanged = plateTrim !== (capture.plate_text ?? "").trim();
  const typeChanged = vType !== (capture.vehicle_type ?? "");
  const colorChanged = color !== (capture.color ?? "");
  const editsChanged = plateChanged || typeChanged || colorChanged;

  // Gom các trường nhân viên đã sửa tay (biển, loại xe, màu biển) thành một
  // patch; chỉ gửi trường thực sự đổi để không ghi đè giá trị model đang đúng.
  const buildPatch = (): PlatePatch => {
    const p: PlatePatch = {};
    if (plateTrim && plateChanged) p.plate_text = plateTrim;
    if (typeChanged && vType) p.vehicle_type = vType;
    if (colorChanged && color) p.color = color;
    return p;
  };

  const ensureEditsSaved = async () => {
    const p = buildPatch();
    if (Object.keys(p).length) {
      await patchPlate.mutateAsync({ readingId: capture.reading_id, data: p });
    }
  };

  const saveEdits = async () => {
    const p = buildPatch();
    if (!Object.keys(p).length || busy) return;
    await patchPlate.mutateAsync({ readingId: capture.reading_id, data: p });
    toast.success("Đã lưu chỉnh sửa");
  };

  // Trả các trường sửa tay về đúng giá trị model đã nhận dạng (dùng khi nhập nhầm).
  const hasEdits = editsChanged;
  const resetEdits = () => {
    if (busy) return;
    setPlate(capture.plate_text ?? "");
    setVType(capture.vehicle_type ?? "");
    setColor(capture.color ?? "");
  };

  const doEntry = async (allowPlateless = false, overrideDup = false) => {
    if (busy || inFlight.current) return;
    if (!plateTrim && !allowPlateless) return;
    inFlight.current = true;
    try {
      await ensureEditsSaved();
      // Không gửi vehicle_group: BE suy ra từ vehicle_type (đã lưu ở
      // ensureEditsSaved), giữ map loại xe -> nhóm phí nhất quán một nguồn.
      const session = await confirmEntry.mutateAsync({
        data: {
          reading_id: capture.reading_id,
          ...(overrideDup ? { override_duplicate: true } : {}),
        },
      });
      setDupBlocked(false);
      // BE trả cảnh báo (biển trong danh sách đen, hoặc trùng đã ghi đè) qua
      // session.warning; hiện cho nhân viên biết vẫn cần lưu ý dù đã cho vào.
      if (session?.warning) toast.warning(session.warning);
      else toast.success(plateTrim ? "Đã xác nhận VÀO" : "Đã tạo phiên chờ (vào không biển)");
      onDone();
    } catch (e) {
      // BE trả 409 cho hai nguyên nhân khác nhau, phân biệt bằng error_code:
      // đoán theo mỗi mã HTTP sẽ báo nhầm "biển trùng" khi thật ra là bãi đầy,
      // kèm nút ghi đè vô nghĩa vì bấm lại cũng đầy y như cũ.
      const err = e as { response?: { status?: number; data?: { detail?: { error_code?: string } } } };
      const code = err?.response?.data?.detail?.error_code;
      if (code === "lot_full") {
        toast.error("Bãi đã đầy, không nhận thêm xe.");
      } else if (err?.response?.status === 409) {
        setDupBlocked(true);
        toast.error("Biển đang trong bãi. Bấm ghi đè nếu chắc chắn cho vào.");
      } else {
        toast.error("Xác nhận VÀO thất bại");
      }
    } finally {
      inFlight.current = false;
    }
  };

  /** Bước 1 khi cho xe RA: tính thử để nhân viên đối chiếu, KHÔNG đóng phiên. */
  const doExitPreview = async (sessionId?: number) => {
    if (busy || inFlight.current) return;
    inFlight.current = true;
    try {
      await ensureEditsSaved();
      const res = await previewExit.mutateAsync({
        data: { reading_id: capture.reading_id, ...(sessionId ? { session_id: sessionId } : {}) },
      });
      if (res.outcome === "suggest" && res.candidates?.length) {
        setCandidates(res.candidates);
        return;
      }
      if (res.outcome === "no_match") {
        // Không khớp xe nào: để nhân viên chọn phiên tay hoặc dùng Nhập tay.
        // Không tự tạo phiên tranh chấp ở bước xem trước.
        toast.error("Không khớp xe nào trong bãi. Chọn phiên hoặc dùng Nhập tay.");
        return;
      }
      setCandidates([]);
      setExitPreview(res);
    } catch {
      toast.error("Không tính thử được lượt RA");
    } finally {
      inFlight.current = false;
    }
  };

  /** Bước 2: chốt thật (đóng phiên, ghi phí) sau khi nhân viên đã đối chiếu. */
  const doExit = async (sessionId?: number) => {
    if (busy || inFlight.current) return;
    inFlight.current = true;
    try {
      await ensureEditsSaved();
      const res = await confirmExit.mutateAsync({
        data: { reading_id: capture.reading_id, ...(sessionId ? { session_id: sessionId } : {}) },
      });
      setExitPreview(null);
      if (res.candidates && res.candidates.length > 0 && !sessionId) {
        setCandidates(res.candidates);
        return;
      }
      const s = res.session;
      if (!s) {
        toast.error("Không tìm thấy phiên phù hợp. Chọn phiên hoặc dùng Nhập tay.");
        return;
      }
      // BE không khớp được xe nào thì tạo phiên tranh chấp (chưa có phí). Phải
      // báo đúng, nếu rơi xuống nhánh dưới sẽ hiện "RA miễn phí" và nhân viên
      // không biết vừa phát sinh một phiên cần xử lý.
      if (res.outcome === "disputed") {
        toast.warning("Không khớp xe nào trong bãi. Đã tạo phiên tranh chấp, cần xử lý ở màn Phiên.");
        onDone();
        return;
      }
      if ((s.fee_amount ?? 0) > 0) {
        setPayFor({
          sessionId: s.id,
          amount: s.fee_amount as number,
          plate: s.plate_text,
          entryTime: s.entry_time,
          exitTime: s.exit_time,
          // Ưu tiên số liệu đã tính ở bước đối chiếu; nếu chốt thẳng (không qua
          // xem trước) thì suy lại thời lượng từ giờ vào/ra của phiên đã đóng.
          minutes:
            exitPreview?.minutes ??
            (s.entry_time && s.exit_time
              ? (new Date(s.exit_time).getTime() - new Date(s.entry_time).getTime()) / 60000
              : null),
          explanation: feeExplanation(exitPreview?.fee_rule_snapshot as Record<string, unknown> | null),
        });
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
      toast.error("Nhập tay cần biển số và loại xe");
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

  // RA đi 2 bước: xem trước để đối chiếu, rồi mới chốt. Nếu đang ở màn đối chiếu
  // thì Enter nghĩa là chốt luôn, không phải tính thử lại.
  const primaryConfirm = () =>
    direction === "in" ? doEntry(false) : exitPreview ? doExit(exitPreview.session?.id) : doExitPreview();

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
    reset: resetEdits,
    cancel: () => {
      if (payFor) {
        if (!paid) setPayFor(null);
      } else if (exitPreview) {
        setExitPreview(null);
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
    focusPlate: () => document.getElementById(plateFieldId)?.focus(),
  }));

  const entryDisabled = busy || !plateTrim;
  const exitDisabled = busy;

  // Đối chiếu vào/ra trước khi chốt: chiếm trọn panel để ảnh đủ to mà nhìn.
  if (exitPreview) {
    return (
      <ExitReview
        preview={exitPreview}
        exitLocalUrl={capture.local_image_url}
        onConfirm={() => doExit(exitPreview.session?.id)}
        onCancel={() => setExitPreview(null)}
        busy={busy}
      />
    );
  }

  if (payFor) {
    return (
      <PayRow
        sessionId={payFor.sessionId}
        plate={payFor.plate}
        amount={payFor.amount}
        entryTime={payFor.entryTime}
        exitTime={payFor.exitTime}
        minutes={payFor.minutes}
        explanation={payFor.explanation}
        method={method}
        onMethod={setMethod}
        onConfirm={paid ? onDone : confirmPay}
        pending={createPayment.isPending}
        paid={paid}
      />
    );
  }

  // Bố cục: phần phụ (độ tin cậy, danh sách phiên, nhập tay) cuộn được ở trên;
  // thanh thao tác chính ghim đáy nên biển số và nút xác nhận không bao giờ bị
  // đẩy khỏi màn hình — trước đây nhân viên phải cuộn mới bấm được nút chính.
  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="min-h-0 flex-1 space-y-2 overflow-auto">
        <div className="flex items-center justify-between gap-2">
          <StatusChip kind="review" value={state} />
          <div className="flex items-center gap-2">
            <Button variant="ghost" className="h-9" onClick={resetEdits} disabled={!hasEdits || busy}>
              Hoàn tác sửa
            </Button>
            <Button variant="outline" className="h-9" onClick={saveEdits} disabled={!editsChanged || busy}>
              Lưu chỉnh sửa
            </Button>
            <Button variant="outline" className="h-9" onClick={onRecapture} disabled={busy}>
              Nhận lại
            </Button>
            {/* Khác với "Hoàn tác sửa" (chỉ trả biển/loại xe/màu về đúng giá trị
                model đã nhận, luôn tắt khi chưa sửa gì) — nút này xoá hẳn cả ảnh
                lẫn kết quả của lượt hiện tại, cho lượt chụp mới hoàn toàn. Trước
                đây không có cách nào bỏ một lượt chụp hỏng ngoài phím tắt Esc. */}
            <Button variant="ghost" className="h-9" onClick={onDone} disabled={busy}>
              Xoá lượt
            </Button>
          </div>
        </div>

        <RecognitionResult capture={capture} />

        {candidates.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Chọn phiên để nối</p>
            {candidates.map((c) => (
              <Button
                key={c.id}
                variant="outline"
                className="w-full justify-start"
                onClick={() => doExitPreview(c.id)}
              >
                #{c.id} — {c.plate_text ?? "?"}
              </Button>
            ))}
          </div>
        )}

        {dupBlocked && (
          <p className="text-[13px] text-st-amber">Biển đang có phiên trong bãi. Ghi đè chỉ khi chắc chắn.</p>
        )}

        {manualOpen && direction === "in" && (
          <div className="space-y-2 border-t border-line pt-2">
            <p className="text-[13px] text-muted">Nhập tay hoàn toàn: cần biển số và loại xe ở thanh dưới.</p>
            <Button className="h-11" onClick={doManualEntry} disabled={busy || !plateTrim || !group}>
              Ghi nhận nhập tay
            </Button>
          </div>
        )}

        {manualOpen && direction === "out" && (
          <p className="border-t border-line pt-2 text-[13px] text-muted">
            Nhập tay RA: chọn phiên trong danh sách để nối.
          </p>
        )}
      </div>

      {/* Thanh thao tác ghim đáy: luôn thấy, không nằm trong vùng cuộn. Biển số
          + loại xe + màu biển + giá gộp chung 1 hàng để đọc liền mạch như một
          dải "đối chiếu trước khi xác nhận", thay vì biển số chiếm hẳn 1 hàng
          rộng lênh khênh rồi tách rời 2 dropdown ở hàng dưới. */}
      <div className="shrink-0 space-y-2 border-t border-line pt-2">
        <div className="flex flex-wrap items-end gap-3">
          <PlateField
            id={plateFieldId}
            value={plate}
            onChange={setPlate}
            size="lg"
            highlight={state === "needs_review"}
          />

          <div className="w-[150px] shrink-0">
            <label htmlFor={`${plateFieldId}-vtype`} className="mb-1 block text-[12px] text-muted">
              Loại xe
            </label>
            <select
              id={`${plateFieldId}-vtype`}
              aria-label="Loại xe"
              className="h-9 w-full rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
              value={vType}
              onChange={(e) => setVType(e.target.value)}
            >
              <option value="">—</option>
              {VEHICLE_TYPE_OPTIONS.map((o) => (
                <option key={o.code} value={o.code}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="w-[160px] shrink-0">
            <label htmlFor={`${plateFieldId}-color`} className="mb-1 block text-[12px] text-muted">
              Màu biển
            </label>
            <div className="flex items-center gap-1.5">
              <span
                className="inline-block h-4 w-4 shrink-0 rounded-full border border-line"
                style={{ background: plateColor(color)?.swatch ?? "transparent" }}
              />
              <select
                id={`${plateFieldId}-color`}
                aria-label="Màu biển"
                className="h-9 w-full rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
                value={color}
                onChange={(e) => setColor(e.target.value)}
              >
                <option value="">—</option>
                {PLATE_COLOR_OPTIONS.map((o) => (
                  <option key={o.code} value={o.code}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {direction === "in" && (
            <div className="min-w-[130px] shrink-0">
              <span className="mb-1 block text-[12px] text-muted">
                {vType ? `Giá ${vehicleTypeLabel(vType)}` : "Giá"}
              </span>
              <span className="tnum block h-9 leading-9 text-sm font-medium" data-testid="entry-price">
                {!vType ? "Chọn loại xe" : (priceText ?? "Chưa có bảng giá")}
              </span>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-line pt-2">
          {direction === "in" ? (
            <>
              <Button className="h-11 min-w-[44px]" onClick={() => doEntry(false)} disabled={entryDisabled}>
                Xác nhận VÀO
              </Button>
              {!plateTrim && (
                <Button variant="outline" className="h-11" onClick={() => doEntry(true)} disabled={busy}>
                  Vào không biển (phiên chờ)
                </Button>
              )}
              {dupBlocked && (
                <Button variant="outline" className="h-11" onClick={() => doEntry(false, true)} disabled={busy}>
                  Vào (ghi đè trùng)
                </Button>
              )}
            </>
          ) : (
            <Button className="h-11 min-w-[44px]" onClick={() => doExitPreview()} disabled={exitDisabled}>
              Đối chiếu &amp; cho RA
            </Button>
          )}

          {!manualOpen && (
            <Button variant="secondary" className="h-11" onClick={() => setManualOpen(true)}>
              Nhập tay
            </Button>
          )}

          {!plateTrim && direction === "in" && (
            <span className="text-[13px] text-muted">Cần biển số, hoặc dùng "Vào không biển".</span>
          )}
        </div>
      </div>
    </div>
  );
});
