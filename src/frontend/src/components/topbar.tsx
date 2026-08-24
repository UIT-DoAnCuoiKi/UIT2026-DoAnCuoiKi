import { useNavigate } from "react-router-dom";
import { PanelLeft, Sun, Moon, LogOut, Search } from "lucide-react";
import { useTheme } from "@/theme/theme-provider";
import { clearToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Topbar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const { theme, toggle } = useTheme();
  const nav = useNavigate();
  return (
    <header className="flex h-14 items-center gap-3 border-b border-line px-6">
      <Button variant="ghost" size="icon" aria-label="Gập thanh bên" onClick={onToggleSidebar}>
        <PanelLeft size={18} />
      </Button>
      <div className="relative hidden md:block">
        <Search size={16} className="absolute left-2 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
        <Input className="h-9 w-64 pl-8" placeholder="Tìm kiếm" aria-label="Tìm kiếm" />
      </div>
      <div className="ml-auto flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          aria-label={theme === "dark" ? "Chế độ sáng" : "Chế độ tối"}
          onClick={toggle}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Đăng xuất"
          onClick={() => {
            clearToken();
            nav("/login");
          }}
        >
          <LogOut size={18} />
        </Button>
      </div>
    </header>
  );
}
