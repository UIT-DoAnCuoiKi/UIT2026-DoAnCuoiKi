import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { VehicleGroupsTab } from "./vehicle-groups-tab";
import { UsersTab } from "./users-tab";
import { LanesTab } from "./lanes-tab";
import { TogglesTab } from "./toggles-tab";
import { SurfaceCard } from "@/components/surface-card";
import { getRole } from "@/lib/auth";

export function ConfigPage() {
  const role = getRole();
  const canManageUsers = role === "root" || role === "manager";
  return (
    <div className="space-y-4">
      <Tabs defaultValue="price">
        <TabsList>
          <TabsTrigger value="price">Loại xe</TabsTrigger>
          {canManageUsers && <TabsTrigger value="users">Tài khoản</TabsTrigger>}
          <TabsTrigger value="lanes">Lane</TabsTrigger>
          <TabsTrigger value="toggles">Feature toggle</TabsTrigger>
        </TabsList>
        <TabsContent value="price">
          <SurfaceCard variant="white">
            <VehicleGroupsTab />
          </SurfaceCard>
        </TabsContent>
        {canManageUsers && (
          <TabsContent value="users">
            <SurfaceCard variant="white">
              <UsersTab />
            </SurfaceCard>
          </TabsContent>
        )}
        <TabsContent value="lanes">
          <SurfaceCard variant="white">
            <LanesTab />
          </SurfaceCard>
        </TabsContent>
        <TabsContent value="toggles">
          <TogglesTab />
        </TabsContent>
      </Tabs>
      <p className="text-[13px] text-muted">
        Dữ liệu phiên tự xóa sau 30 ngày kể từ khi xe ra (tuân thủ Luật Bảo vệ dữ liệu cá nhân).
      </p>
    </div>
  );
}
