import {
  ResponsiveContainer,
  LineChart as RLine,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import type { DailyRow } from "@/features/stats/stats-export";
import { EmptyState } from "@/components/empty-state";

export function TrafficLineChart({ data }: { data: DailyRow[] }) {
  if (data.length === 0) return <EmptyState title="Chưa có dữ liệu lưu lượng" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <RLine data={data}>
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis dataKey="date" stroke="var(--muted)" fontSize={12} />
        <YAxis stroke="var(--muted)" fontSize={12} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="entries" name="Vào" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="exits" name="Ra" stroke="var(--chart-3)" strokeWidth={2} dot={false} />
      </RLine>
    </ResponsiveContainer>
  );
}
