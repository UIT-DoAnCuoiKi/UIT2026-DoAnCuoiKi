import { useEffect, useState } from "react";
import { useGetStats } from "@/api/generated/stats/stats";
import { KpiTile } from "@/components/kpi-tile";
import { SurfaceCard } from "@/components/surface-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getRole } from "@/lib/auth";
import { formatVnd } from "@/lib/format";
import { downloadStatsCsv, fetchDailyRows, type DailyRow } from "./stats-export";
import { TrafficLineChart } from "@/components/charts/line-chart";
import { RevenueBarChart } from "@/components/charts/bar-chart";
import { GroupDonutChart } from "@/components/charts/donut-chart";

export function StatsPage() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const { data, isLoading } = useGetStats(from || to ? { from: from || null, to: to || null } : undefined);
  const s = (data ?? {}) as { in_lot?: number; entries?: number; exits?: number; revenue?: number };
  const role = getRole();
  const isAdmin = role === "manager" || role === "root";
  const [rows, setRows] = useState<DailyRow[]>([]);

  useEffect(() => {
    fetchDailyRows(from, to)
      .then(setRows)
      .catch(() => setRows([]));
  }, [from, to]);

  return (
    <div className="space-y-[18px]">
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-[13px] text-muted">
          Từ
          <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label className="text-[13px] text-muted">
          Đến
          <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
        {isAdmin && (
          <Button className="ml-auto" onClick={() => downloadStatsCsv(from, to)}>
            Xuất CSV
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
        <KpiTile title="Đang trong bãi" value={String(s.in_lot ?? 0)} tile="blue" loading={isLoading} />
        <KpiTile title="Lưu lượng hôm nay" value={String(s.entries ?? 0)} tile="peri" loading={isLoading} />
        <KpiTile title="Doanh thu hôm nay" value={formatVnd(s.revenue ?? 0)} tile="mint" loading={isLoading} />
        <KpiTile title="Ra hôm nay" value={String(s.exits ?? 0)} tile="purple" loading={isLoading} />
      </div>

      <SurfaceCard variant="white">
        <h2 className="mb-3 text-sm font-semibold">Lưu lượng theo ngày</h2>
        <TrafficLineChart data={rows} />
        <table className="sr-only">
          <caption>Bảng số lưu lượng</caption>
          <thead>
            <tr>
              <th>Ngày</th>
              <th>Vào</th>
              <th>Ra</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.date}>
                <td>{r.date}</td>
                <td>{r.entries}</td>
                <td>{r.exits}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SurfaceCard>

      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
        <SurfaceCard variant="white">
          <h2 className="mb-3 text-sm font-semibold">Doanh thu theo ngày</h2>
          <RevenueBarChart data={rows} />
        </SurfaceCard>
        <SurfaceCard variant="white">
          <h2 className="mb-3 text-sm font-semibold">Cơ cấu nhóm xe</h2>
          <GroupDonutChart data={[]} />
        </SurfaceCard>
      </div>
    </div>
  );
}
