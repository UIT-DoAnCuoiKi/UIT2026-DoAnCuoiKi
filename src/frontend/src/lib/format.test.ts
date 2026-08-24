import { formatVnd, formatDuration, formatDateTime, formatPlate } from "./format";

test("formatVnd renders vi-VN dong (NBSP before symbol)", () => {
  expect(formatVnd(15000)).toBe("15.000 ₫");
  expect(formatVnd(null)).toBe("—");
});

test("formatDuration renders h m from ISO range", () => {
  expect(formatDuration("2026-08-23T08:00:00Z", "2026-08-23T09:30:00Z")).toBe("1 giờ 30 phút");
  expect(formatDuration("2026-08-23T08:00:00Z", "2026-08-23T08:45:00Z")).toBe("45 phút");
  expect(formatDuration("2026-08-23T08:00:00Z", null)).toBe("—");
});

test("formatDateTime formats vi-VN", () => {
  expect(formatDateTime(null)).toBe("—");
  expect(typeof formatDateTime("2026-08-23T09:30:00Z")).toBe("string");
  expect(formatDateTime("not-a-date")).toBe("—");
});

test("formatPlate uppercases and trims", () => {
  expect(formatPlate(" 51f-12345 ")).toBe("51F-12345");
  expect(formatPlate(null)).toBe("—");
});
