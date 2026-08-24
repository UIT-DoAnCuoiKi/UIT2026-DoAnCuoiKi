import { reviewStateMeta, sessionStatusMeta } from "@/lib/status";

function meta(kind: "review" | "session", value: string) {
  return kind === "review" ? reviewStateMeta(value) : sessionStatusMeta(value);
}

export function StatusDot({ kind, value }: { kind: "review" | "session"; value: string }) {
  const { token } = meta(kind, value);
  return (
    <span
      className="inline-block h-2 w-2 rounded-full"
      style={{ backgroundColor: `var(--${token})` }}
      aria-hidden
    />
  );
}

export function StatusChip({ kind, value }: { kind: "review" | "session"; value: string }) {
  const { token, Icon, label } = meta(kind, value);
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[13px]"
      style={{
        color: `var(--${token})`,
        backgroundColor: `color-mix(in srgb, var(--${token}) 12%, transparent)`,
      }}
    >
      <Icon size={14} aria-hidden />
      <span>{label}</span>
    </span>
  );
}
