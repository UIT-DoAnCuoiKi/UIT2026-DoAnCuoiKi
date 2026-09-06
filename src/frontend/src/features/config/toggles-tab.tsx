import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useGetToggles, useUpdateToggles, getGetTogglesQueryKey } from "@/api/generated/config/config";
import type { ToggleOut } from "@/api/generated/model";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { SurfaceCard } from "@/components/surface-card";

type ToggleKey = "read_plate" | "plate_color" | "vehicle_class" | "dev_mode";
const DEFAULTS: ToggleOut = { read_plate: true, plate_color: true, vehicle_class: true, dev_mode: false };

export function TogglesTab() {
  const qc = useQueryClient();
  const { data } = useGetToggles();
  const update = useUpdateToggles();
  const t = data ?? DEFAULTS;

  // Cập nhật lạc quan: lật Switch ngay, ghi đè bằng phản hồi thật, rollback nếu lỗi.
  // Trước đây thiếu bước này nên UI không đổi sau khi lưu.
  const set = async (key: ToggleKey, value: boolean) => {
    const key0 = getGetTogglesQueryKey();
    const prev = qc.getQueryData<ToggleOut>(key0) ?? t;
    qc.setQueryData<ToggleOut>(key0, { ...prev, [key]: value });
    try {
      const next = await update.mutateAsync({ data: { [key]: value } });
      qc.setQueryData<ToggleOut>(key0, next);
      toast.success("Đã cập nhật cấu hình");
    } catch {
      qc.setQueryData<ToggleOut>(key0, prev);
      toast.error("Cập nhật thất bại");
    }
  };

  const Row = ({
    id,
    label,
    checked,
    hint,
  }: {
    id: ToggleKey;
    label: string;
    checked: boolean;
    hint?: string;
  }) => (
    <div className="flex items-center justify-between py-3">
      <div>
        <Label htmlFor={id}>{label}</Label>
        {hint && <p className="text-[13px] text-muted">{hint}</p>}
      </div>
      <Switch id={id} checked={checked} disabled={update.isPending} onCheckedChange={(v) => set(id, v)} />
    </div>
  );

  return (
    <SurfaceCard variant="white" className="divide-y divide-line">
      <Row id="read_plate" label="Đọc biển số (read_plate)" checked={t.read_plate} hint="Tắt thì màn cổng ép nhập tay" />
      <Row id="plate_color" label="Nhận màu biển (plate_color)" checked={t.plate_color} />
      <Row id="vehicle_class" label="Phân loại xe (vehicle_class)" checked={t.vehicle_class} />
      <Row
        id="dev_mode"
        label="Chế độ dev (dev_mode)"
        checked={t.dev_mode}
        hint="Bật thì màn Trạm cổng hiện thêm nút Tải ảnh thay camera thật — chỉ dùng khi test, tắt khi vận hành thật để không ai thay ảnh gốc bằng ảnh tuỳ ý."
      />
    </SurfaceCard>
  );
}
