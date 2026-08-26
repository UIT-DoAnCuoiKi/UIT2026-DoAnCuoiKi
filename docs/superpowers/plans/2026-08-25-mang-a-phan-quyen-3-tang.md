# Mảng A: Phân quyền 3 tầng (root / manager / staff) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển hệ thống từ 2 vai `staff`/`admin` sang 3 vai `root`/`manager`/`staff`, siết thống kê khỏi staff, đưa CRUD nhân viên về root, và bỏ thống kê khỏi màn Trạm cổng.

**Architecture:** Backend đổi các `require_role("admin")` theo ma trận quyền mới và rename vai top thành `root`; JWT và schema không đổi (vai là `String(16)`). Frontend mở rộng kiểu `Role`, cập nhật guard router và sidebar theo vai, bỏ `GateKpis` khỏi màn cổng, và ẩn tab Tài khoản khỏi manager.

**Tech Stack:** FastAPI, SQLAlchemy, pytest (backend, sqlite in memory); React 18, React Router v6, Vitest, React Testing Library (frontend).

## Global Constraints

- Ba vai hợp lệ: `root`, `manager`, `staff`. Vai `admin` bị loại bỏ hoàn toàn (rename thành `root`).
- Quy tắc quyền: `root` = CRUD nhân viên + đồng bộ; `manager` + `root` = cấu hình (ghi) + thống kê; `staff` + `manager` + `root` = thao tác vận hành (sessions, captures/infer, readings, images, payments, shifts, incidents, occupancy, overstay) + đọc cấu hình.
- JWT đã mang claim `role`; không đổi cơ chế token. Model `User.role` là `String(16)`; không đổi schema.
- `deps.require_role(*roles)` đã variadic; không sửa file `deps.py`.
- Backend test chạy tại thư mục `src/backend`: `python -m pytest`. Frontend test chạy tại `src/frontend`: `npx vitest run`.
- Văn bản tiếng Việt không dùng ký tự gạch ngang làm dấu câu; đường dẫn và định danh trong code giữ nguyên.

---

## File Structure

Backend:
- `app/routers/users.py` sửa `_ROLES` và guard CRUD nhân viên thành `root`.
- `app/routers/stats.py`, `config.py`, `registry.py`, `devices.py`, `spaces.py` sửa guard sang `manager` + `root`.
- `app/routers/sync.py` sửa guard sang `root`.
- `scripts/seed_admin.py` seed vai `root`.
- `scripts/migrate_admin_to_root.py` mới, đổi dữ liệu vai `admin` sang `root`.
- `tests/test_rbac_roles.py` mới, kiểm ranh giới quyền mới.
- Cập nhật các test hard code vai `admin`.

Frontend:
- `src/lib/auth.ts` mở rộng kiểu `Role`.
- `src/app/router.tsx` guard route theo vai.
- `src/components/sidebar.tsx` lọc nav theo vai.
- `src/features/gate/gate-page.tsx` bỏ `GateKpis`.
- `src/features/config/config-page.tsx` ẩn tab Tài khoản khỏi manager.
- Cập nhật `src/components/sidebar.test.tsx`, `src/app/role-guard.test.tsx`; thêm `gate-page.test.tsx`, `config-page.test.tsx`.

---

### Task 1: Backend, ma trận quyền 3 vai + seed + migration

**Files:**
- Modify: `src/backend/app/routers/users.py:13-14`
- Modify: `src/backend/app/routers/stats.py:5-24,32`
- Modify: `src/backend/app/routers/config.py:13`
- Modify: `src/backend/app/routers/registry.py:15`
- Modify: `src/backend/app/routers/devices.py:14`
- Modify: `src/backend/app/routers/spaces.py:14`
- Modify: `src/backend/app/routers/sync.py:43`
- Modify: `src/backend/scripts/seed_admin.py`
- Create: `src/backend/scripts/migrate_admin_to_root.py`
- Create: `src/backend/tests/test_rbac_roles.py`
- Modify: `src/backend/tests/conftest.py:82`, `tests/test_config.py:7,28,35`, `tests/test_stats.py:29`, `tests/test_rbac_users.py:17`, `tests/test_auth_login.py:7,12`, `tests/test_phase2_acceptance.py:7`, `tests/test_seed_admin.py:14`

**Interfaces:**
- Produces: vai hợp lệ `"root"`, `"manager"`, `"staff"`; hàm `migrate_admin_to_root(db: Session) -> int` trả số bản ghi đã đổi.
- Consumes: fixture `client`, `make_user`, `db_session` từ `tests/conftest.py`; `require_role(*roles)` từ `app/deps.py`.

- [ ] **Step 1: Viết test ranh giới quyền mới (failing)**

Tạo `src/backend/tests/test_rbac_roles.py`:

```python
from sqlalchemy import select

from app.models import User
from scripts.migrate_admin_to_root import migrate_admin_to_root


def _token(client, make_user, username, role):
    make_user(username=username, password="pw", role=role)
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["access_token"]


def test_staff_cannot_get_stats(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'gate', 'staff')}"}
    assert client.get("/stats", headers=h).status_code == 403


def test_manager_can_get_stats(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'mgr', 'manager')}"}
    assert client.get("/stats", headers=h).status_code == 200


def test_manager_cannot_crud_users(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'mgr', 'manager')}"}
    assert client.get("/users", headers=h).status_code == 403


def test_root_can_crud_users(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'boss', 'root')}"}
    r = client.post("/users", json={"username": "s1", "password": "pw", "role": "staff"}, headers=h)
    assert r.status_code == 201


def test_manager_can_configure(client, make_user):
    h = {"Authorization": f"Bearer {_token(client, make_user, 'mgr', 'manager')}"}
    r = client.post("/price-rules", json={"vehicle_group": "xe_may", "mode": "flat", "unit_price": 3000}, headers=h)
    assert r.status_code == 201


def test_migrate_admin_to_root(db_session, make_user):
    make_user(username="old", password="pw", role="admin")
    n = migrate_admin_to_root(db_session)
    assert n == 1
    assert db_session.scalars(select(User).where(User.username == "old")).one().role == "root"
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd src/backend && python -m pytest tests/test_rbac_roles.py -v`
Expected: `test_staff_cannot_get_stats`, `test_root_can_crud_users`, `test_manager_can_configure` FAIL (403 vs 200 hoặc ngược lại); `test_migrate_admin_to_root` FAIL với `ModuleNotFoundError: scripts.migrate_admin_to_root`.

- [ ] **Step 3: Sửa guard các router**

`app/routers/users.py`, đổi hai dòng 13 và 14:

```python
admin_only = require_role("root")
_ROLES = ("staff", "manager", "root")
```

`app/routers/stats.py`, đổi import dòng 5 (bỏ `get_current_user` không còn dùng) và hai dependency:

```python
from app.deps import require_role
```

Trong `get_stats`, đổi tham số dependency:

```python
    user: User = Depends(require_role("manager", "root")),
```

Trong `export_stats`, đổi:

```python
    admin: User = Depends(require_role("manager", "root")),
```

`app/routers/config.py:13`:

```python
admin_only = require_role("manager", "root")
```

`app/routers/registry.py:15`:

```python
admin_only = require_role("manager", "root")
```

`app/routers/devices.py:14`:

```python
admin_only = require_role("manager", "root")
```

`app/routers/spaces.py:14`:

```python
admin_only = require_role("manager", "root")
```

`app/routers/sync.py:43`:

```python
central_admin = require_role("root")
```

- [ ] **Step 4: Sửa seed và thêm migration script**

`scripts/seed_admin.py`, đổi vai được seed (trong lời gọi `User(...)`):

```python
        role="root",
```

Tạo `scripts/migrate_admin_to_root.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User


def migrate_admin_to_root(db: Session) -> int:
    users = list(db.scalars(select(User).where(User.role == "admin")).all())
    for u in users:
        u.role = "root"
    db.commit()
    return len(users)


def main() -> None:
    db = SessionLocal()
    try:
        n = migrate_admin_to_root(db)
        print(f"đã đổi {n} tài khoản admin sang root")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Cập nhật test hard code vai admin**

`tests/conftest.py:82` (fixture `admin_headers`, dùng bởi 14 file, đổi một dòng là đủ):

```python
    make_user(username="boss", password="pw", role="root")
```

`tests/test_config.py`, đổi ba lời gọi `_token(client, make_user, 'admin')` (dòng 7, 28, 35) thành `'root'`:

```python
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
```
```python
    admin_h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
```
```python
    h = {"Authorization": f"Bearer {_token(client, make_user, 'root')}"}
```

`tests/test_stats.py:29`:

```python
    make_user(username="adm", password="pw", role="root")
```

`tests/test_rbac_users.py:17`:

```python
    make_user(username="admin1", password="pw", role="root")
```

`tests/test_auth_login.py`, dòng 7 và 12:

```python
    make_user(username="admin1", password="pw", role="root")
```
```python
    assert body["role"] == "root"
```

`tests/test_phase2_acceptance.py:7`:

```python
    make_user(username="root", password="rootpw", role="root")
```

`tests/test_seed_admin.py:14`:

```python
    assert admin.role == "root"
```

`tests/test_tokens.py` không đổi: chuỗi vai ở đó chỉ là payload để kiểm mã hóa và giải mã, không phụ thuộc tính hợp lệ của vai.

- [ ] **Step 6: Chạy toàn bộ test backend, xác nhận pass**

Run: `cd src/backend && python -m pytest -q`
Expected: PASS toàn bộ (gồm `tests/test_rbac_roles.py` và các file đã sửa).

- [ ] **Step 7: Commit**

```bash
cd src/backend
git add app/routers/users.py app/routers/stats.py app/routers/config.py app/routers/registry.py app/routers/devices.py app/routers/spaces.py app/routers/sync.py scripts/seed_admin.py scripts/migrate_admin_to_root.py tests/
git commit -m "feat(auth): 3-tier roles root/manager/staff, tighten stats and user CRUD"
```

---

### Task 2: Frontend, kiểu Role + guard route + sidebar theo vai

**Files:**
- Modify: `src/frontend/src/lib/auth.ts:4,29-32`
- Modify: `src/frontend/src/app/router.tsx:24-32`
- Modify: `src/frontend/src/components/sidebar.tsx:8-13`
- Modify: `src/frontend/src/components/sidebar.test.tsx`
- Modify: `src/frontend/src/app/role-guard.test.tsx`

**Interfaces:**
- Consumes: vai `"root"`, `"manager"`, `"staff"` từ Task 1 (giá trị claim trong JWT).
- Produces: `type Role = "root" | "manager" | "staff"`; `getRole(): Role | null`.

- [ ] **Step 1: Viết lại test sidebar và role-guard theo hành vi mới (failing)**

Thay toàn bộ `src/components/sidebar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { saveToken } from "@/lib/auth";

function jwt(role: string) {
  const b64 = (o: object) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${b64({})}.${b64({ role, exp: Math.floor(Date.now() / 1000) + 3600 })}.s`;
}

test("staff sees only Trạm cổng and Quản lý phiên", () => {
  saveToken(jwt("staff"));
  render(<MemoryRouter><Sidebar collapsed={false} /></MemoryRouter>);
  expect(screen.getByText("Trạm cổng")).toBeInTheDocument();
  expect(screen.getByText("Quản lý phiên")).toBeInTheDocument();
  expect(screen.queryByText("Thống kê")).toBeNull();
  expect(screen.queryByText("Cấu hình")).toBeNull();
});

test("manager sees Thống kê and Cấu hình", () => {
  saveToken(jwt("manager"));
  render(<MemoryRouter><Sidebar collapsed={false} /></MemoryRouter>);
  expect(screen.getByText("Thống kê")).toBeInTheDocument();
  expect(screen.getByText("Cấu hình")).toBeInTheDocument();
});

test("root sees Thống kê and Cấu hình", () => {
  saveToken(jwt("root"));
  render(<MemoryRouter><Sidebar collapsed={false} /></MemoryRouter>);
  expect(screen.getByText("Thống kê")).toBeInTheDocument();
  expect(screen.getByText("Cấu hình")).toBeInTheDocument();
});
```

Thay toàn bộ `src/app/role-guard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RequireRole } from "./role-guard";
import { saveToken, clearToken } from "@/lib/auth";

function jwt(role: string) {
  const b64 = (o: object) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${b64({})}.${b64({ role, exp: Math.floor(Date.now() / 1000) + 3600 })}.s`;
}

function tree(initial: string) {
  return (
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/login" element={<div>LOGIN</div>} />
        <Route path="/gate" element={<div>GATE</div>} />
        <Route
          path="/config"
          element={
            <RequireRole roles={["manager", "root"]}>
              <div>CONFIG</div>
            </RequireRole>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

test("no token redirects to login", () => {
  clearToken();
  render(tree("/config"));
  expect(screen.getByText("LOGIN")).toBeInTheDocument();
});

test("staff blocked from config route -> gate", () => {
  saveToken(jwt("staff"));
  render(tree("/config"));
  expect(screen.getByText("GATE")).toBeInTheDocument();
});

test("manager allowed", () => {
  saveToken(jwt("manager"));
  render(tree("/config"));
  expect(screen.getByText("CONFIG")).toBeInTheDocument();
});

test("root allowed", () => {
  saveToken(jwt("root"));
  render(tree("/config"));
  expect(screen.getByText("CONFIG")).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd src/frontend && npx vitest run src/components/sidebar.test.tsx src/app/role-guard.test.tsx`
Expected: FAIL. `getRole` hiện chỉ nhận `staff`/`admin`, nên vai `manager`/`root` trả `null` và các mục nav không hiện; guard chặn `manager`/`root`.

- [ ] **Step 3: Mở rộng kiểu Role trong `src/lib/auth.ts`**

Đổi dòng 4:

```ts
export type Role = "root" | "manager" | "staff";
```

Đổi hàm `getRole` (dòng 29 tới 32):

```ts
export function getRole(): Role | null {
  const r = claims()?.role;
  return r === "root" || r === "manager" || r === "staff" ? r : null;
}
```

- [ ] **Step 4: Cập nhật nav trong `src/components/sidebar.tsx`**

Thay mảng `ITEMS` (dòng 8 tới 13):

```tsx
const ITEMS: Item[] = [
  { to: "/gate", label: "Trạm cổng", Icon: LayoutGrid, roles: ["staff", "manager", "root"] },
  { to: "/sessions", label: "Quản lý phiên", Icon: ListChecks, roles: ["staff", "manager", "root"] },
  { to: "/stats", label: "Thống kê", Icon: BarChart3, roles: ["manager", "root"] },
  { to: "/config", label: "Cấu hình", Icon: Settings, roles: ["manager", "root"] },
];
```

- [ ] **Step 5: Guard route trong `src/app/router.tsx`**

Thay hai entry `stats` và `config` (dòng 24 tới 32) thành:

```tsx
      {
        path: "stats",
        element: (
          <RequireRole roles={["manager", "root"]}>
            <StatsPage />
          </RequireRole>
        ),
      },
      {
        path: "config",
        element: (
          <RequireRole roles={["manager", "root"]}>
            <ConfigPage />
          </RequireRole>
        ),
      },
```

- [ ] **Step 6: Chạy test, xác nhận pass**

Run: `cd src/frontend && npx vitest run src/components/sidebar.test.tsx src/app/role-guard.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd src/frontend
git add src/lib/auth.ts src/app/router.tsx src/components/sidebar.tsx src/components/sidebar.test.tsx src/app/role-guard.test.tsx
git commit -m "feat(ui): role-based nav and route guards for root/manager/staff"
```

---

### Task 3: Frontend, bỏ thống kê khỏi màn Trạm cổng

**Files:**
- Modify: `src/frontend/src/features/gate/gate-page.tsx:2,24`
- Create: `src/frontend/src/features/gate/gate-page.test.tsx`

**Interfaces:**
- Consumes: `useGateSocket()` trả `{ capture, events, degraded }` (mock trong test).

- [ ] **Step 1: Viết test khẳng định màn cổng không có KPI (failing)**

Tạo `src/features/gate/gate-page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { GatePage } from "./gate-page";

vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({ capture: null, events: [], degraded: false }),
}));

vi.mock("@/api/generated/stats/stats", () => ({
  useGetStats: () => ({ data: { in_lot: 5, entries: 3, exits: 2, revenue: 1000 }, isLoading: false }),
}));

test("gate page shows no statistics KPI", () => {
  render(
    <MemoryRouter>
      <GatePage />
    </MemoryRouter>,
  );
  expect(screen.queryByText("Đang trong bãi")).toBeNull();
  expect(screen.queryByText("Doanh thu")).toBeNull();
});
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd src/frontend && npx vitest run src/features/gate/gate-page.test.tsx`
Expected: FAIL. `GateKpis` còn render nên chuỗi "Đang trong bãi" và "Doanh thu" hiện diện.

- [ ] **Step 3: Bỏ `GateKpis` khỏi `src/features/gate/gate-page.tsx`**

Xóa dòng import (dòng 2):

```tsx
import { GateKpis } from "./gate-kpis";
```

Xóa phần tử render `<GateKpis />` (dòng 24). Sau khi sửa, đầu phần return là khối cảnh báo `degraded` rồi tới khối nút chọn hướng, không còn `<GateKpis />`.

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `cd src/frontend && npx vitest run src/features/gate/gate-page.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd src/frontend
git add src/features/gate/gate-page.tsx src/features/gate/gate-page.test.tsx
git commit -m "feat(gate): remove statistics KPIs from gate station for privacy"
```

---

### Task 4: Frontend, ẩn tab Tài khoản khỏi manager (chỉ root)

**Files:**
- Modify: `src/frontend/src/features/config/config-page.tsx`
- Create: `src/frontend/src/features/config/config-page.test.tsx`

**Interfaces:**
- Consumes: `getRole()` từ `@/lib/auth` (Task 2), trả `"root" | "manager" | "staff" | null`.

- [ ] **Step 1: Viết test hiển thị tab theo vai (failing)**

Tạo `src/features/config/config-page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { ConfigPage } from "./config-page";

vi.mock("./price-rules-tab", () => ({ PriceRulesTab: () => <div>PRICE</div> }));
vi.mock("./users-tab", () => ({ UsersTab: () => <div>USERS</div> }));
vi.mock("./lanes-tab", () => ({ LanesTab: () => <div>LANES</div> }));
vi.mock("./toggles-tab", () => ({ TogglesTab: () => <div>TOGGLES</div> }));

const roleRef = { current: "manager" as string };
vi.mock("@/lib/auth", () => ({ getRole: () => roleRef.current }));

test("manager does not see Tài khoản tab", () => {
  roleRef.current = "manager";
  render(<ConfigPage />);
  expect(screen.queryByText("Tài khoản")).toBeNull();
});

test("root sees Tài khoản tab", () => {
  roleRef.current = "root";
  render(<ConfigPage />);
  expect(screen.getByText("Tài khoản")).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd src/frontend && npx vitest run src/features/config/config-page.test.tsx`
Expected: FAIL ở test manager. `ConfigPage` hiện luôn render tab Tài khoản không phụ thuộc vai.

- [ ] **Step 3: Ẩn tab Tài khoản khi vai không phải root**

Thay toàn bộ `src/features/config/config-page.tsx`:

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PriceRulesTab } from "./price-rules-tab";
import { UsersTab } from "./users-tab";
import { LanesTab } from "./lanes-tab";
import { TogglesTab } from "./toggles-tab";
import { SurfaceCard } from "@/components/surface-card";
import { getRole } from "@/lib/auth";

export function ConfigPage() {
  const isRoot = getRole() === "root";
  return (
    <div className="space-y-4">
      <Tabs defaultValue="price">
        <TabsList>
          <TabsTrigger value="price">Bảng giá</TabsTrigger>
          {isRoot && <TabsTrigger value="users">Tài khoản</TabsTrigger>}
          <TabsTrigger value="lanes">Lane</TabsTrigger>
          <TabsTrigger value="toggles">Feature toggle</TabsTrigger>
        </TabsList>
        <TabsContent value="price">
          <SurfaceCard variant="white">
            <PriceRulesTab />
          </SurfaceCard>
        </TabsContent>
        {isRoot && (
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
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `cd src/frontend && npx vitest run src/features/config/config-page.test.tsx`
Expected: PASS.

- [ ] **Step 5: Chạy toàn bộ test frontend**

Run: `cd src/frontend && npx vitest run`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
cd src/frontend
git add src/features/config/config-page.tsx src/features/config/config-page.test.tsx
git commit -m "feat(config): hide user management tab from manager, root only"
```

---

## Kiểm chứng tiêu chí chấp nhận (sau khi xong 4 task)

- staff: sidebar chỉ Trạm cổng và Quản lý phiên; API `GET /stats` trả 403 (test `test_staff_cannot_get_stats`); route `/stats`, `/config` redirect `/gate` (test role-guard).
- manager: có Thống kê và Cấu hình; không có tab Tài khoản (test `config-page`); `GET /users` trả 403 (test `test_manager_cannot_crud_users`); `GET /stats` trả 200.
- root: thấy tất cả gồm tab Tài khoản; CRUD nhân viên hoạt động (test `test_root_can_crud_users`).
- Màn Trạm cổng không còn KPI (test `gate-page`).
- Toàn bộ suite backend và frontend pass.

## Ghi chú triển khai production

Với cơ sở dữ liệu Postgres đã có dữ liệu, chạy một lần: `cd src/backend && python -m scripts.migrate_admin_to_root` để đổi các vai `admin` cũ sang `root`. Môi trường test dùng `create_all` nên không cần bước này.
