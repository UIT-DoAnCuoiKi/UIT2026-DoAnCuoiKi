import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PriceRulesTab } from "./price-rules-tab";
import { UsersTab } from "./users-tab";
import { LanesTab } from "./lanes-tab";
import { TogglesTab } from "./toggles-tab";
import { SurfaceCard } from "@/components/surface-card";

export function ConfigPage() {
  return (
    <div className="space-y-4">
      <Tabs defaultValue="price">
        <TabsList>
          <TabsTrigger value="price">Bảng giá</TabsTrigger>
          <TabsTrigger value="users">Tài khoản</TabsTrigger>
          <TabsTrigger value="lanes">Lane</TabsTrigger>
          <TabsTrigger value="toggles">Feature toggle</TabsTrigger>
        </TabsList>
        <TabsContent value="price">
          <SurfaceCard variant="white">
            <PriceRulesTab />
          </SurfaceCard>
        </TabsContent>
        <TabsContent value="users">
          <SurfaceCard variant="white">
            <UsersTab />
          </SurfaceCard>
        </TabsContent>
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
