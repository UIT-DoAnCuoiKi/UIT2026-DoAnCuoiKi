import { groupLabel } from "./vehicle-groups";

test("groupLabel returns display_name when present", () => {
  const map = { xe_may: "Xe máy", o_to_con: "Ô tô con" };
  expect(groupLabel(map, "xe_may")).toBe("Xe máy");
});

test("groupLabel falls back to code when unknown", () => {
  expect(groupLabel({}, "xe_la")).toBe("xe_la");
});

test("groupLabel returns dash for empty", () => {
  expect(groupLabel({}, null)).toBe("—");
});
