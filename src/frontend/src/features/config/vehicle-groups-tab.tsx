import { useState } from "react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useListVehicleGroups,
  useCreateVehicleGroup,
  useUpdateVehicleGroup,
  useDeleteVehicleGroup,
} from "@/api/generated/vehicle-groups/vehicle-groups";
import { useListPriceRules, useCreatePriceRule, useUpdatePriceRule } from "@/api/generated/config/config";
import type { VehicleGroupOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatVnd } from "@/lib/format";
import { isAxiosError } from "axios";

export function VehicleGroupsTab() {
  const { data: groups, isLoading } = useListVehicleGroups();
  const { data: rules } = useListPriceRules();
  const update = useUpdateVehicleGroup();
  const remove = useDeleteVehicleGroup();
  const create = useCreateVehicleGroup();
  const createRule = useCreatePriceRule();
  const updateRule = useUpdatePriceRule();

  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");

  const ruleFor = (code: string) => (rules ?? []).find((r) => r.vehicle_group === code && r.active);

  const setPrice = async (code: string, unitPrice: number) => {
    const existing = ruleFor(code);
    if (existing) {
      await updateRule.mutateAsync({ ruleId: existing.id, data: { unit_price: unitPrice } });
    } else {
      await createRule.mutateAsync({ data: { vehicle_group: code, mode: "flat", unit_price: unitPrice } });
    }
    toast.success("Đã cập nhật giá");
  };

  const cols: ColumnDef<VehicleGroupOut, unknown>[] = [
    { header: "Tên hiển thị", accessorKey: "display_name" },
    { header: "Mã", accessorKey: "code" },
    {
      header: "Đơn giá",
      cell: ({ row }) => {
        const rule = ruleFor(row.original.code);
        return <span className="tnum">{rule ? formatVnd(rule.unit_price) : "—"}</span>;
      },
    },
    {
      header: "Đặt giá",
      cell: ({ row }) => (
        <PriceCell current={ruleFor(row.original.code)?.unit_price ?? null} onSave={(v) => setPrice(row.original.code, v)} />
      ),
    },
    {
      header: "Kích hoạt",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            await update.mutateAsync({ groupId: row.original.id, data: { active: !row.original.active } });
            toast.success("Đã cập nhật");
          }}
        >
          {row.original.active ? "Bật" : "Tắt"}
        </Button>
      ),
    },
    {
      header: "Xóa",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            try {
              await remove.mutateAsync({ groupId: row.original.id });
              toast.success("Đã xóa nhóm");
            } catch (e) {
              if (isAxiosError(e) && e.response?.status === 409) {
                toast.error("Nhóm đang được sử dụng, không xóa được");
              } else {
                toast.error("Xóa thất bại");
              }
            }
          }}
        >
          Xóa
        </Button>
      ),
    },
  ];

  const addGroup = async () => {
    if (!newCode.trim() || !newName.trim()) {
      toast.error("Nhập mã và tên hiển thị");
      return;
    }
    await create.mutateAsync({ data: { code: newCode.trim(), display_name: newName.trim() } });
    setNewCode("");
    setNewName("");
    toast.success("Đã thêm nhóm");
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <Input placeholder="Mã (vd: xe_dien)" value={newCode} onChange={(e) => setNewCode(e.target.value)} className="max-w-[180px]" />
        <Input placeholder="Tên hiển thị (vd: Xe điện)" value={newName} onChange={(e) => setNewName(e.target.value)} className="max-w-[220px]" />
        <Button onClick={addGroup}>Thêm nhóm</Button>
      </div>
      <DataTable columns={cols} data={groups ?? []} loading={isLoading} empty="Chưa có nhóm xe" />
    </div>
  );
}

function PriceCell({ current, onSave }: { current: number | null; onSave: (value: number) => Promise<void> }) {
  const [value, setValue] = useState<string>(current != null ? String(current) : "");
  return (
    <div className="flex items-center gap-1">
      <Input
        type="number"
        min={0}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="h-8 w-[110px]"
        aria-label="Đơn giá"
      />
      <Button
        variant="outline"
        size="sm"
        onClick={async () => {
          const n = Number(value);
          if (!Number.isFinite(n) || n < 0) {
            toast.error("Giá không hợp lệ");
            return;
          }
          await onSave(n);
        }}
      >
        Lưu
      </Button>
    </div>
  );
}
