import { toast } from "sonner";
import { useGetToggles, useUpdateToggles } from "@/api/generated/config/config";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { SurfaceCard } from "@/components/surface-card";

type ToggleKey = "read_plate" | "plate_color" | "vehicle_class";

export function TogglesTab() {
  const { data } = useGetToggles();
  const update = useUpdateToggles();
  const set = async (key: ToggleKey, value: boolean) => {
    await update.mutateAsync({ data: { [key]: value } });
    toast.success("Đã cập nhật cấu hình");
  };
  const t = data ?? { read_plate: true, plate_color: true, vehicle_class: true };

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
      <Switch id={id} checked={checked} onCheckedChange={(v) => set(id, v)} />
    </div>
  );

  return (
    <SurfaceCard variant="white" className="divide-y divide-line">
      <Row id="read_plate" label="Đọc biển số (read_plate)" checked={t.read_plate} hint="Tắt thì màn cổng ép nhập tay" />
      <Row id="plate_color" label="Nhận màu biển (plate_color)" checked={t.plate_color} />
      <Row id="vehicle_class" label="Phân loại xe (vehicle_class)" checked={t.vehicle_class} />
    </SurfaceCard>
  );
}
