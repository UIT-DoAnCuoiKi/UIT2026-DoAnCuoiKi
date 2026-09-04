import { useMemo, useState } from "react";
import { useListSessions } from "@/api/generated/sessions/sessions";
import type { ListSessionsParams } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { sessionColumns } from "./sessions-columns";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SurfaceCard } from "@/components/surface-card";
import { useVehicleGroupMap } from "@/lib/vehicle-groups";
import { matchFlagLabel } from "@/lib/labels";

const PAGE = 20;
const STATUSES = ["", "in_lot", "completed", "disputed", "pending_manual"];
const STATUS_LABEL: Record<string, string> = {
  in_lot: "Trong bãi",
  completed: "Hoàn tất",
  disputed: "Tranh chấp",
  pending_manual: "Chờ xử lý tay",
};
const MATCH_FLAGS = ["", "exact", "auto_corrected", "manual", "lost_ticket"];
const SELECT_CLASS =
  "h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm";

export function SessionsPage() {
  const [plate, setPlate] = useState("");
  const [status, setStatus] = useState("");
  const [group, setGroup] = useState("");
  const [matchFlag, setMatchFlag] = useState("");
  const [entryFrom, setEntryFrom] = useState("");
  const [entryTo, setEntryTo] = useState("");
  const [offset, setOffset] = useState(0);
  const groupMap = useVehicleGroupMap();

  const params: ListSessionsParams = useMemo(
    () => ({
      plate: plate || null,
      status: status || null,
      vehicle_group: group || null,
      match_flag: matchFlag || null,
      entry_from: entryFrom ? new Date(entryFrom + "T00:00:00").toISOString() : null,
      entry_to: entryTo ? new Date(new Date(entryTo + "T00:00:00").getTime() + 86400000).toISOString() : null,
      limit: PAGE,
      offset,
    }),
    [plate, status, group, matchFlag, entryFrom, entryTo, offset],
  );
  const { data, isLoading } = useListSessions(params);
  const total = data?.total ?? 0;

  const reset = () => setOffset(0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          placeholder="Tra biển số"
          value={plate}
          onChange={(e) => {
            setPlate(e.target.value);
            reset();
          }}
          aria-label="Tra biển số"
        />
        <select
          className={SELECT_CLASS}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            reset();
          }}
          aria-label="Lọc trạng thái"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? STATUS_LABEL[s] ?? s : "Tất cả trạng thái"}
            </option>
          ))}
        </select>
        <select
          className={SELECT_CLASS}
          value={group}
          onChange={(e) => {
            setGroup(e.target.value);
            reset();
          }}
          aria-label="Lọc nhóm xe"
        >
          <option value="">Tất cả nhóm xe</option>
          {Object.entries(groupMap).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
        <select
          className={SELECT_CLASS}
          value={matchFlag}
          onChange={(e) => {
            setMatchFlag(e.target.value);
            reset();
          }}
          aria-label="Lọc cách khớp"
        >
          {MATCH_FLAGS.map((m) => (
            <option key={m} value={m}>
              {m ? matchFlagLabel(m) : "Tất cả cách khớp"}
            </option>
          ))}
        </select>
        <input
          type="date"
          className={SELECT_CLASS}
          value={entryFrom}
          onChange={(e) => {
            setEntryFrom(e.target.value);
            reset();
          }}
          aria-label="Giờ vào từ"
        />
        <input
          type="date"
          className={SELECT_CLASS}
          value={entryTo}
          onChange={(e) => {
            setEntryTo(e.target.value);
            reset();
          }}
          aria-label="Giờ vào đến"
        />
      </div>
      <SurfaceCard variant="white">
        <DataTable
          columns={sessionColumns}
          data={data?.items ?? []}
          loading={isLoading}
          empty="Chưa có phiên"
        />
      </SurfaceCard>
      <div className="flex items-center justify-end gap-2 text-sm">
        <Button
          variant="outline"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE))}
        >
          Trước
        </Button>
        <span className="tnum text-muted">
          {offset + 1}–{Math.min(offset + PAGE, total)} / {total}
        </span>
        <Button
          variant="outline"
          disabled={offset + PAGE >= total}
          onClick={() => setOffset((o) => o + PAGE)}
        >
          Sau
        </Button>
      </div>
    </div>
  );
}
