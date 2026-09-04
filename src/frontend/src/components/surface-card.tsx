import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function SurfaceCard({
  variant = "surface",
  className,
  children,
}: {
  variant?: "surface" | "white";
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] p-5",
        variant === "surface" ? "bg-surface" : "border border-line bg-bg",
        className,
      )}
    >
      {children}
    </div>
  );
}
