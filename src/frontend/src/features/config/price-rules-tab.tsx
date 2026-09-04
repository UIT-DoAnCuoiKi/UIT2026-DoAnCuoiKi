import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";
import { useListPriceRules, useUpdatePriceRule } from "@/api/generated/config/config";
import type { PriceRuleOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";

export function PriceRulesTab() {
  const { data, isLoading } = useListPriceRules();
  const update = useUpdatePriceRule();
  const cols: ColumnDef<PriceRuleOut, unknown>[] = [
    { header: "Nhóm", accessorKey: "vehicle_group" },
    { header: "Chế độ", accessorKey: "mode" },
    {
      header: "Đơn giá",
      cell: ({ row }) => <span className="tnum">{formatVnd(row.original.unit_price)}</span>,
    },
    { header: "Block (phút)", cell: ({ row }) => row.original.block_minutes ?? "—" },
    {
      header: "Kích hoạt",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            await update.mutateAsync({ ruleId: row.original.id, data: { active: !row.original.active } });
            toast.success("Đã cập nhật");
          }}
        >
          {row.original.active ? "Bật" : "Tắt"}
        </Button>
      ),
    },
  ];
  return <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có bảng giá" />;
}
