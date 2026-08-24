import { useGetStats } from "@/api/generated/stats/stats";
import { KpiTile } from "@/components/kpi-tile";
import { formatVnd } from "@/lib/format";

export function GateKpis() {
  const { data, isLoading } = useGetStats();
  const s = (data ?? {}) as { in_lot?: number; entries?: number; exits?: number; revenue?: number };
  return (
    <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
      <KpiTile title="Đang trong bãi" value={String(s.in_lot ?? 0)} tile="blue" loading={isLoading} />
      <KpiTile title="Vào hôm nay" value={String(s.entries ?? 0)} tile="peri" loading={isLoading} />
      <KpiTile title="Ra hôm nay" value={String(s.exits ?? 0)} tile="mint" loading={isLoading} />
      <KpiTile title="Doanh thu" value={formatVnd(s.revenue ?? 0)} tile="purple" loading={isLoading} />
    </div>
  );
}
