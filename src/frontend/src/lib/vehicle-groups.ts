import { useListVehicleGroups } from "@/api/generated/vehicle-groups/vehicle-groups";

// Ánh xạ loại xe (đầu ra detector) sang nhóm phí. Map nhiều-một nhưng xác định:
// một loại xe luôn về đúng một nhóm phí. Phải khớp backend
// app/services/vehicle_groups.py:_MAP.
const TYPE_TO_GROUP: Record<string, string> = {
  motorbike: "xe_may",
  bicycle: "xe_may",
  car: "o_to_con",
  truck: "xe_tai",
  bus: "xe_khach",
};

export function groupForVehicleType(vType?: string | null): string | undefined {
  if (!vType) return undefined;
  return TYPE_TO_GROUP[vType.toLowerCase()];
}

export function useVehicleGroupMap(): Record<string, string> {
  const { data } = useListVehicleGroups();
  const map: Record<string, string> = {};
  for (const g of data ?? []) map[g.code] = g.display_name;
  return map;
}

export function groupLabel(map: Record<string, string>, code?: string | null): string {
  if (!code) return "—";
  return map[code] ?? code;
}
