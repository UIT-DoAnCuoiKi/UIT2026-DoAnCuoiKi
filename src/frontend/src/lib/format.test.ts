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

test("chuoi khong co mui gio duoc hieu la UTC", () => {
  // 13:26 UTC = 20:26 giờ Việt Nam; trước đây hiển thị thành 13:26.
  const co_z = formatDateTime("2026-09-17T13:26:00Z");
  const khong_z = formatDateTime("2026-09-17T13:26:00");
  expect(khong_z).toBe(co_z);
});

test("thoi luong tinh dung khi mot dau co Z mot dau khong", () => {
  expect(formatDuration("2026-09-17T13:00:00", "2026-09-17T14:30:00Z")).toBe("1 giờ 30 phút");
});
