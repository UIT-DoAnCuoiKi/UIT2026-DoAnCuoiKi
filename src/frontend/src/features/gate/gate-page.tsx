import { useCallback, useEffect, useRef, useState } from "react";
import { GatePanel, type GatePanelHandle } from "./gate-panel";
import { latestForDirectionAndLane, useGateSocket } from "./use-gate-socket";
import { useGateShortcuts, type ShortcutAction } from "./use-gate-shortcuts";
import { useListLanes } from "@/api/generated/config/config";
import { Button } from "@/components/ui/button";

type LayoutMode = "split" | "in" | "out";
const LS_KEY = "gate-layout-mode";
// Làn VÀO và làn RA thường là 2 vị trí vật lý khác nhau trong bãi xe (không
// phải cùng 1 làn đổi chiều), nên mỗi panel nhớ lựa chọn làn riêng của nó.
const LANE_KEY_IN = "gate-lane-in";
const LANE_KEY_OUT = "gate-lane-out";

const SHORTCUTS: { key: string; desc: string }[] = [
  { key: "1 / 2", desc: "Focus panel VÀO / RA" },
  { key: "Space", desc: "Chụp khung hình" },
  { key: "Enter", desc: "Xác nhận VÀO/RA hoặc thu tiền" },
  { key: "E", desc: "Sửa biển" },
  { key: "M", desc: "Nhập tay" },
  { key: "R", desc: "Hoàn tác sửa (trả về giá trị model)" },
  { key: "Esc", desc: "Hủy kết quả panel" },
  { key: "1/2/3", desc: "Chọn phương thức khi thu tiền" },
  { key: "?", desc: "Bật/tắt bảng phím tắt" },
];

export function GatePage() {
  // events (không phải capturesByDirection) để tự lọc theo làn ở dưới — 1 kết
  // nối WS dùng chung, mỗi panel chỉ lấy đúng capture của làn nó đang trực.
  const { events, degraded } = useGateSocket();
  const { data: lanes = [] } = useListLanes();
  const [layout, setLayout] = useState<LayoutMode>(() => (localStorage.getItem(LS_KEY) as LayoutMode) || "split");
  const [active, setActive] = useState<"in" | "out">("in");
  const [showHelp, setShowHelp] = useState(false);
  const [payOpen, setPayOpen] = useState<{ in: boolean; out: boolean }>({ in: false, out: false });
  const [laneNameIn, setLaneNameIn] = useState<string>(() => localStorage.getItem(LANE_KEY_IN) ?? "");
  const [laneNameOut, setLaneNameOut] = useState<string>(() => localStorage.getItem(LANE_KEY_OUT) ?? "");

  const inRef = useRef<GatePanelHandle | null>(null);
  const outRef = useRef<GatePanelHandle | null>(null);

  useEffect(() => {
    localStorage.setItem(LS_KEY, layout);
    if (layout === "in") setActive("in");
    if (layout === "out") setActive("out");
  }, [layout]);

  useEffect(() => localStorage.setItem(LANE_KEY_IN, laneNameIn), [laneNameIn]);
  useEffect(() => localStorage.setItem(LANE_KEY_OUT, laneNameOut), [laneNameOut]);

  const laneIn = lanes.find((l) => l.name === laneNameIn);
  const laneOut = lanes.find((l) => l.name === laneNameOut);
  const wsCaptureIn = latestForDirectionAndLane(events, "in", laneNameIn || null);
  const wsCaptureOut = latestForDirectionAndLane(events, "out", laneNameOut || null);

  const activeRef = () => (active === "in" ? inRef.current : outRef.current);

  // Phải ổn định identity (useCallback, không tạo hàm mới mỗi render): DecisionPanel
  // đặt callback này trong dependency của 1 useEffect, nên nếu đổi reference mỗi
  // lần GatePage render sẽ tạo vòng lặp vô hạn (effect chạy lại -> setState ->
  // GatePage render lại -> effect chạy lại...).
  const onPayOpenChangeIn = useCallback((open: boolean) => setPayOpen((p) => ({ ...p, in: open })), []);
  const onPayOpenChangeOut = useCallback((open: boolean) => setPayOpen((p) => ({ ...p, out: open })), []);

  const onAction = useCallback(
    (action: Exclude<ShortcutAction, null>) => {
      switch (action) {
        case "focus-in":
          if (layout !== "out") setActive("in");
          break;
        case "focus-out":
          if (layout !== "in") setActive("out");
          break;
        case "capture":
          activeRef()?.capture();
          break;
        case "edit-plate":
          activeRef()?.focusPlate();
          break;
        case "confirm":
        case "dialog-confirm":
          activeRef()?.confirm();
          break;
        case "manual":
          activeRef()?.manual();
          break;
        case "reset":
          activeRef()?.reset();
          break;
        case "cancel":
        case "dialog-close":
          activeRef()?.cancel();
          break;
        case "method-1":
          activeRef()?.payMethod(1);
          break;
        case "method-2":
          activeRef()?.payMethod(2);
          break;
        case "method-3":
          activeRef()?.payMethod(3);
          break;
        case "toggle-help":
          setShowHelp((v) => !v);
          break;
        default:
          break;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [active, layout],
  );

  useGateShortcuts({ dialogOpen: payOpen[active], onAction });

  const showIn = layout === "split" || layout === "in";
  const showOut = layout === "split" || layout === "out";

  return (
    <div className="flex h-full flex-col gap-[14px]">
      {degraded && (
        <div role="status" className="rounded-[var(--radius-control)] bg-tile-peri px-4 py-2 text-[13px] text-[#1c1c1c]">
          Mất kết nối realtime. Đang dùng chế độ dự phòng (polling).
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button variant={layout === "split" ? "default" : "outline"} className="h-9" onClick={() => setLayout("split")}>
          Chia đôi
        </Button>
        <Button variant={layout === "in" ? "default" : "outline"} className="h-9" onClick={() => setLayout("in")}>
          Chỉ VÀO
        </Button>
        <Button variant={layout === "out" ? "default" : "outline"} className="h-9" onClick={() => setLayout("out")}>
          Chỉ RA
        </Button>
        <Button variant="outline" className="h-9" onClick={() => setShowHelp((v) => !v)}>
          Phím tắt (?)
        </Button>

        {/* Chọn làn đang trực cho từng hướng — rỗng nghĩa là không lọc theo
            làn (hành vi cũ), dùng khi chưa cấu hình làn nào hoặc chỉ có 1 làn. */}
        {showIn && (
          <select
            aria-label="Làn đang trực (VÀO)"
            className="h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-[13px]"
            value={laneNameIn}
            onChange={(e) => setLaneNameIn(e.target.value)}
          >
            <option value="">Làn VÀO: chưa chọn</option>
            {lanes.map((l) => (
              <option key={l.id} value={l.name}>
                Làn VÀO: {l.name}
              </option>
            ))}
          </select>
        )}
        {showOut && (
          <select
            aria-label="Làn đang trực (RA)"
            className="h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-[13px]"
            value={laneNameOut}
            onChange={(e) => setLaneNameOut(e.target.value)}
          >
            <option value="">Làn RA: chưa chọn</option>
            {lanes.map((l) => (
              <option key={l.id} value={l.name}>
                Làn RA: {l.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div
        className={
          layout === "split"
            ? "grid min-h-0 flex-1 grid-rows-1 grid-cols-1 gap-[14px] lg:grid-cols-2"
            : "grid min-h-0 flex-1 grid-rows-1 grid-cols-1 gap-[14px]"
        }
      >
        {showIn && (
          <GatePanel
            ref={inRef}
            direction="in"
            wide={layout !== "split"}
            wsCapture={wsCaptureIn}
            active={active === "in"}
            onActivate={() => setActive("in")}
            onPayOpenChange={onPayOpenChangeIn}
            laneName={laneIn?.name}
            laneCameras={laneIn?.cameras}
          />
        )}
        {showOut && (
          <GatePanel
            ref={outRef}
            direction="out"
            wide={layout !== "split"}
            wsCapture={wsCaptureOut}
            active={active === "out"}
            onActivate={() => setActive("out")}
            onPayOpenChange={onPayOpenChangeOut}
            laneName={laneOut?.name}
            laneCameras={laneOut?.cameras}
          />
        )}
      </div>

      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true" onClick={() => setShowHelp(false)}>
          <div className="w-[360px] space-y-2 rounded-[var(--radius-control)] bg-bg p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-semibold">Phím tắt</p>
            <ul className="space-y-1 text-[13px]">
              {SHORTCUTS.map((s) => (
                <li key={s.key} className="flex justify-between gap-4">
                  <span className="font-mono">{s.key}</span>
                  <span className="text-muted">{s.desc}</span>
                </li>
              ))}
            </ul>
            <Button variant="outline" onClick={() => setShowHelp(false)}>
              Đóng
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
