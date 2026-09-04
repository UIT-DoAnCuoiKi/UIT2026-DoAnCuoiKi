import { useEffect } from "react";

export type ShortcutAction =
  | "focus-in"
  | "focus-out"
  | "capture"
  | "confirm"
  | "edit-plate"
  | "manual"
  | "reset"
  | "cancel"
  | "toggle-help"
  | "method-1"
  | "method-2"
  | "method-3"
  | "dialog-confirm"
  | "dialog-close"
  | null;

export function resolveShortcut(key: string, dialogOpen: boolean): ShortcutAction {
  if (dialogOpen) {
    switch (key) {
      case "1":
        return "method-1";
      case "2":
        return "method-2";
      case "3":
        return "method-3";
      case "Enter":
        return "dialog-confirm";
      case "Escape":
        return "dialog-close";
      default:
        return null;
    }
  }
  switch (key) {
    case "1":
      return "focus-in";
    case "2":
      return "focus-out";
    case " ":
      return "capture";
    case "Enter":
      return "confirm";
    case "e":
    case "E":
      return "edit-plate";
    case "m":
    case "M":
      return "manual";
    case "r":
    case "R":
      return "reset";
    case "Escape":
      return "cancel";
    case "?":
      return "toggle-help";
    default:
      return null;
  }
}

export function useGateShortcuts(opts: {
  dialogOpen: boolean;
  onAction: (action: Exclude<ShortcutAction, null>) => void;
}) {
  const { dialogOpen, onAction } = opts;
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      // Trong ô nhập chỉ cho Escape thoát; các phím khác để người dùng gõ biển
      if (typing && e.key !== "Escape") return;
      const action = resolveShortcut(e.key, dialogOpen);
      if (action) {
        e.preventDefault();
        onAction(action);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [dialogOpen, onAction]);
}
