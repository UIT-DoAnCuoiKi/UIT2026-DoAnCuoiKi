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

// Ngày địa phương dạng YYYY-MM-DD cho input type=date (tránh lệch múi giờ của toISOString).
function localDate(d: Date): string {
  const off = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - off).toISOString().slice(0, 10);
}

type QuickRange = "1d" | "1w" | "1m";
const QUICK_RANGES: { key: QuickRange; label: string; days: number }[] = [
  { key: "1d", label: "1 ngày", days: 1 },
  { key: "1w", label: "1 tuần", days: 7 },
  { key: "1m", label: "1 tháng", days: 30 },
];

export function StatsPage() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [range, setRange] = useState<QuickRange | null>(null);

  const applyQuickRange = (r: QuickRange, days: number) => {
    const today = new Date();
    const start = new Date();
    start.setDate(today.getDate() - (days - 1));
    setFrom(localDate(start));
    setTo(localDate(today));
    setRange(r);
  };
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
        <div className="flex items-center gap-1.5" role="group" aria-label="Lọc nhanh theo khoảng thời gian">
          {QUICK_RANGES.map((q) => (
            <Button
              key={q.key}
              variant={range === q.key ? "default" : "outline"}
              size="sm"
              className="h-9"
              aria-pressed={range === q.key}
              onClick={() => applyQuickRange(q.key, q.days)}
            >
              {q.label}
            </Button>
          ))}
        </div>
        <label className="text-[13px] text-muted">
          Từ
          <Input
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setRange(null);
            }}
          />
        </label>
        <label className="text-[13px] text-muted">
          Đến
          <Input
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setRange(null);
            }}
          />
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
