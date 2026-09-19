import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { cn } from "@/lib/cn";

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <div className="flex h-full">
      <aside
        className={cn(
          "hidden shrink-0 border-r border-line md:block",
          collapsed ? "w-16" : "w-[212px]",
        )}
      >
        <Sidebar collapsed={collapsed} />
      </aside>

      {/* Thanh bên chính ẩn dưới md nên mobile cần drawer riêng. */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-[248px] max-w-[80vw] border-r border-line bg-bg shadow-lg">
            <Sidebar collapsed={false} onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onToggleSidebar={() => setCollapsed((c) => !c)} onOpenMobileMenu={() => setMobileOpen(true)} />
        <main className="min-h-0 flex-1 overflow-auto p-3 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
