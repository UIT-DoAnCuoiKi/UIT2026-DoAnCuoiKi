import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { cn } from "@/lib/cn";

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
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
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onToggleSidebar={() => setCollapsed((c) => !c)} />
        <main className="min-h-0 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
