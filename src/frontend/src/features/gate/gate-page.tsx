import { useState } from "react";
import { GateKpis } from "./gate-kpis";
import { GateCaptureView } from "./gate-capture";
import { DecisionPanel } from "./decision-panel";
import { GateEventsRail } from "./gate-events-rail";
import { useGateSocket } from "./use-gate-socket";
import { SurfaceCard } from "@/components/surface-card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";

export function GatePage() {
  const { capture, events, degraded } = useGateSocket();
  const [direction, setDirection] = useState<"in" | "out">("in");
  return (
    <div className="space-y-[18px]">
      {degraded && (
        <div
          role="status"
          className="rounded-[var(--radius-control)] bg-tile-peri px-4 py-2 text-[13px] text-[#1c1c1c]"
        >
          Mất kết nối realtime. Đang dùng chế độ dự phòng (polling).
        </div>
      )}
      <GateKpis />
      <div className="flex gap-2">
        <Button
          variant={direction === "in" ? "default" : "outline"}
          className="h-11"
          onClick={() => setDirection("in")}
        >
          Hướng VÀO
        </Button>
        <Button
          variant={direction === "out" ? "default" : "outline"}
          className="h-11"
          onClick={() => setDirection("out")}
        >
          Hướng RA
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2 xl:grid-cols-[1fr_1fr_300px]">
        <GateCaptureView capture={capture} />
        <SurfaceCard variant="white">
          {capture ? (
            <DecisionPanel capture={capture} direction={direction} onDone={() => {}} />
          ) : (
            <EmptyState title="Chưa có lượt chụp" hint="Đang chờ sự kiện từ cổng" />
          )}
        </SurfaceCard>
        <SurfaceCard variant="surface" className="xl:col-auto lg:col-span-2 xl:col-span-1">
          <h2 className="mb-3 text-sm font-semibold">Sự kiện cổng</h2>
          <GateEventsRail events={events} />
        </SurfaceCard>
      </div>
    </div>
  );
}
