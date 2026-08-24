import { useMemo, useState } from "react";
import { useListSessions } from "@/api/generated/sessions/sessions";
import type { ListSessionsParams } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { sessionColumns } from "./sessions-columns";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SurfaceCard } from "@/components/surface-card";

const PAGE = 20;
const STATUSES = ["", "in_lot", "completed", "disputed", "pending_manual"];

export function SessionsPage() {
  const [plate, setPlate] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);

  const params: ListSessionsParams = useMemo(
    () => ({ plate: plate || null, status: status || null, limit: PAGE, offset }),
    [plate, status, offset],
  );
  const { data, isLoading } = useListSessions(params);
  const total = data?.total ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          placeholder="Tra biển số"
          value={plate}
          onChange={(e) => {
            setPlate(e.target.value);
            setOffset(0);
          }}
          aria-label="Tra biển số"
        />
        <select
          className="h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
          aria-label="Lọc trạng thái"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s || "Tất cả trạng thái"}
            </option>
          ))}
        </select>
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
