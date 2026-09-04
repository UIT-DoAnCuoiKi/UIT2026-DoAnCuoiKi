import {
  ResponsiveContainer,
  BarChart as RBar,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { DailyRow } from "@/features/stats/stats-export";
import { EmptyState } from "@/components/empty-state";

export function RevenueBarChart({ data }: { data: DailyRow[] }) {
  if (data.length === 0) return <EmptyState title="Chưa có dữ liệu doanh thu" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <RBar data={data}>
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis dataKey="date" stroke="var(--muted)" fontSize={12} />
        <YAxis stroke="var(--muted)" fontSize={12} />
        <Tooltip />
        <Bar dataKey="revenue" name="Doanh thu" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
      </RBar>
    </ResponsiveContainer>
  );
}
