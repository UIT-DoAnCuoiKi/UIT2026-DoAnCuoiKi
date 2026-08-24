import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";

const TILE: Record<string, string> = {
  blue: "bg-tile-blue",
  purple: "bg-tile-purple",
  mint: "bg-tile-mint",
  peri: "bg-tile-peri",
};

export function KpiTile({
  title,
  value,
  tile,
  delta,
  loading = false,
}: {
  title: string;
  value: string;
  tile: "blue" | "purple" | "mint" | "peri";
  delta?: number;
  loading?: boolean;
}) {
  return (
    <div className={cn("rounded-[var(--radius-card)] p-5", TILE[tile])}>
      <p className="text-[13px] text-[#1c1c1c]/70">{title}</p>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-20" />
      ) : (
        <div className="mt-2 flex items-end justify-between">
          <span className="tnum text-2xl font-semibold text-[#1c1c1c]">{value}</span>
          {delta !== undefined && (
            <span
              className={cn(
                "flex items-center gap-0.5 text-[13px]",
                delta >= 0 ? "text-st-green" : "text-st-red",
              )}
            >
              {delta >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {Math.abs(delta)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}
