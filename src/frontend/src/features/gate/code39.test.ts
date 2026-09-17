import { expect, test } from "vitest";
import { code39Bars } from "./code39";

test("moi ky tu gom 5 vach den, co ky tu bao dau va cuoi", () => {
  const { bars } = code39Bars("A1");
  expect(bars).toHaveLength(5 * 4);  // * A 1 *
});

test("bo qua ky tu ngoai bang ma", () => {
  expect(code39Bars("A#").bars).toHaveLength(5 * 3);
});

test("vach rong gap hon vach hep", () => {
  const { bars, width } = code39Bars("0", 2, 5);
  expect(Math.max(...bars.map((b) => b.width))).toBe(5);
  expect(width).toBeGreaterThan(0);
});
