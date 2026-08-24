import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";
import { useListUsers, useUpdateUser } from "@/api/generated/users/users";
import type { UserOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";

export function UsersTab() {
  const { data, isLoading } = useListUsers();
  const update = useUpdateUser();
  const cols: ColumnDef<UserOut, unknown>[] = [
    { header: "Tên đăng nhập", accessorKey: "username" },
    { header: "Vai", accessorKey: "role" },
    {
      header: "Kích hoạt",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            await update.mutateAsync({ userId: row.original.id, data: { active: !row.original.active } });
            toast.success("Đã cập nhật");
          }}
        >
          {row.original.active ? "Bật" : "Tắt"}
        </Button>
      ),
    },
  ];
  return <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có tài khoản" />;
}
