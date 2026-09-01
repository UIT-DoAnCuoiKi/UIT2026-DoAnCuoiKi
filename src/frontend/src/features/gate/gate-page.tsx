import { useCallback, useEffect, useRef, useState } from "react";
import { GatePanel, type GatePanelHandle } from "./gate-panel";
import { useGateSocket } from "./use-gate-socket";
import { useGateShortcuts, type ShortcutAction } from "./use-gate-shortcuts";
import { Button } from "@/components/ui/button";

type LayoutMode = "split" | "in" | "out";
const LS_KEY = "gate-layout-mode";

const SHORTCUTS: { key: string; desc: string }[] = [
  { key: "1 / 2", desc: "Focus panel VÀO / RA" },
  { key: "Space", desc: "Chụp khung hình" },
  { key: "Enter", desc: "Xác nhận VÀO/RA hoặc thu tiền" },
  { key: "E", desc: "Sửa biển" },
  { key: "M", desc: "Nhập tay" },
  { key: "Esc", desc: "Hủy kết quả panel" },
  { key: "1/2/3", desc: "Chọn phương thức khi thu tiền" },
  { key: "?", desc: "Bật/tắt bảng phím tắt" },
];

export function GatePage() {
  const { capturesByDirection, degraded } = useGateSocket();
  const [layout, setLayout] = useState<LayoutMode>(() => (localStorage.getItem(LS_KEY) as LayoutMode) || "split");
  const [active, setActive] = useState<"in" | "out">("in");
  const [showHelp, setShowHelp] = useState(false);
  const [payOpen, setPayOpen] = useState<{ in: boolean; out: boolean }>({ in: false, out: false });

  const inRef = useRef<GatePanelHandle | null>(null);
  const outRef = useRef<GatePanelHandle | null>(null);

  useEffect(() => {
    localStorage.setItem(LS_KEY, layout);
    if (layout === "in") setActive("in");
    if (layout === "out") setActive("out");
  }, [layout]);

  const activeRef = () => (active === "in" ? inRef.current : outRef.current);

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
      </div>

      <div
        className={
          layout === "split"
            ? "grid min-h-0 flex-1 grid-cols-1 gap-[14px] lg:grid-cols-2"
            : "grid min-h-0 flex-1 grid-cols-1 gap-[14px]"
        }
      >
        {showIn && (
          <GatePanel
            ref={inRef}
            direction="in"
            wsCapture={capturesByDirection.in}
            active={active === "in"}
            onActivate={() => setActive("in")}
            onPayOpenChange={(open) => setPayOpen((p) => ({ ...p, in: open }))}
          />
        )}
        {showOut && (
          <GatePanel
            ref={outRef}
            direction="out"
            wsCapture={capturesByDirection.out}
            active={active === "out"}
            onActivate={() => setActive("out")}
            onPayOpenChange={(open) => setPayOpen((p) => ({ ...p, out: open }))}
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
