export type PlateColorInfo = { label: string; swatch: string };

const MAP: Record<string, PlateColorInfo> = {
  white: { label: "Trắng", swatch: "#ffffff" },
  yellow: { label: "Vàng", swatch: "#f4c400" },
  blue: { label: "Xanh", swatch: "#2e6fd6" },
  red: { label: "Đỏ", swatch: "#d24a3e" },
};

// Danh sách chọn màu biển cho thao tác sửa tay ở trạm cổng.
export const PLATE_COLOR_OPTIONS = Object.entries(MAP).map(([code, info]) => ({ code, ...info }));

export function plateColor(value?: string | null): PlateColorInfo | null {
  if (!value) return null;
  return MAP[value.toLowerCase()] ?? { label: value, swatch: "transparent" };
}
