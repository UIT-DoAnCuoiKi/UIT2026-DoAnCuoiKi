import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";

export function DataTable<T>({
  columns,
  data,
  loading = false,
  empty = "Không có dữ liệu",
}: {
  columns: ColumnDef<T, unknown>[];
  data: T[];
  loading?: boolean;
  empty?: string;
}) {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });
  if (loading)
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  if (data.length === 0) return <EmptyState title={empty} />;
  return (
    // w-full ép cột co lại làm chữ xuống dòng; cuộn ngang + nowrap giữ độ rộng cột trên màn hẹp.
    <div className="overflow-x-auto">
      <table className="w-full min-w-max text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-line text-left text-muted">
              {hg.headers.map((h) => (
                <th key={h.id} className="whitespace-nowrap px-3 py-2 font-medium">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-b border-line hover:bg-surface">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="whitespace-nowrap px-3 py-2">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
