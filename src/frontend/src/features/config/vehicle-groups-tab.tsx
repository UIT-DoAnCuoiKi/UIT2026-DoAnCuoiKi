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
import type { PriceRuleOut, VehicleGroupOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatVnd } from "@/lib/format";
import { priceModeLabel, PRICE_MODE_OPTIONS } from "@/lib/labels";

// Danh mục loại xe cố định (seed backend): màn này chỉ chỉnh giá, không thêm/xóa nhóm.
export function VehicleGroupsTab() {
  const qc = useQueryClient();
  const { data: groups, isLoading } = useListVehicleGroups();
  const { data: rules } = useListPriceRules();
  const createRule = useCreatePriceRule();
  const updateRule = useUpdatePriceRule();

  const ruleFor = (code: string) => (rules ?? []).find((r) => r.vehicle_group === code && r.active);

  const savePrice = async (
    code: string,
    existing: PriceRuleOut | undefined,
    next: { mode: string; unitPrice: number; blockMinutes: number | null },
  ) => {
    if (existing) {
      await updateRule.mutateAsync({
        ruleId: existing.id,
        data: { mode: next.mode, unit_price: next.unitPrice, block_minutes: next.blockMinutes },
      });
    } else {
      await createRule.mutateAsync({
        data: { vehicle_group: code, mode: next.mode, unit_price: next.unitPrice, block_minutes: next.blockMinutes },
      });
    }
    await qc.invalidateQueries({ queryKey: getListPriceRulesQueryKey() });
    toast.success("Đã cập nhật giá");
  };

  const cols: ColumnDef<VehicleGroupOut, unknown>[] = [
    { header: "Loại xe", accessorKey: "display_name" },
    {
      header: "Hiện tại",
      cell: ({ row }) => {
        const rule = ruleFor(row.original.code);
        if (!rule) return <span className="text-muted">chưa đặt</span>;
        return (
          <span className="tnum">
            {formatVnd(rule.unit_price)}{" "}
            <span className="text-muted">
              {rule.mode === "block" ? `/ ${rule.block_minutes ?? "?"} phút` : "/ lượt"}
            </span>
          </span>
        );
      },
    },
    {
      header: "Đặt giá",
      cell: ({ row }) => (
        <PriceForm
          key={row.original.code + (ruleFor(row.original.code)?.unit_price ?? "new")}
          rule={ruleFor(row.original.code)}
          onSave={(next) => savePrice(row.original.code, ruleFor(row.original.code), next)}
        />
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <DataTable columns={cols} data={groups ?? []} loading={isLoading} empty="Chưa có loại xe" />
      <p className="text-[13px] text-muted">Danh mục loại xe cố định. Chỉ điều chỉnh được giá.</p>
    </div>
  );
}

function PriceForm({
  rule,
  onSave,
}: {
  rule: PriceRuleOut | undefined;
  onSave: (next: { mode: string; unitPrice: number; blockMinutes: number | null }) => Promise<void>;
}) {
  const [mode, setMode] = useState(rule?.mode ?? "flat");
  const [unitPrice, setUnitPrice] = useState(rule ? String(rule.unit_price) : "");
  const [blockMinutes, setBlockMinutes] = useState(rule?.block_minutes ? String(rule.block_minutes) : "");
  const [busy, setBusy] = useState(false);

  const price = Number(unitPrice);
  const minutes = Number(blockMinutes);
  const needsBlockMinutes = mode === "block";
  const validPrice = unitPrice.trim() !== "" && Number.isFinite(price) && price >= 0;
  const validMinutes = !needsBlockMinutes || (blockMinutes.trim() !== "" && Number.isFinite(minutes) && minutes > 0);
  const dirty =
    mode !== (rule?.mode ?? "flat") ||
    price !== (rule?.unit_price ?? NaN) ||
    (needsBlockMinutes ? minutes : null) !== (rule?.block_minutes ?? null);

  const save = async () => {
    if (!validPrice) {
      toast.error("Giá không hợp lệ");
      return;
    }
    if (!validMinutes) {
      toast.error("Cần nhập số phút mỗi khối");
      return;
    }
    setBusy(true);
    try {
      await onSave({ mode, unitPrice: price, blockMinutes: needsBlockMinutes ? minutes : null });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <select
        aria-label="Chế độ tính giá"
        className="h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
        value={mode}
        onChange={(e) => setMode(e.target.value)}
      >
        {PRICE_MODE_OPTIONS.map((o) => (
          <option key={o.code} value={o.code}>
            {priceModeLabel(o.code)}
          </option>
        ))}
      </select>
      <div className="relative">
        <Input
          type="number"
          min={0}
          step={1000}
          inputMode="numeric"
          value={unitPrice}
          onChange={(e) => setUnitPrice(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && dirty && !busy) save();
          }}
          className="h-9 w-[120px] pr-7 tnum"
          aria-label="Đơn giá (đồng)"
        />
        <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[13px] text-muted">đ</span>
      </div>
      {needsBlockMinutes && (
        <div className="relative">
          <Input
            type="number"
            min={1}
            step={1}
            inputMode="numeric"
            value={blockMinutes}
            onChange={(e) => setBlockMinutes(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && dirty && !busy) save();
            }}
            className="h-9 w-[104px] pr-10 tnum"
            aria-label="Số phút mỗi khối"
          />
          <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[13px] text-muted">
            phút
          </span>
        </div>
      )}
      <Button variant="outline" size="sm" className="h-9" disabled={!dirty || busy} onClick={save}>
        {busy ? "Đang lưu" : "Lưu"}
      </Button>
    </div>
  );
}
