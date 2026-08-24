import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";
import { useListLanes, useUpdateLane } from "@/api/generated/config/config";
import type { LaneOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";

export function LanesTab() {
  const { data, isLoading } = useListLanes();
  const update = useUpdateLane();
  const cols: ColumnDef<LaneOut, unknown>[] = [
    { header: "Tên", accessorKey: "name" },
    { header: "RTSP", cell: ({ row }) => row.original.rtsp_url ?? "—" },
    {
      header: "Kích hoạt",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            await update.mutateAsync({ laneId: row.original.id, data: { active: !row.original.active } });
            toast.success("Đã cập nhật");
          }}
        >
          {row.original.active ? "Bật" : "Tắt"}
        </Button>
      ),
    },
  ];
  return <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có lane" />;
}
