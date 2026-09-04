import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useListVehicleGroups } from "@/api/generated/vehicle-groups/vehicle-groups";
import {
  useListPriceRules,
  useCreatePriceRule,
  useUpdatePriceRule,
  getListPriceRulesQueryKey,
} from "@/api/generated/config/config";
import type { VehicleGroupOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatVnd } from "@/lib/format";

// Danh mục loại xe cố định (seed backend). Màn này chỉ cho chỉnh đơn giá, không
// thêm/xóa nhóm và không hiển thị mã kỹ thuật.
export function VehicleGroupsTab() {
  const qc = useQueryClient();
  const { data: groups, isLoading } = useListVehicleGroups();
  const { data: rules } = useListPriceRules();
  const createRule = useCreatePriceRule();
  const updateRule = useUpdatePriceRule();

  const ruleFor = (code: string) => (rules ?? []).find((r) => r.vehicle_group === code && r.active);

  const setPrice = async (code: string, unitPrice: number) => {
    const existing = ruleFor(code);
    if (existing) {
      await updateRule.mutateAsync({ ruleId: existing.id, data: { unit_price: unitPrice } });
    } else {
      await createRule.mutateAsync({ data: { vehicle_group: code, mode: "flat", unit_price: unitPrice } });
    }
    await qc.invalidateQueries({ queryKey: getListPriceRulesQueryKey() });
    toast.success("Đã cập nhật giá");
  };

  const cols: ColumnDef<VehicleGroupOut, unknown>[] = [
    { header: "Loại xe", accessorKey: "display_name" },
    {
      header: "Đơn giá hiện tại",
      cell: ({ row }) => {
        const rule = ruleFor(row.original.code);
        return <span className="tnum">{rule ? formatVnd(rule.unit_price) : "chưa đặt"}</span>;
      },
    },
    {
      header: "Đặt giá",
      cell: ({ row }) => (
        <PriceCell
          key={ruleFor(row.original.code)?.unit_price ?? "new"}
          current={ruleFor(row.original.code)?.unit_price ?? null}
          onSave={(v) => setPrice(row.original.code, v)}
        />
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <DataTable columns={cols} data={groups ?? []} loading={isLoading} empty="Chưa có loại xe" />
      <p className="text-[13px] text-muted">Danh mục loại xe cố định. Chỉ điều chỉnh được đơn giá.</p>
    </div>
  );
}

function PriceCell({ current, onSave }: { current: number | null; onSave: (value: number) => Promise<void> }) {
  const [value, setValue] = useState<string>(current != null ? String(current) : "");
  const [busy, setBusy] = useState(false);
  const n = Number(value);
  const dirty = value.trim() !== "" && n !== current;
  const save = async () => {
    if (!Number.isFinite(n) || n < 0) {
      toast.error("Giá không hợp lệ");
      return;
    }
    setBusy(true);
    try {
      await onSave(n);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex items-center gap-1.5">
      <div className="relative">
        <Input
          type="number"
          min={0}
          step={1000}
          inputMode="numeric"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && dirty && !busy) save();
          }}
          className="h-9 w-[130px] pr-7 tnum"
          aria-label="Đơn giá (đồng)"
        />
        <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[13px] text-muted">đ</span>
      </div>
      <Button variant="outline" size="sm" className="h-9" disabled={!dirty || busy} onClick={save}>
        {busy ? "Đang lưu" : "Lưu"}
      </Button>
    </div>
  );
}
