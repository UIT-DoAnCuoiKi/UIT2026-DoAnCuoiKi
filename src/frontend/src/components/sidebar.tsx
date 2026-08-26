import { NavLink } from "react-router-dom";
import { LayoutGrid, ListChecks, BarChart3, Settings, type LucideIcon } from "lucide-react";
import { getRole, type Role } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { Brand, LogoMark } from "@/components/brand";

type Item = { to: string; label: string; Icon: LucideIcon; roles: Role[] };
const ITEMS: Item[] = [
  { to: "/gate", label: "Trạm cổng", Icon: LayoutGrid, roles: ["staff", "manager", "root"] },
  { to: "/sessions", label: "Quản lý phiên", Icon: ListChecks, roles: ["staff", "manager", "root"] },
  { to: "/stats", label: "Thống kê", Icon: BarChart3, roles: ["manager", "root"] },
  { to: "/config", label: "Cấu hình", Icon: Settings, roles: ["manager", "root"] },
];

export function Sidebar({ collapsed }: { collapsed: boolean }) {
  const role = getRole();
  const items = ITEMS.filter((i) => role && i.roles.includes(role));
  return (
    <nav className="flex h-full flex-col gap-1 p-3" aria-label="Điều hướng chính">
      <div className="mb-4 px-2">
        {collapsed ? <LogoMark size={28} /> : <Brand size="sm" />}
      </div>
      {items.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "relative flex items-center gap-3 rounded-[var(--radius-control)] px-3 py-2 text-sm text-ink hover:bg-surface",
              isActive &&
                "bg-surface font-medium before:absolute before:left-0 before:top-1/2 before:h-4 before:w-0.5 before:-translate-y-1/2 before:bg-ink before:content-['']",
            )
          }
        >
          <Icon size={18} aria-hidden />
          {!collapsed && <span>{label}</span>}
        </NavLink>
      ))}
    </nav>
  );
}
