import { Link } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import type { SessionListItem } from "@/api/generated/model";
import { StatusChip } from "@/components/status-chip";
import { formatPlate, formatVnd, formatDateTime, formatDuration } from "@/lib/format";
import { useVehicleGroupMap, groupLabel } from "@/lib/vehicle-groups";

function GroupCell({ code }: { code?: string | null }) {
  const map = useVehicleGroupMap();
  return <>{groupLabel(map, code)}</>;
}

export const sessionColumns: ColumnDef<SessionListItem, unknown>[] = [
  {
    header: "Biển số",
    accessorKey: "plate_text",
    cell: ({ row }) => (
      <Link to={`/sessions/${row.original.id}`} className="tnum font-medium">
        {formatPlate(row.original.plate_text)}
      </Link>
    ),
  },
  {
    header: "Nhóm xe",
    accessorKey: "vehicle_group",
    cell: ({ row }) => <GroupCell code={row.original.vehicle_group} />,
  },
  { header: "Giờ vào", cell: ({ row }) => formatDateTime(row.original.entry_time) },
  { header: "Giờ ra", cell: ({ row }) => formatDateTime(row.original.exit_time) },
  {
    header: "Thời lượng",
    cell: ({ row }) => formatDuration(row.original.entry_time, row.original.exit_time),
  },
  {
    header: "Phí",
    cell: ({ row }) => <span className="tnum">{formatVnd(row.original.fee_amount)}</span>,
  },
  { header: "Loại xe", cell: ({ row }) => row.original.vehicle_type ?? "—" },
  { header: "Nhân viên", cell: ({ row }) => row.original.closed_by_name ?? "—" },
  { header: "Phương thức", cell: ({ row }) => row.original.payment_method ?? "—" },
  {
    header: "Trạng thái",
    cell: ({ row }) => <StatusChip kind="session" value={row.original.status} />,
  },
  { header: "Khớp", cell: ({ row }) => row.original.match_flag ?? "—" },
];
