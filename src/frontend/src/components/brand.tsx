import { cn } from "@/lib/cn";

/** SmartPark parking "P" mark on a periwinkle tile. */
export function LogoMark({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role="img"
      aria-label="SmartPark"
      className={cn("shrink-0", className)}
    >
      <defs>
        <linearGradient id="brandGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#95a4fc" />
          <stop offset="1" stopColor="#c6c7f8" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="48" height="48" rx="14" fill="url(#brandGrad)" />
      <path
        transform="translate(13 9)"
        fillRule="evenodd"
        fill="#1c1c1c"
        d="M0 0 H9 A6 6 0 0 1 9 12 H4.5 V20 H0 Z M4.5 4 H8 A2 2 0 0 1 8 8 H4.5 Z"
      />
    </svg>
  );
}

type BrandProps = {
  size?: "lg" | "sm";
  invert?: boolean;
  showTagline?: boolean;
  className?: string;
};

const NAME = "SmartPark";
const TAGLINE = "Hệ thống quản lý bãi đỗ xe thông minh";

export function Brand({ size = "sm", invert = false, showTagline = false, className }: BrandProps) {
  const lg = size === "lg";
  return (
    <div className={cn("flex items-center", lg ? "gap-4" : "gap-3", className)}>
      <LogoMark size={lg ? 72 : 28} />
      <div className="leading-tight">
        <div
          className={cn(
            "font-semibold tracking-tight",
            lg ? "text-4xl" : "text-sm",
            invert ? "text-white" : "text-ink",
          )}
        >
          {NAME}
        </div>
        {showTagline && (
          <div
            className={cn(
              lg ? "mt-1.5 text-lg" : "mt-1 text-sm",
              invert ? "text-white/60" : "text-muted",
            )}
          >
            {TAGLINE}
          </div>
        )}
      </div>
    </div>
  );
}
