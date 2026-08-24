import type { GateCapture } from "./use-gate-socket";
import { StatusDot } from "@/components/status-chip";
import { formatPlate } from "@/lib/format";

export function GateEventsRail({ events }: { events: GateCapture[] }) {
  if (events.length === 0) return <p className="text-[13px] text-muted">Chưa có sự kiện</p>;
  return (
    <ul className="space-y-2">
      {events.map((e) => (
        <li key={e.capture_id} className="flex items-center gap-2 text-[13px]">
          <StatusDot kind="review" value={e.review_state} />
          <span className="tnum font-medium">{formatPlate(e.plate_text)}</span>
          <span className="ml-auto text-muted">{e.direction === "in" ? "VÀO" : "RA"}</span>
        </li>
      ))}
    </ul>
  );
}
