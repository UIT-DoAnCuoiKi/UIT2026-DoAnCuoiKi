import { useListVehicleGroups } from "@/api/generated/vehicle-groups/vehicle-groups";

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
