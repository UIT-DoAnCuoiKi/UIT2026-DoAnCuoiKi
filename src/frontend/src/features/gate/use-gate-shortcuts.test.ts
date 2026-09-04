import { resolveShortcut } from "./use-gate-shortcuts";

test("maps panel keys when no dialog", () => {
  expect(resolveShortcut("1", false)).toBe("focus-in");
  expect(resolveShortcut("2", false)).toBe("focus-out");
  expect(resolveShortcut(" ", false)).toBe("capture");
  expect(resolveShortcut("Enter", false)).toBe("confirm");
  expect(resolveShortcut("e", false)).toBe("edit-plate");
  expect(resolveShortcut("M", false)).toBe("manual");
  expect(resolveShortcut("Escape", false)).toBe("cancel");
  expect(resolveShortcut("?", false)).toBe("toggle-help");
  expect(resolveShortcut("z", false)).toBeNull();
});

test("maps payment method keys when dialog open", () => {
  expect(resolveShortcut("1", true)).toBe("method-1");
  expect(resolveShortcut("3", true)).toBe("method-3");
  expect(resolveShortcut("Enter", true)).toBe("dialog-confirm");
  expect(resolveShortcut("Escape", true)).toBe("dialog-close");
});
