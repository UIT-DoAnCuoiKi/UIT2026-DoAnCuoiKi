import { plateColor } from "./plate-color";

test("maps known color code to Vietnamese label and swatch", () => {
  expect(plateColor("white")).toEqual({ label: "Trắng", swatch: "#ffffff" });
  expect(plateColor("YELLOW")).toEqual({ label: "Vàng", swatch: "#f4c400" });
});

test("returns null for empty", () => {
  expect(plateColor(null)).toBeNull();
  expect(plateColor("")).toBeNull();
});

test("unknown code falls back to raw label with transparent swatch", () => {
  expect(plateColor("teal")).toEqual({ label: "teal", swatch: "transparent" });
});
