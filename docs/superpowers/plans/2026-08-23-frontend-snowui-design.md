# Frontend SnowUI Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React operations dashboard (staff + admin) for the smart parking system on the SnowUI theme, consuming the frozen FastAPI backend contract, with light/dark mode and a touch-friendly gate screen.

**Architecture:** Vite + React 18 + TypeScript SPA. Generated orval React Query hooks call the backend; JWT is attached by the existing axios interceptor. SnowUI design tokens live as CSS variables (`:root` / `.dark`) mapped into Tailwind v4 `@theme`. Screens are role-guarded routes inside a three-column AppShell. The gate screen is realtime via a hand-written `useGateSocket` (WS is outside OpenAPI) with polling fallback. One small, contained backend enrichment adds the pipeline meta the realtime channel currently omits.

**Tech Stack:** Vite, React 18, TypeScript, React Router v6, TanStack Query (present) + TanStack Table, shadcn/ui + Radix + Tailwind CSS v4, Recharts, lucide-react, React Hook Form + Zod, jwt-decode, Vitest + React Testing Library. Backend touch: FastAPI/Pydantic (enrichment only).

## Global Constraints

Copied verbatim from the spec; every task implicitly includes these.

- **No hardcoded hex in components.** Components use semantic tokens only (`--bg`, `--ink`, `--st-green`, ...). Tokens defined once in `theme/tokens.css`.
- **Color is never the only signal.** Every status uses color + icon + text label (WCAG `color-not-only`).
- **Frontend never computes confidence thresholds.** It renders strictly by the backend `review_state` / `status` string.
- **Disputed sessions are never auto-priced.** Fee for disputed is entered by hand and posted via resolve.
- **Manual override is always reachable.** The "Nhập tay hoàn toàn" button and the plate-edit field are always visible on the gate screen. When `read_plate` toggle is off, the gate forces manual entry.
- **Idempotency by `capture_id`** on the gate so flaky network never double-submits.
- **Contrast >= 4.5:1 in both themes**, verified for dark independently. Focus ring on every interactive element. Icon-only buttons need `aria-label`. Touch targets on the gate >= 44px. Respect `prefers-reduced-motion`. Toasts `aria-live` polite, never steal focus.
- **Privacy (Luật Bảo vệ dữ liệu cá nhân, 01/01/2026):** evidence images shown only on explicit dispute review; each `GET /images/{id}` view is audited by the backend and the UI states access is logged. No face-processing code, no face-recognition imports. Plates are not persisted outside the working-session lifecycle. Retention (30 days after exit) is stated on the session-detail and config screens.
- **Vietnamese display text.** No i18n in MVP.
- **Number/date formatting** via Intl, locale `vi-VN`. Money/duration/plate/time columns use `tabular-nums`.
- **Base URL** from `VITE_API_BASE` (already wired in `src/api/axios-instance.ts`).

---

## File Structure

New frontend files (all under `src/frontend/`). Generated `src/api/generated/**` and `src/api/axios-instance.ts` stay as-is (axios-instance is hand-written and must not be clobbered by orval `clean:true`).

```
src/frontend/
  index.html                      # Vite entry, Inter font preconnect
  vite.config.ts                  # React plugin, @ alias, vitest config
  tsconfig.json                   # add @ path (modify existing)
  components.json                 # shadcn config
  Dockerfile                      # multi-stage node build -> nginx (compose already references ./src/frontend)
  nginx.conf                      # SPA fallback
  src/
    main.tsx                      # ReactDOM root, providers, router
    vite-env.d.ts                 # ImportMetaEnv typing for VITE_API_BASE
    test/setup.ts                 # RTL + jest-dom setup for vitest
    theme/
      tokens.css                  # SnowUI CSS variables :root/.dark + @theme mapping + Inter
      theme-provider.tsx          # light/dark context, localStorage, <html class="dark">
    lib/
      cn.ts                       # clsx + tailwind-merge helper (shadcn standard)
      format.ts                   # currency, duration, datetime, plate (vi-VN)
      status.ts                   # review_state/status -> {token, icon, label}
      auth.ts                     # token store + jwt role/exp read
      image-blob.ts               # authed blob fetch for /images/{id} + /captures image
    app/
      query-client.ts             # QueryClient factory
      router.tsx                  # route table
      role-guard.tsx              # <RequireRole roles=[...]>
      providers.tsx               # QueryClientProvider + ThemeProvider + Toaster
    components/
      ui/                         # shadcn primitives (button, input, dialog, ...)
      app-shell.tsx
      sidebar.tsx
      topbar.tsx
      right-rail.tsx
      kpi-tile.tsx
      surface-card.tsx
      status-chip.tsx             # StatusChip + StatusDot
      plate-field.tsx
      data-table.tsx              # generic TanStack Table wrapper
      empty-state.tsx
      charts/{line-chart,bar-chart,donut-chart}.tsx
    features/
      auth/login-page.tsx
      gate/
        gate-page.tsx
        use-gate-socket.ts        # WS + polling fallback + idempotency
        gate-capture.tsx          # camera frame + pipeline meta chips
        decision-panel.tsx        # renders by review_state (4 states) + manual override
        gate-kpis.tsx
        gate-events-rail.tsx
      sessions/
        sessions-page.tsx
        sessions-columns.tsx
        session-detail-page.tsx
        dispute-panel.tsx
      stats/
        stats-page.tsx
        stats-export.ts           # authed CSV blob download
      config/
        config-page.tsx
        price-rules-tab.tsx
        users-tab.tsx
        lanes-tab.tsx
        toggles-tab.tsx
```

Backend files touched (Task 1 only):
- `src/backend/app/schemas/capture.py` (add `lane`, `duplicate` already present)
- `src/backend/app/routers/captures.py` (enrich WS event + typed `/captures/latest`)
- `src/backend/tests/test_capture_ingest.py` / `test_gate_ws.py` (assert enriched fields)
- Regenerate `src/frontend/openapi.json` + orval output.

---

## Interfaces shared across tasks (exact names)

Generated hooks (import from `@/api/generated/<tag>/<tag>`), models from `@/api/generated/model`:

- auth: `useLogin` -> `TokenResponse { access_token: string; token_type?: string; role: string }`
- sessions: `useConfirmEntry` (`EntryRequest {reading_id}` -> `SessionOut`), `useConfirmExit` (`ExitRequest {reading_id, session_id?}` -> `ExitResult {outcome, session?, candidates?: SessionBrief[], match_flag?}`), `useManualSession` (`ManualRequest {action, plate_text?, vehicle_group?, session_id?}` -> `SessionOut`), `useDisputeSession` (`{sessionId}` -> `SessionOut`), `useResolveSession` (`{sessionId, data: ResolveRequest {fee_amount}}` -> `SessionOut`), `useListSessions(params: ListSessionsParams {plate?, status?, limit?, offset?})` -> `SessionListResponse {total, items: SessionOut[]}`, `useSessionDetail(id)` -> `SessionDetail`
- captures: `useLatestCapture(params: LatestCaptureParams {lane?})`, `useIngestCapture` (edge only, unused by dashboard)
- readings: `usePatchPlate` (`{readingId, data: PlatePatch {plate_text}}`)
- stats: `useGetStats(params: GetStatsParams {from?, to?})`, raw `exportStats` (returns CSV — handled via blob, not the hook)
- config: `useListPriceRules`, `useCreatePriceRule`, `useUpdatePriceRule` (`{ruleId, data}`), `useListLanes`, `useCreateLane`, `useUpdateLane` (`{laneId, data}`), `useGetToggles` -> `ToggleOut {read_plate, plate_color, vehicle_class}`, `useUpdateToggles`
- images: raw blob fetch (not the generated JSON hook)
- users: `useListUsers`, `useCreateUser`, `useUpdateUser` (`{userId, data}`)

Domain string enums (backend, render-only):
- `review_state`: `confident` | `needs_review` | `disputed` | `manual`
- session `status`: `in_lot` | `completed` | `disputed` | `pending_manual`

`lib/auth.ts` produces:
- `saveToken(token: string): void` (also caches role)
- `getToken(): string | null`
- `clearToken(): void`
- `getRole(): 'staff' | 'admin' | null` (decodes JWT, ignores if `exp` passed)
- `isExpired(): boolean`

`lib/format.ts` produces:
- `formatVnd(n: number | null | undefined): string`
- `formatDuration(startISO?: string | null, endISO?: string | null): string`
- `formatDateTime(iso?: string | null): string`
- `formatPlate(s?: string | null): string`

`lib/status.ts` produces:
- `reviewStateMeta(s: string): { token: string; Icon: LucideIcon; label: string }`
- `sessionStatusMeta(s: string): { token: string; Icon: LucideIcon; label: string }`

`features/gate/use-gate-socket.ts` produces:
- `type GateCapture = { reading_id: number; capture_id: string; direction: string; lane?: string | null; review_state: string; plate_text?: string | null; vehicle_group?: string | null; vehicle_type?: string | null; color?: string | null; plate_valid?: boolean | null; image_asset_id?: number | null; duplicate?: boolean }`
- `useGateSocket(opts?: { lane?: string }): { capture: GateCapture | null; events: GateCapture[]; connected: boolean; degraded: boolean }`

---

## Phase 0 — Backend realtime enrichment

### Task 1: Enrich WS event and `/captures/latest`, regenerate client

**Files:**
- Modify: `src/backend/app/schemas/capture.py`
- Modify: `src/backend/app/routers/captures.py:81-110`
- Test: `src/backend/tests/test_capture_ingest.py`, `src/backend/tests/test_gate_ws.py`
- Regenerate: `src/frontend/openapi.json`, `src/frontend/src/api/generated/**`

**Interfaces:**
- Consumes: existing `PlateReading` row (persists `plate_valid`, `color`, `vehicle_type`, `image_asset_id`, `lane`), existing `_response()` helper, `group_for()`.
- Produces: WS event + `/captures/latest` both return the full `CaptureResponse` shape plus `lane`. `CaptureResponse` gains `lane: str | None`.

- [ ] **Step 1: Write the failing tests**

Add to `src/backend/tests/test_gate_ws.py` (inside the existing WS test, after receiving the event assert the enriched keys), and to `test_capture_ingest.py` for latest:

```python
# test_gate_ws.py — after `event = ws.receive_json()`
assert set(event) >= {
    "reading_id", "capture_id", "direction", "lane", "review_state",
    "plate_text", "vehicle_group", "vehicle_type", "color",
    "plate_valid", "image_asset_id", "duplicate",
}

# test_capture_ingest.py — new test
def test_latest_capture_returns_enriched_fields(client, edge_headers, sample_capture):
    client.post("/captures", **sample_capture)  # existing ingest helper
    r = client.get("/captures/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["reading_id"] > 0
    assert "vehicle_type" in body and "color" in body
    assert "plate_valid" in body and "image_asset_id" in body
    assert "lane" in body and "duplicate" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/backend && pytest tests/test_gate_ws.py tests/test_capture_ingest.py -q`
Expected: FAIL — enriched keys missing from event and latest body.

- [ ] **Step 3: Add `lane` to `CaptureResponse`**

In `src/backend/app/schemas/capture.py`, add to `CaptureResponse` (after `direction`):

```python
    lane: str | None = None
```

- [ ] **Step 4: Enrich the WS publish and type `/captures/latest`**

In `src/backend/app/routers/captures.py`, replace the `gate_hub.publish({...})` block (lines ~81-89) with the enriched event, and rewrite `latest_capture` to return the typed `CaptureResponse`:

```python
    gate_hub.publish({
        "reading_id": reading.id,
        "capture_id": reading.capture_id,
        "direction": reading.direction,
        "lane": reading.lane,
        "review_state": reading.review_state,
        "plate_text": plate_text,
        "vehicle_group": group_for(data.vehicle_type),
        "vehicle_type": reading.vehicle_type,
        "color": reading.color,
        "plate_valid": reading.plate_valid,
        "image_asset_id": reading.image_asset_id,
        "duplicate": False,
    })
```

```python
@router.get("/captures/latest", response_model=CaptureResponse | None)
def latest_capture(lane: str | None = None, db: Session = Depends(get_db)) -> CaptureResponse | None:
    stmt = select(PlateReading).order_by(PlateReading.id.desc())
    if lane:
        stmt = stmt.where(PlateReading.lane == lane)
    reading = db.scalars(stmt.limit(1)).first()
    if reading is None:
        return None
    text = crypto.decrypt_text(reading.plate_text_ciphertext) if reading.plate_text_ciphertext else None
    resp = _response(reading, text, group_for(reading.vehicle_type), duplicate=False)
    resp.lane = reading.lane
    return resp
```

Also update `_response` to set `lane` (add `lane=reading.lane,` inside the `CaptureResponse(...)` call).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd src/backend && pytest tests/test_gate_ws.py tests/test_capture_ingest.py -q`
Expected: PASS. Then run full suite: `pytest -q` — Expected: all previously-passing tests still pass (84+).

- [ ] **Step 6: Regenerate OpenAPI + orval client**

Run:
```bash
cd src/backend && python -m scripts.export_openapi > ../frontend/openapi.json
cd ../frontend && npm run gen:api
```
Expected: `openapi.json` updated; `latestCapture` now returns `CaptureResponse` (check `src/api/generated/captures/captures.ts` no longer types it as `LatestCapture200`). `git status` shows regenerated model files.

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/schemas/capture.py src/backend/app/routers/captures.py src/backend/tests src/frontend/openapi.json src/frontend/src/api/generated
git commit -m "feat(backend): enrich gate WS event and /captures/latest with pipeline meta"
```

---

## Phase 1 — Frontend foundation

### Task 2: Vite + React + TS + Vitest scaffold

**Files:**
- Create: `src/frontend/index.html`, `src/frontend/vite.config.ts`, `src/frontend/src/main.tsx`, `src/frontend/src/vite-env.d.ts`, `src/frontend/src/test/setup.ts`, `src/frontend/src/lib/cn.ts`
- Modify: `src/frontend/package.json`, `src/frontend/tsconfig.json`

**Interfaces:**
- Produces: working `npm run dev`, `npm run build`, `npm run test`; `@` alias -> `src`; `cn()` helper.

- [ ] **Step 1: Install deps**

Run (in `src/frontend`):
```bash
npm i react react-dom react-router-dom @tanstack/react-table recharts lucide-react react-hook-form zod @hookform/resolvers jwt-decode clsx tailwind-merge class-variance-authority
npm i -D vite @vitejs/plugin-react @types/react @types/react-dom vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 2: Add scripts to `package.json`**

Merge into `"scripts"` (keep existing `gen:api*`):

```json
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 3: `tsconfig.json` — add path alias**

Add to `compilerOptions`:

```json
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["vitest/globals", "@testing-library/jest-dom"]
```

- [ ] **Step 4: `vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

- [ ] **Step 5: `src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 6: `src/test/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 7: `src/lib/cn.ts`**

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 8: `index.html`**

```html
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <title>Bãi đỗ xe</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 9: `src/main.tsx` (temporary smoke root; replaced in Task 8)**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import "@/theme/tokens.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div style={{ padding: 24 }}>Parking dashboard boot OK</div>
  </React.StrictMode>,
);
```

Note: `tokens.css` is created in Task 4; until then temporarily comment the import or create an empty file. Prefer to do Task 3+4 before running dev.

- [ ] **Step 10: Verify build tooling**

Run: `npm run test` (no tests yet -> "No test files" is acceptable) and `npx tsc --noEmit`.
Expected: tsc passes (allowing the tokens.css import once Task 4 done).

- [ ] **Step 11: Commit**

```bash
git add src/frontend/package.json src/frontend/package-lock.json src/frontend/tsconfig.json src/frontend/vite.config.ts src/frontend/index.html src/frontend/src/main.tsx src/frontend/src/vite-env.d.ts src/frontend/src/test src/frontend/src/lib/cn.ts
git commit -m "chore(frontend): scaffold vite react ts + vitest"
```

### Task 3: Tailwind v4 + shadcn/ui init

**Files:**
- Create: `src/frontend/components.json`, shadcn primitives under `src/frontend/src/components/ui/`
- Modify: `src/frontend/vite.config.ts` (add tailwind plugin), `src/frontend/src/theme/tokens.css` (created here as the CSS entry)

**Interfaces:**
- Produces: Tailwind v4 pipeline; shadcn `cn` path; base UI primitives (button, input, label, dialog, tabs, toast/sonner, table, select, switch, skeleton, badge, card, dropdown-menu).

- [ ] **Step 1: Install Tailwind v4**

Run: `npm i -D tailwindcss @tailwindcss/vite`

- [ ] **Step 2: Add Tailwind plugin to `vite.config.ts`**

Add import `import tailwindcss from "@tailwindcss/vite";` and put `tailwindcss()` in the `plugins` array (before/after react is fine).

- [ ] **Step 3: `src/theme/tokens.css` — Tailwind entry (tokens filled in Task 4)**

```css
@import "tailwindcss";
@custom-variant dark (&:is(.dark *));
```

- [ ] **Step 4: `components.json` for shadcn (Tailwind v4, CSS variables)**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/theme/tokens.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/cn",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

- [ ] **Step 5: Add primitives via shadcn CLI**

Run:
```bash
npx shadcn@latest add button input label card dialog tabs table select switch skeleton badge dropdown-menu sonner
```
Expected: files created under `src/components/ui/`. If the CLI rewrites `tokens.css` with its own `:root` block, that is expected — Task 4 overwrites it with the SnowUI tokens.

- [ ] **Step 6: Verify**

Run: `npx tsc --noEmit`
Expected: PASS (shadcn primitives compile).

- [ ] **Step 7: Commit**

```bash
git add src/frontend/components.json src/frontend/vite.config.ts src/frontend/src/theme/tokens.css src/frontend/src/components/ui src/frontend/package.json src/frontend/package-lock.json
git commit -m "chore(frontend): tailwind v4 + shadcn primitives"
```

### Task 4: SnowUI design tokens + ThemeProvider

**Files:**
- Modify (overwrite): `src/frontend/src/theme/tokens.css`
- Create: `src/frontend/src/theme/theme-provider.tsx`
- Test: `src/frontend/src/theme/theme-provider.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: CSS tokens (all names from Global Constraints); `ThemeProvider`, `useTheme(): { theme: 'light'|'dark'; toggle(): void; setTheme(t): void }`. Toggling adds/removes `dark` class on `document.documentElement` and persists to `localStorage['theme']`.

- [ ] **Step 1: Write the failing test**

`src/frontend/src/theme/theme-provider.test.tsx`:

```tsx
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider, useTheme } from "./theme-provider";

function Probe() {
  const { theme, toggle } = useTheme();
  return <button onClick={toggle}>theme:{theme}</button>;
}

test("toggles dark class on html and persists", async () => {
  render(<ThemeProvider><Probe /></ThemeProvider>);
  expect(screen.getByText("theme:light")).toBeInTheDocument();
  expect(document.documentElement.classList.contains("dark")).toBe(false);
  await act(async () => { await userEvent.click(screen.getByRole("button")); });
  expect(document.documentElement.classList.contains("dark")).toBe(true);
  expect(localStorage.getItem("theme")).toBe("dark");
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- theme-provider`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `theme-provider.tsx`**

```tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "light" | "dark";
type Ctx = { theme: Theme; toggle: () => void; setTheme: (t: Theme) => void };

const ThemeContext = createContext<Ctx | null>(null);

function initialTheme(): Theme {
  const saved = typeof localStorage !== "undefined" ? localStorage.getItem("theme") : null;
  if (saved === "light" || saved === "dark") return saved;
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(initialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const setTheme = (t: Theme) => setThemeState(t);
  const toggle = () => setThemeState((t) => (t === "light" ? "dark" : "light"));

  return (
    <ThemeContext.Provider value={{ theme, toggle, setTheme }}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): Ctx {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
```

- [ ] **Step 4: Overwrite `tokens.css` with SnowUI tokens**

```css
@import "tailwindcss";
@custom-variant dark (&:is(.dark *));

:root {
  --bg: #ffffff;
  --surface: #f7f9fb;
  --ink: #1c1c1c;
  --muted: rgba(28, 28, 28, 0.4);
  --faint: rgba(28, 28, 28, 0.2);
  --line: rgba(28, 28, 28, 0.1);
  --primary: #1c1c1c;
  --on-primary: #ffffff;

  --tile-blue: #e3f5ff;
  --tile-purple: #e5ecf6;
  --tile-mint: #def8ee;
  --tile-peri: #edf0ff;

  --chart-1: #95a4fc;
  --chart-2: #c6c7f8;
  --chart-3: #a1e3cb;
  --chart-4: #b1e3ff;
  --chart-5: #a8c5da;
  --chart-6: #1c1c1c;

  --st-green: #1f9d63;
  --st-purple: #7a7cd6;
  --st-blue: #2e8bc0;
  --st-amber: #b98900;
  --st-red: #d24a3e;
  --st-grey: rgba(28, 28, 28, 0.4);

  --radius-card: 16px;
  --radius-control: 8px;
}

.dark {
  --bg: #1c1c1c;
  --surface: rgba(255, 255, 255, 0.05);
  --ink: #ffffff;
  --muted: rgba(255, 255, 255, 0.4);
  --faint: rgba(255, 255, 255, 0.2);
  --line: rgba(255, 255, 255, 0.1);
  --primary: #95a4fc;
  --on-primary: #1c1c1c;

  --tile-blue: rgba(255, 255, 255, 0.05);
  --tile-purple: rgba(255, 255, 255, 0.05);
  --tile-mint: #def8ee;
  --tile-peri: #edf0ff;

  --st-green: #3fbe82;
  --st-purple: #95a4fc;
  --st-blue: #59a8d4;
  --st-amber: #e6a23c;
  --st-red: #e4695e;
  --st-grey: rgba(255, 255, 255, 0.4);
}

@theme inline {
  --color-bg: var(--bg);
  --color-surface: var(--surface);
  --color-ink: var(--ink);
  --color-muted: var(--muted);
  --color-faint: var(--faint);
  --color-line: var(--line);
  --color-primary: var(--primary);
  --color-on-primary: var(--on-primary);

  --color-tile-blue: var(--tile-blue);
  --color-tile-purple: var(--tile-purple);
  --color-tile-mint: var(--tile-mint);
  --color-tile-peri: var(--tile-peri);

  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-chart-6: var(--chart-6);

  --color-st-green: var(--st-green);
  --color-st-purple: var(--st-purple);
  --color-st-blue: var(--st-blue);
  --color-st-amber: var(--st-amber);
  --color-st-red: var(--st-red);
  --color-st-grey: var(--st-grey);

  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --radius: var(--radius-control);
}

@layer base {
  html, body, #root { height: 100%; }
  body {
    background-color: var(--bg);
    color: var(--ink);
    font-family: var(--font-sans);
    font-feature-settings: "cv11";
  }
  .tnum { font-variant-numeric: tabular-nums; }
}
```

This makes utilities like `bg-bg`, `text-ink`, `bg-surface`, `border-line`, `text-st-red`, `bg-tile-blue`, `text-chart-1` available. Card radius via `rounded-[var(--radius-card)]`; controls `rounded-[var(--radius-control)]`.

- [ ] **Step 5: Run to verify pass**

Run: `npm run test -- theme-provider`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/theme
git commit -m "feat(frontend): SnowUI design tokens + light/dark ThemeProvider"
```

### Task 5: Formatting utilities

**Files:**
- Create: `src/frontend/src/lib/format.ts`
- Test: `src/frontend/src/lib/format.test.ts`

**Interfaces:**
- Produces: `formatVnd`, `formatDuration`, `formatDateTime`, `formatPlate` (signatures in shared Interfaces section).

- [ ] **Step 1: Write the failing test**

`src/frontend/src/lib/format.test.ts`:

```ts
import { formatVnd, formatDuration, formatDateTime, formatPlate } from "./format";

test("formatVnd renders vi-VN dong", () => {
  expect(formatVnd(15000)).toBe("15.000 ₫");
  expect(formatVnd(null)).toBe("—");
});

test("formatDuration renders h m from ISO range", () => {
  expect(formatDuration("2026-08-23T08:00:00Z", "2026-08-23T09:30:00Z")).toBe("1 giờ 30 phút");
  expect(formatDuration("2026-08-23T08:00:00Z", null)).toBe("—");
});

test("formatDateTime formats vi-VN", () => {
  expect(formatDateTime(null)).toBe("—");
  expect(typeof formatDateTime("2026-08-23T09:30:00Z")).toBe("string");
});

test("formatPlate uppercases and trims", () => {
  expect(formatPlate(" 51f-12345 ")).toBe("51F-12345");
  expect(formatPlate(null)).toBe("—");
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- format`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `format.ts`**

```ts
const DASH = "—";

const vnd = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" });
const dt = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit", month: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit",
});

export function formatVnd(n: number | null | undefined): string {
  if (n === null || n === undefined) return DASH;
  // Intl currency renders "15.000 ₫" for vi-VN.
  return vnd.format(n);
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return DASH;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return DASH;
  return dt.format(d);
}

export function formatDuration(startISO?: string | null, endISO?: string | null): string {
  if (!startISO || !endISO) return DASH;
  const ms = new Date(endISO).getTime() - new Date(startISO).getTime();
  if (!Number.isFinite(ms) || ms < 0) return DASH;
  const mins = Math.floor(ms / 60000);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h === 0) return `${m} phút`;
  return `${h} giờ ${m} phút`;
}

export function formatPlate(s?: string | null): string {
  if (!s) return DASH;
  return s.trim().toUpperCase();
}
```

Note: if the test's exact currency string differs by Node ICU build (e.g. non-breaking space), adjust the expected string to match `vnd.format(15000)` output printed once — keep the implementation, fix the assertion.

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- format`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/lib/format.ts src/frontend/src/lib/format.test.ts
git commit -m "feat(frontend): vi-VN formatting utilities"
```

### Task 6: Auth token store + JWT role + 401 handling + QueryClient

**Files:**
- Create: `src/frontend/src/lib/auth.ts`, `src/frontend/src/app/query-client.ts`
- Modify: `src/frontend/src/api/axios-instance.ts` (add 401 response interceptor — hand-written file, safe to edit)
- Test: `src/frontend/src/lib/auth.test.ts`

**Interfaces:**
- Produces: `saveToken`, `getToken`, `clearToken`, `getRole`, `isExpired` (signatures in shared Interfaces). `makeQueryClient(): QueryClient`.
- On any 401, axios interceptor calls `clearToken()` then `window.location.assign("/login")`.

- [ ] **Step 1: Write the failing test**

`src/frontend/src/lib/auth.test.ts`:

```ts
import { saveToken, getToken, clearToken, getRole, isExpired } from "./auth";

// header.payload.signature — payload base64url of {role, exp}
function makeJwt(payload: object): string {
  const b64 = (o: object) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${b64({ alg: "HS256" })}.${b64(payload)}.sig`;
}

beforeEach(() => localStorage.clear());

test("stores and reads token", () => {
  const t = makeJwt({ role: "admin", exp: Math.floor(Date.now() / 1000) + 3600 });
  saveToken(t);
  expect(getToken()).toBe(t);
  expect(getRole()).toBe("admin");
  expect(isExpired()).toBe(false);
});

test("expired token", () => {
  const t = makeJwt({ role: "staff", exp: Math.floor(Date.now() / 1000) - 10 });
  saveToken(t);
  expect(isExpired()).toBe(true);
});

test("clear", () => {
  saveToken(makeJwt({ role: "staff", exp: 0 }));
  clearToken();
  expect(getToken()).toBeNull();
  expect(getRole()).toBeNull();
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- auth`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `auth.ts`**

```ts
import { jwtDecode } from "jwt-decode";

type Claims = { role?: string; exp?: number };
export type Role = "staff" | "admin";
const KEY = "token";

export function saveToken(token: string): void {
  localStorage.setItem(KEY, token);
}
export function getToken(): string | null {
  return localStorage.getItem(KEY);
}
export function clearToken(): void {
  localStorage.removeItem(KEY);
}

function claims(): Claims | null {
  const t = getToken();
  if (!t) return null;
  try {
    return jwtDecode<Claims>(t);
  } catch {
    return null;
  }
}

export function getRole(): Role | null {
  const r = claims()?.role;
  return r === "staff" || r === "admin" ? r : null;
}

export function isExpired(): boolean {
  const exp = claims()?.exp;
  if (!exp) return true;
  return Date.now() >= exp * 1000;
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- auth`
Expected: PASS.

- [ ] **Step 5: Add 401 interceptor to `axios-instance.ts`**

Append after the request interceptor (do not remove existing code):

```ts
AXIOS_INSTANCE.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") window.location.assign("/login");
    }
    return Promise.reject(error);
  },
);
```

- [ ] **Step 6: Write `query-client.ts`**

```ts
import { QueryClient } from "@tanstack/react-query";

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
    },
  });
}
```

- [ ] **Step 7: Run full test + tsc**

Run: `npm run test && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/frontend/src/lib/auth.ts src/frontend/src/lib/auth.test.ts src/frontend/src/app/query-client.ts src/frontend/src/api/axios-instance.ts
git commit -m "feat(frontend): auth token store, jwt role, 401 redirect, query client"
```

### Task 7: Router + role guard

**Files:**
- Create: `src/frontend/src/app/role-guard.tsx`, `src/frontend/src/app/router.tsx`, `src/frontend/src/app/providers.tsx`
- Test: `src/frontend/src/app/role-guard.test.tsx`

**Interfaces:**
- Consumes: `getToken`, `getRole`, `isExpired`, `Role`.
- Produces: `<RequireRole roles={Role[]}>` — if no valid token -> redirect `/login`; if role not in `roles` -> redirect `/gate`. `AppRouter` component. `Providers` wrapping QueryClientProvider + ThemeProvider + `<Toaster/>` (sonner).

- [ ] **Step 1: Write the failing test**

`src/frontend/src/app/role-guard.test.tsx`:

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
        <Route path="/config" element={<RequireRole roles={["admin"]}><div>CONFIG</div></RequireRole>} />
      </Routes>
    </MemoryRouter>
  );
}

test("no token redirects to login", () => {
  clearToken();
  render(tree("/config"));
  expect(screen.getByText("LOGIN")).toBeInTheDocument();
});

test("staff blocked from admin route -> gate", () => {
  saveToken(jwt("staff"));
  render(tree("/config"));
  expect(screen.getByText("GATE")).toBeInTheDocument();
});

test("admin allowed", () => {
  saveToken(jwt("admin"));
  render(tree("/config"));
  expect(screen.getByText("CONFIG")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- role-guard`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `role-guard.tsx`**

```tsx
import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { getToken, getRole, isExpired, type Role } from "@/lib/auth";

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const token = getToken();
  if (!token || isExpired()) return <Navigate to="/login" replace />;
  const role = getRole();
  if (!role || !roles.includes(role)) return <Navigate to="/gate" replace />;
  return <>{children}</>;
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- role-guard`
Expected: PASS.

- [ ] **Step 5: Write `providers.tsx`**

```tsx
import type { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/theme/theme-provider";
import { makeQueryClient } from "./query-client";

const client = makeQueryClient();

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        {children}
        <Toaster position="top-right" />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 6: Write `router.tsx` (routes wired to real pages in later tasks; use placeholders that are real components created here)**

Create the route table referencing page components. Until each feature task lands, point unimplemented routes at a shared `<EmptyState/>`-based stub. Real version:

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/app-shell";
import { RequireRole } from "./role-guard";
import { LoginPage } from "@/features/auth/login-page";
import { GatePage } from "@/features/gate/gate-page";
import { SessionsPage } from "@/features/sessions/sessions-page";
import { SessionDetailPage } from "@/features/sessions/session-detail-page";
import { StatsPage } from "@/features/stats/stats-page";
import { ConfigPage } from "@/features/config/config-page";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: (
      <RequireRole roles={["staff", "admin"]}>
        <AppShell />
      </RequireRole>
    ),
    children: [
      { index: true, element: <Navigate to="/gate" replace /> },
      { path: "gate", element: <GatePage /> },
      { path: "sessions", element: <SessionsPage /> },
      { path: "sessions/:id", element: <SessionDetailPage /> },
      { path: "stats", element: <StatsPage /> },
      {
        path: "config",
        element: (
          <RequireRole roles={["admin"]}>
            <ConfigPage />
          </RequireRole>
        ),
      },
    ],
  },
  { path: "*", element: <Navigate to="/gate" replace /> },
]);
```

Note: page imports resolve only after their tasks land. Execute Task 8 (AppShell) then Tasks 9-17. To keep the tree compiling between tasks, create each page file as a minimal stub (`export function XPage(){ return <EmptyState title="..."/>; }`) when its route is first referenced, then flesh out in its task.

- [ ] **Step 7: Update `main.tsx` to use providers + router**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import "@/theme/tokens.css";
import { Providers } from "@/app/providers";
import { router } from "@/app/router";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  </React.StrictMode>,
);
```

- [ ] **Step 8: Commit**

```bash
git add src/frontend/src/app src/frontend/src/main.tsx
git commit -m "feat(frontend): router + role guard + providers"
```

### Task 8: AppShell, Sidebar, Topbar, RightRail

**Files:**
- Create: `src/frontend/src/components/app-shell.tsx`, `sidebar.tsx`, `topbar.tsx`, `right-rail.tsx`, `surface-card.tsx`, `empty-state.tsx`
- Test: `src/frontend/src/components/sidebar.test.tsx`

**Interfaces:**
- Consumes: `getRole`, `clearToken`, `useTheme`, React Router `<Outlet/>`, `useLocation`.
- Produces: `AppShell` (three-column grid: sidebar 212px / main / right rail 300px; rail hidden < 1200px, sidebar collapses < 860px). `Sidebar` filters nav by role. `Topbar` with collapse, breadcrumb, search, theme toggle, logout. `RightRail` with three blocks (props-driven; visible only on gate + stats). `SurfaceCard` variants `surface`|`white`. `EmptyState`.

- [ ] **Step 1: Write the failing test (role-filtered nav)**

`src/frontend/src/components/sidebar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { saveToken } from "@/lib/auth";

function jwt(role: string) {
  const b64 = (o: object) => btoa(JSON.stringify(o)).replace(/=+$/, "");
  return `${b64({})}.${b64({ role, exp: Math.floor(Date.now() / 1000) + 3600 })}.s`;
}

test("staff does not see Cấu hình; admin does", () => {
  saveToken(jwt("staff"));
  const { rerender } = render(<MemoryRouter><Sidebar collapsed={false} /></MemoryRouter>);
  expect(screen.queryByText("Cấu hình")).toBeNull();
  expect(screen.getByText("Trạm cổng")).toBeInTheDocument();

  saveToken(jwt("admin"));
  rerender(<MemoryRouter><Sidebar collapsed={false} /></MemoryRouter>);
  expect(screen.getByText("Cấu hình")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- sidebar`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `sidebar.tsx`**

```tsx
import { NavLink } from "react-router-dom";
import { LayoutGrid, ListChecks, BarChart3, Settings, type LucideIcon } from "lucide-react";
import { getRole, type Role } from "@/lib/auth";
import { cn } from "@/lib/cn";

type Item = { to: string; label: string; Icon: LucideIcon; roles: Role[] };
const ITEMS: Item[] = [
  { to: "/gate", label: "Trạm cổng", Icon: LayoutGrid, roles: ["staff", "admin"] },
  { to: "/sessions", label: "Quản lý phiên", Icon: ListChecks, roles: ["staff", "admin"] },
  { to: "/stats", label: "Thống kê", Icon: BarChart3, roles: ["staff", "admin"] },
  { to: "/config", label: "Cấu hình", Icon: Settings, roles: ["admin"] },
];

export function Sidebar({ collapsed }: { collapsed: boolean }) {
  const role = getRole();
  const items = ITEMS.filter((i) => role && i.roles.includes(role));
  return (
    <nav className="flex h-full flex-col gap-1 p-3" aria-label="Điều hướng chính">
      <div className="mb-4 px-2 text-sm font-semibold">Bãi đỗ xe</div>
      {items.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "relative flex items-center gap-3 rounded-[var(--radius-control)] px-3 py-2 text-sm",
              "text-ink hover:bg-surface",
              isActive && "bg-surface font-medium before:absolute before:left-0 before:top-1/2 before:h-4 before:w-0.5 before:-translate-y-1/2 before:bg-ink before:content-['']",
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
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- sidebar`
Expected: PASS.

- [ ] **Step 5: Write `surface-card.tsx` and `empty-state.tsx`**

```tsx
// surface-card.tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function SurfaceCard({
  variant = "surface", className, children,
}: { variant?: "surface" | "white"; className?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] p-5",
        variant === "surface" ? "bg-surface" : "bg-bg border border-line",
        className,
      )}
    >
      {children}
    </div>
  );
}
```

```tsx
// empty-state.tsx
import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 p-10 text-center">
      <Inbox className="text-muted" aria-hidden />
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint && <p className="text-[13px] text-muted">{hint}</p>}
      {action}
    </div>
  );
}
```

- [ ] **Step 6: Write `right-rail.tsx`**

```tsx
import type { ReactNode } from "react";

export function RightRail({ blocks }: { blocks: { title: string; body: ReactNode }[] }) {
  return (
    <aside className="hidden w-[300px] shrink-0 flex-col gap-5 border-l border-line p-5 xl:flex" aria-label="Bảng phụ">
      {blocks.map((b) => (
        <section key={b.title}>
          <h2 className="mb-3 text-sm font-semibold">{b.title}</h2>
          {b.body}
        </section>
      ))}
    </aside>
  );
}
```

- [ ] **Step 7: Write `topbar.tsx`**

```tsx
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
        <Button variant="ghost" size="icon" aria-label={theme === "dark" ? "Chế độ sáng" : "Chế độ tối"} onClick={toggle}>
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
        <Button
          variant="ghost" size="icon" aria-label="Đăng xuất"
          onClick={() => { clearToken(); nav("/login"); }}
        >
          <LogOut size={18} />
        </Button>
      </div>
    </header>
  );
}
```

- [ ] **Step 8: Write `app-shell.tsx`**

```tsx
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
```

- [ ] **Step 9: Create minimal page stubs so router compiles**

Create stub files (each replaced in its own task):
`features/auth/login-page.tsx`, `features/gate/gate-page.tsx`, `features/sessions/sessions-page.tsx`, `features/sessions/session-detail-page.tsx`, `features/stats/stats-page.tsx`, `features/config/config-page.tsx`, each:

```tsx
import { EmptyState } from "@/components/empty-state";
export function XPage() { return <EmptyState title="Đang xây dựng" />; }
```

(Rename `XPage` to the matching export name per `router.tsx`.)

- [ ] **Step 10: Run dev + build**

Run: `npm run build`
Expected: build passes; `npm run dev` renders shell with sidebar + topbar, dark toggle works.

- [ ] **Step 11: Commit**

```bash
git add src/frontend/src/components src/frontend/src/features
git commit -m "feat(frontend): app shell, sidebar, topbar, right rail, cards"
```

---

## Phase 2 — Login and auth flow

### Task 9: Login screen

**Files:**
- Modify: `src/frontend/src/features/auth/login-page.tsx`
- Test: `src/frontend/src/features/auth/login-page.test.tsx`

**Interfaces:**
- Consumes: `useLogin` (`@/api/generated/auth/auth`), `LoginRequest`, `saveToken`, `getRole`, RHF + Zod, sonner `toast`.
- Produces: `LoginPage`. On success: `saveToken(access_token)`, navigate to `/gate`. On 401: inline error, focus username.

- [ ] **Step 1: Write the failing test**

`login-page.test.tsx` (mock `useLogin`):

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "./login-page";

const mutateAsync = vi.fn();
vi.mock("@/api/generated/auth/auth", () => ({
  useLogin: () => ({ mutateAsync, isPending: false }),
}));
const navigate = vi.fn();
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  useNavigate: () => navigate,
}));

test("submits credentials and navigates to /gate", async () => {
  mutateAsync.mockResolvedValue({ access_token: "h.e.s", token_type: "bearer", role: "staff" });
  render(<MemoryRouter><LoginPage /></MemoryRouter>);
  await userEvent.type(screen.getByLabelText("Tên đăng nhập"), "guard1");
  await userEvent.type(screen.getByLabelText("Mật khẩu"), "secret");
  await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
  expect(mutateAsync).toHaveBeenCalledWith({ data: { username: "guard1", password: "secret" } });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- login-page`
Expected: FAIL — stub has no form.

- [ ] **Step 3: Implement `login-page.tsx`**

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff } from "lucide-react";
import { useLogin } from "@/api/generated/auth/auth";
import { saveToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({ username: z.string().min(1, "Bắt buộc"), password: z.string().min(1, "Bắt buộc") });
type Form = z.infer<typeof schema>;

export function LoginPage() {
  const nav = useNavigate();
  const { mutateAsync, isPending } = useLogin();
  const [show, setShow] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const { register, handleSubmit, setFocus, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: Form) => {
    setAuthError(null);
    try {
      const res = await mutateAsync({ data });
      saveToken(res.access_token);
      nav("/gate");
    } catch {
      setAuthError("Sai tên đăng nhập hoặc mật khẩu");
      setFocus("username");
    }
  };

  return (
    <div className="grid h-full grid-cols-1 md:grid-cols-2">
      <div className="relative hidden items-center justify-center bg-[#1c1c1c] md:flex">
        <div className="absolute inset-0 bg-gradient-to-br from-[#95a4fc]/30 to-transparent" aria-hidden />
        <span className="relative text-2xl font-semibold text-white">Bãi đỗ xe</span>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={handleSubmit(onSubmit)} className="w-full max-w-sm space-y-4" noValidate>
          <h1 className="text-xl font-semibold">Đăng nhập</h1>
          {authError && <p role="alert" className="text-sm text-st-red">{authError}</p>}
          <div className="space-y-1.5">
            <Label htmlFor="username">Tên đăng nhập</Label>
            <Input id="username" autoComplete="username" {...register("username")} />
            {errors.username && <p className="text-[13px] text-st-red">{errors.username.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Mật khẩu</Label>
            <div className="relative">
              <Input id="password" type={show ? "text" : "password"} autoComplete="current-password" {...register("password")} />
              <button
                type="button" onClick={() => setShow((s) => !s)}
                aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted"
              >
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && <p className="text-[13px] text-st-red">{errors.password.message}</p>}
          </div>
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? "Đang đăng nhập..." : "Đăng nhập"}
          </Button>
          <a href="#" className="block text-[13px] text-muted">Quên mật khẩu</a>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- login-page`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/features/auth
git commit -m "feat(frontend): login screen + auth flow"
```

---

## Phase 3 — Gate screen (core, then realtime in Phase 4)

### Task 10: Status mapping + StatusChip/StatusDot + PlateField

**Files:**
- Create: `src/frontend/src/lib/status.ts`, `src/frontend/src/components/status-chip.tsx`, `src/frontend/src/components/plate-field.tsx`
- Test: `src/frontend/src/lib/status.test.ts`

**Interfaces:**
- Produces: `reviewStateMeta`, `sessionStatusMeta` (return `{ token, Icon, label }`). `StatusChip`/`StatusDot` (props: `kind: 'review'|'session'; value: string`). `PlateField` (props: `value, onChange, highlight?, size?: 'md'|'lg', disabled?`).

- [ ] **Step 1: Write the failing test**

`status.test.ts`:

```ts
import { reviewStateMeta, sessionStatusMeta } from "./status";

test("review_state maps to token+label", () => {
  expect(reviewStateMeta("confident").token).toBe("st-green");
  expect(reviewStateMeta("needs_review").token).toBe("st-amber");
  expect(reviewStateMeta("disputed").token).toBe("st-red");
  expect(reviewStateMeta("manual").token).toBe("st-purple");
  expect(reviewStateMeta("confident").label).toBe("Tin cậy");
});

test("session status maps", () => {
  expect(sessionStatusMeta("completed").token).toBe("st-green");
  expect(sessionStatusMeta("in_lot").token).toBe("st-blue");
  expect(sessionStatusMeta("disputed").token).toBe("st-red");
  expect(sessionStatusMeta("pending_manual").token).toBe("st-purple");
});

test("unknown falls back to grey", () => {
  expect(reviewStateMeta("weird").token).toBe("st-grey");
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- status`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `status.ts`**

```ts
import { CheckCircle2, AlertTriangle, XCircle, Pencil, LogIn, Clock, HelpCircle, type LucideIcon } from "lucide-react";

type Meta = { token: string; Icon: LucideIcon; label: string };
const GREY: Meta = { token: "st-grey", Icon: HelpCircle, label: "Không rõ" };

const REVIEW: Record<string, Meta> = {
  confident: { token: "st-green", Icon: CheckCircle2, label: "Tin cậy" },
  needs_review: { token: "st-amber", Icon: AlertTriangle, label: "Cần soát" },
  disputed: { token: "st-red", Icon: XCircle, label: "Tranh chấp" },
  manual: { token: "st-purple", Icon: Pencil, label: "Nhập tay" },
};

const SESSION: Record<string, Meta> = {
  completed: { token: "st-green", Icon: CheckCircle2, label: "Hoàn tất" },
  in_lot: { token: "st-blue", Icon: LogIn, label: "Trong bãi" },
  disputed: { token: "st-red", Icon: XCircle, label: "Tranh chấp" },
  pending_manual: { token: "st-purple", Icon: Clock, label: "Chờ xử lý tay" },
};

export function reviewStateMeta(s: string): Meta { return REVIEW[s] ?? GREY; }
export function sessionStatusMeta(s: string): Meta { return SESSION[s] ?? GREY; }
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- status`
Expected: PASS.

- [ ] **Step 5: Write `status-chip.tsx`**

```tsx
import { reviewStateMeta, sessionStatusMeta } from "@/lib/status";

function meta(kind: "review" | "session", value: string) {
  return kind === "review" ? reviewStateMeta(value) : sessionStatusMeta(value);
}

export function StatusDot({ kind, value }: { kind: "review" | "session"; value: string }) {
  const { token } = meta(kind, value);
  return <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: `var(--${token})` }} aria-hidden />;
}

export function StatusChip({ kind, value }: { kind: "review" | "session"; value: string }) {
  const { token, Icon, label } = meta(kind, value);
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[13px]"
      style={{ color: `var(--${token})`, backgroundColor: `color-mix(in srgb, var(--${token}) 12%, transparent)` }}
    >
      <Icon size={14} aria-hidden />
      <span>{label}</span>
    </span>
  );
}
```

- [ ] **Step 6: Write `plate-field.tsx`**

```tsx
import { cn } from "@/lib/cn";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function PlateField({
  value, onChange, highlight = false, size = "md", disabled = false,
}: {
  value: string; onChange: (v: string) => void;
  highlight?: boolean; size?: "md" | "lg"; disabled?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="plate">Biển số</Label>
      <Input
        id="plate" value={value} disabled={disabled}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        className={cn(
          "tnum font-semibold tracking-wide",
          size === "lg" ? "h-12 text-[30px]" : "text-base",
          highlight && "border-st-amber ring-1 ring-st-amber",
        )}
      />
    </div>
  );
}
```

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/lib/status.ts src/frontend/src/lib/status.test.ts src/frontend/src/components/status-chip.tsx src/frontend/src/components/plate-field.tsx
git commit -m "feat(frontend): status mapping, status chip/dot, plate field"
```

### Task 11: KPI tile + gate KPIs

**Files:**
- Create: `src/frontend/src/components/kpi-tile.tsx`, `src/frontend/src/features/gate/gate-kpis.tsx`
- Test: `src/frontend/src/components/kpi-tile.test.tsx`

**Interfaces:**
- Consumes: `useGetStats`, `formatVnd`, `Skeleton`.
- Produces: `KpiTile` (props: `title, value, tile: 'blue'|'purple'|'mint'|'peri', delta?, loading?`). `GateKpis` reading `/stats`.

- [ ] **Step 1: Write the failing test**

`kpi-tile.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { KpiTile } from "./kpi-tile";

test("renders value and delta; skeleton when loading", () => {
  const { rerender } = render(<KpiTile title="Đang trong bãi" value="12" tile="blue" delta={5} />);
  expect(screen.getByText("Đang trong bãi")).toBeInTheDocument();
  expect(screen.getByText("12")).toBeInTheDocument();
  rerender(<KpiTile title="X" value="0" tile="blue" loading />);
  expect(screen.queryByText("0")).toBeNull();
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- kpi-tile`
Expected: FAIL.

- [ ] **Step 3: Write `kpi-tile.tsx`**

```tsx
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";

const TILE: Record<string, string> = {
  blue: "bg-tile-blue", purple: "bg-tile-purple", mint: "bg-tile-mint", peri: "bg-tile-peri",
};

export function KpiTile({
  title, value, tile, delta, loading = false,
}: {
  title: string; value: string; tile: "blue" | "purple" | "mint" | "peri";
  delta?: number; loading?: boolean;
}) {
  return (
    <div className={cn("rounded-[var(--radius-card)] p-5", TILE[tile])}>
      <p className="text-[13px] text-[#1c1c1c]/70">{title}</p>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-20" />
      ) : (
        <div className="mt-2 flex items-end justify-between">
          <span className="tnum text-2xl font-semibold text-[#1c1c1c]">{value}</span>
          {delta !== undefined && (
            <span className={cn("flex items-center gap-0.5 text-[13px]", delta >= 0 ? "text-st-green" : "text-st-red")}>
              {delta >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {Math.abs(delta)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}
```

Note: pastel tiles keep dark ink text intentionally (SnowUI) even in dark mode where the tile stays pastel; the neutral tiles switch to `--surface` via the token.

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- kpi-tile`
Expected: PASS.

- [ ] **Step 5: Write `gate-kpis.tsx`**

```tsx
import { useGetStats } from "@/api/generated/stats/stats";
import { KpiTile } from "@/components/kpi-tile";
import { formatVnd } from "@/lib/format";

export function GateKpis() {
  const { data, isLoading } = useGetStats();
  const s = (data ?? {}) as { in_lot?: number; entries?: number; exits?: number; revenue?: number };
  return (
    <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
      <KpiTile title="Đang trong bãi" value={String(s.in_lot ?? 0)} tile="blue" loading={isLoading} />
      <KpiTile title="Vào hôm nay" value={String(s.entries ?? 0)} tile="peri" loading={isLoading} />
      <KpiTile title="Ra hôm nay" value={String(s.exits ?? 0)} tile="mint" loading={isLoading} />
      <KpiTile title="Doanh thu" value={formatVnd(s.revenue ?? 0)} tile="purple" loading={isLoading} />
    </div>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/components/kpi-tile.tsx src/frontend/src/components/kpi-tile.test.tsx src/frontend/src/features/gate/gate-kpis.tsx
git commit -m "feat(frontend): KPI tile + gate KPIs"
```

### Task 12: Gate decision panel (four review_state) + manual override + capture panel

**Files:**
- Create: `src/frontend/src/features/gate/decision-panel.tsx`, `gate-capture.tsx`, `src/frontend/src/lib/image-blob.ts`
- Modify: `src/frontend/src/features/gate/gate-page.tsx`
- Test: `src/frontend/src/features/gate/decision-panel.test.tsx`

**Interfaces:**
- Consumes: `useConfirmEntry`, `useConfirmExit`, `useManualSession`, `usePatchPlate`, `useGetToggles`, `GateCapture` (from Task 13 type; declare the type inline in `decision-panel.tsx` props to avoid a hard dependency, matching the shared `GateCapture` shape), `PlateField`, `StatusChip`, `reviewStateMeta`, sonner `toast`, `formatVnd`.
- Produces: `DecisionPanel` (props: `capture: GateCapture; direction: 'in'|'out'; onDone(): void`). Renders one of four states, plus always-visible manual override button and plate field. `GateCapture` type is defined in Task 13 and imported here; if Task 12 runs first, define the same type locally and re-export from Task 13.

Decision logic (render strictly by `review_state`; do not compute thresholds):
- `confident`: entry -> `useConfirmEntry({data:{reading_id}})`; exit -> `useConfirmExit({data:{reading_id}})`, if `outcome` ok show provisional fee then close.
- `needs_review`: plate field highlighted; edit -> `usePatchPlate({readingId, data:{plate_text}})`; exit -> `useConfirmExit`; if `candidates` non-empty, show `SessionBrief` list to pick, then `useConfirmExit({data:{reading_id, session_id}})`.
- `disputed`: no candidates; show entry+exit images side by side (`image-blob`), manual fee entry, `useDisputeSession` then resolve.
- `manual`: force plate + vehicle_group; `useManualSession({data:{action, plate_text, vehicle_group, session_id?}})`.

- [ ] **Step 1: Write `image-blob.ts`**

```ts
import { AXIOS_INSTANCE } from "@/api/axios-instance";

// Authed blob fetch for /images/{id}. Each call is audited server-side (privacy).
export async function fetchImageObjectUrl(imageId: number): Promise<string> {
  const res = await AXIOS_INSTANCE.get(`/images/${imageId}`, { responseType: "blob" });
  return URL.createObjectURL(res.data as Blob);
}
```

- [ ] **Step 2: Write the failing test (review_state -> action button)**

`decision-panel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionPanel } from "./decision-panel";

const confirmEntry = vi.fn().mockResolvedValue({ id: 1, status: "in_lot" });
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: confirmEntry, isPending: false }),
  useConfirmExit: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useManualSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({
  usePatchPlate: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }),
}));

const base = { reading_id: 7, capture_id: "c1", direction: "in", review_state: "confident", plate_text: "51F-123" };

test("confident IN shows confirm entry and calls API", async () => {
  render(<DecisionPanel capture={base as any} direction="in" onDone={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận VÀO/i }));
  expect(confirmEntry).toHaveBeenCalledWith({ data: { reading_id: 7 } });
});

test("manual state always shows full manual entry button", () => {
  render(<DecisionPanel capture={{ ...base, review_state: "manual" } as any} direction="in" onDone={() => {}} />);
  expect(screen.getByRole("button", { name: /Nhập tay hoàn toàn/i })).toBeInTheDocument();
});
```

- [ ] **Step 3: Run to verify fail**

Run: `npm run test -- decision-panel`
Expected: FAIL — stub only.

- [ ] **Step 4: Implement `decision-panel.tsx`**

```tsx
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useConfirmEntry, useConfirmExit, useManualSession } from "@/api/generated/sessions/sessions";
import { usePatchPlate } from "@/api/generated/readings/readings";
import { useGetToggles } from "@/api/generated/config/config";
import type { GateCapture } from "./use-gate-socket";
import { PlateField } from "@/components/plate-field";
import { StatusChip } from "@/components/status-chip";
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/lib/format";

export function DecisionPanel({
  capture, direction, onDone,
}: { capture: GateCapture; direction: "in" | "out"; onDone: () => void }) {
  const { data: toggles } = useGetToggles();
  const forceManual = toggles ? !toggles.read_plate : false;
  const state = forceManual ? "manual" : capture.review_state;

  const [plate, setPlate] = useState(capture.plate_text ?? "");
  useEffect(() => setPlate(capture.plate_text ?? ""), [capture.reading_id, capture.plate_text]);

  const confirmEntry = useConfirmEntry();
  const confirmExit = useConfirmExit();
  const manual = useManualSession();
  const patchPlate = usePatchPlate();
  const [candidates, setCandidates] = useState<{ id: number; plate_text?: string | null }[]>([]);

  const savePlate = async () => {
    if (!plate.trim()) return;
    await patchPlate.mutateAsync({ readingId: capture.reading_id, data: { plate_text: plate.trim() } });
    toast.success("Đã cập nhật biển số");
  };

  const doEntry = async () => {
    await confirmEntry.mutateAsync({ data: { reading_id: capture.reading_id } });
    toast.success("Đã xác nhận VÀO");
    onDone();
  };

  const doExit = async (sessionId?: number) => {
    const res = await confirmExit.mutateAsync({
      data: { reading_id: capture.reading_id, ...(sessionId ? { session_id: sessionId } : {}) },
    });
    if (res.candidates && res.candidates.length > 0 && !sessionId) {
      setCandidates(res.candidates);
      return;
    }
    const fee = res.session?.fee_amount;
    toast.success(fee != null ? `Ra: phí ${formatVnd(fee)}` : "Đã xác nhận RA");
    onDone();
  };

  const doManual = async () => {
    await manual.mutateAsync({
      data: {
        action: direction === "in" ? "entry" : "exit",
        plate_text: plate.trim() || undefined,
        vehicle_group: capture.vehicle_group ?? undefined,
      },
    });
    toast.success("Đã ghi nhận nhập tay");
    onDone();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <StatusChip kind="review" value={state} />
        {capture.duplicate && <span className="text-[13px] text-st-amber">Cảnh báo: biển trùng phiên trong bãi</span>}
      </div>

      {capture.plate_valid === false && (
        <p className="text-[13px] text-st-amber">Cảnh báo: biển sai định dạng (vẫn cho xác nhận)</p>
      )}

      <PlateField value={plate} onChange={setPlate} size="lg" highlight={state === "needs_review"} />

      {state === "needs_review" && (
        <Button variant="outline" onClick={savePlate}>Lưu biển đã sửa</Button>
      )}

      {candidates.length > 0 ? (
        <div className="space-y-2">
          <p className="text-sm font-medium">Chọn phiên để nối</p>
          {candidates.map((c) => (
            <Button key={c.id} variant="outline" className="w-full justify-start" onClick={() => doExit(c.id)}>
              #{c.id} — {c.plate_text ?? "?"}
            </Button>
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {state !== "manual" && direction === "in" && (
            <Button className="h-11 min-w-[44px]" onClick={doEntry}>Xác nhận VÀO</Button>
          )}
          {state !== "manual" && direction === "out" && (
            <Button className="h-11 min-w-[44px]" onClick={() => doExit()}>Xác nhận RA</Button>
          )}
        </div>
      )}

      {/* Disputed: evidence review + manual fee handled in dispute-panel (Task 15); on gate, route to sessions. */}

      {/* Always reachable */}
      <div className="border-t border-line pt-3">
        <Button variant="secondary" className="h-11" onClick={doManual}>
          Nhập tay hoàn toàn
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run to verify pass**

Run: `npm run test -- decision-panel`
Expected: PASS.

- [ ] **Step 6: Implement `gate-capture.tsx`**

```tsx
import { useEffect, useState } from "react";
import type { GateCapture } from "./use-gate-socket";
import { fetchImageObjectUrl } from "@/lib/image-blob";
import { SurfaceCard } from "@/components/surface-card";

function Chip({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <span className="rounded-full bg-bg px-2.5 py-1 text-[13px] text-ink border border-line">
      {label}: {value}
    </span>
  );
}

export function GateCaptureView({ capture }: { capture: GateCapture | null }) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    if (capture?.image_asset_id) {
      fetchImageObjectUrl(capture.image_asset_id).then((u) => { url = u; setImgUrl(u); }).catch(() => setImgUrl(null));
    } else setImgUrl(null);
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [capture?.image_asset_id]);

  return (
    <SurfaceCard variant="white" className="space-y-3">
      <div className="flex aspect-video items-center justify-center overflow-hidden rounded-[var(--radius-control)] bg-surface">
        {imgUrl ? <img src={imgUrl} alt="Khung camera" className="h-full w-full object-cover" /> : <span className="text-muted">Chờ ảnh</span>}
      </div>
      <div className="flex flex-wrap gap-2">
        <Chip label="Loại xe" value={capture?.vehicle_type} />
        <Chip label="Nhóm phí" value={capture?.vehicle_group} />
        <Chip label="Màu biển" value={capture?.color} />
      </div>
    </SurfaceCard>
  );
}
```

- [ ] **Step 7: Assemble `gate-page.tsx` (partial — realtime wired in Task 13)**

```tsx
import { useState } from "react";
import { GateKpis } from "./gate-kpis";
import { GateCaptureView } from "./gate-capture";
import { DecisionPanel } from "./decision-panel";
import { SurfaceCard } from "@/components/surface-card";
import { Button } from "@/components/ui/button";
import { useGateSocket } from "./use-gate-socket";
import { EmptyState } from "@/components/empty-state";

export function GatePage() {
  const { capture } = useGateSocket();
  const [direction, setDirection] = useState<"in" | "out">("in");
  return (
    <div className="space-y-[18px]">
      <GateKpis />
      <div className="flex gap-2">
        <Button variant={direction === "in" ? "default" : "outline"} className="h-11" onClick={() => setDirection("in")}>Hướng VÀO</Button>
        <Button variant={direction === "out" ? "default" : "outline"} className="h-11" onClick={() => setDirection("out")}>Hướng RA</Button>
      </div>
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
        <GateCaptureView capture={capture} />
        <SurfaceCard variant="white">
          {capture ? (
            <DecisionPanel capture={capture} direction={direction} onDone={() => {}} />
          ) : (
            <EmptyState title="Chưa có lượt chụp" hint="Đang chờ sự kiện từ cổng" />
          )}
        </SurfaceCard>
      </div>
    </div>
  );
}
```

Note: `useGateSocket` stub is created in Task 13; to keep this compiling, create `use-gate-socket.ts` now with the `GateCapture` type export and a temporary `useGateSocket` returning `{ capture: null, events: [], connected: false, degraded: false }`, then flesh it out in Task 13.

- [ ] **Step 8: Commit**

```bash
git add src/frontend/src/features/gate src/frontend/src/lib/image-blob.ts
git commit -m "feat(frontend): gate decision panel (4 review states) + capture view + manual override"
```

---

## Phase 4 — Realtime

### Task 13: `useGateSocket` + polling fallback + idempotency

**Files:**
- Modify/complete: `src/frontend/src/features/gate/use-gate-socket.ts`, `src/frontend/src/features/gate/gate-events-rail.tsx`
- Modify: `src/frontend/src/features/gate/gate-page.tsx` (mount right rail + degraded banner)
- Test: `src/frontend/src/features/gate/use-gate-socket.test.ts`

**Interfaces:**
- Consumes: `WS /ws/gate` (base from `VITE_API_BASE`, http->ws), `latestCapture` raw fn (`@/api/generated/captures/captures`) for polling fallback, `getToken`.
- Produces: `GateCapture` type (shared shape) + `useGateSocket` (returns `{ capture, events, connected, degraded }`). Dedupes by `capture_id`. On WS error/close, falls back to polling `/captures/latest` every 3s and sets `degraded=true`.

- [ ] **Step 1: Write the failing test (idempotency + degraded)**

Test the pure reducer that ingests events. Extract a `ingestEvent(state, evt)` helper and test it:

`use-gate-socket.test.ts`:

```ts
import { ingestEvent, type GateState } from "./use-gate-socket";

const evt = (id: string) => ({
  reading_id: Number(id.slice(1)), capture_id: id, direction: "in",
  review_state: "confident", plate_text: "51F", vehicle_group: "car",
});

test("dedupes by capture_id and keeps newest first", () => {
  let s: GateState = { capture: null, events: [] };
  s = ingestEvent(s, evt("c1"));
  s = ingestEvent(s, evt("c2"));
  s = ingestEvent(s, evt("c1")); // duplicate
  expect(s.events.map((e) => e.capture_id)).toEqual(["c2", "c1"]);
  expect(s.capture?.capture_id).toBe("c1");
});

test("caps event history at 30", () => {
  let s: GateState = { capture: null, events: [] };
  for (let i = 0; i < 40; i++) s = ingestEvent(s, evt(`c${i}`));
  expect(s.events.length).toBe(30);
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- use-gate-socket`
Expected: FAIL — `ingestEvent` not exported.

- [ ] **Step 3: Implement `use-gate-socket.ts`**

```ts
import { useEffect, useRef, useState } from "react";
import { latestCapture } from "@/api/generated/captures/captures";

export type GateCapture = {
  reading_id: number;
  capture_id: string;
  direction: string;
  lane?: string | null;
  review_state: string;
  plate_text?: string | null;
  vehicle_group?: string | null;
  vehicle_type?: string | null;
  color?: string | null;
  plate_valid?: boolean | null;
  image_asset_id?: number | null;
  duplicate?: boolean;
};

export type GateState = { capture: GateCapture | null; events: GateCapture[] };

const MAX = 30;

export function ingestEvent(state: GateState, evt: GateCapture): GateState {
  if (state.events.some((e) => e.capture_id === evt.capture_id)) return state; // idempotent
  const events = [evt, ...state.events].slice(0, MAX);
  return { capture: evt, events };
}

function wsUrl(): string {
  const base = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE ?? "http://localhost:8000";
  return base.replace(/^http/, "ws") + "/ws/gate";
}

export function useGateSocket(opts?: { lane?: string }): GateState & { connected: boolean; degraded: boolean } {
  const [state, setState] = useState<GateState>({ capture: null, events: [] });
  const [connected, setConnected] = useState(false);
  const [degraded, setDegraded] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;

    const startPolling = () => {
      if (pollRef.current) return;
      setDegraded(true);
      pollRef.current = setInterval(async () => {
        try {
          const c = (await latestCapture(opts?.lane ? { lane: opts.lane } : undefined)) as GateCapture | null;
          if (c && c.capture_id) setState((s) => ingestEvent(s, c));
        } catch { /* keep polling */ }
      }, 3000);
    };
    const stopPolling = () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };

    try {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => { setConnected(true); setDegraded(false); stopPolling(); };
      ws.onmessage = (m) => {
        try {
          const evt = JSON.parse(m.data) as GateCapture;
          setState((s) => ingestEvent(s, evt));
        } catch { /* ignore malformed */ }
      };
      ws.onerror = () => { if (!closed) startPolling(); };
      ws.onclose = () => { setConnected(false); if (!closed) startPolling(); };
    } catch {
      startPolling();
    }

    return () => { closed = true; stopPolling(); ws?.close(); };
  }, [opts?.lane]);

  return { ...state, connected, degraded };
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- use-gate-socket`
Expected: PASS.

- [ ] **Step 5: Write `gate-events-rail.tsx`**

```tsx
import type { GateCapture } from "./use-gate-socket";
import { StatusDot } from "@/components/status-chip";
import { formatPlate } from "@/lib/format";

export function GateEventsRail({ events }: { events: GateCapture[] }) {
  if (events.length === 0) return <p className="text-[13px] text-muted">Chưa có sự kiện</p>;
  return (
    <ul className="space-y-2">
      {events.map((e) => (
        <li key={e.capture_id} className="flex items-center gap-2 text-[13px]">
          <StatusDot kind="review" value={e.review_state} />
          <span className="tnum font-medium">{formatPlate(e.plate_text)}</span>
          <span className="ml-auto text-muted">{e.direction === "in" ? "VÀO" : "RA"}</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 6: Wire right rail + degraded banner into `gate-page.tsx`**

Add: `const { capture, events, degraded } = useGateSocket();` and render, above the grid, a banner when `degraded`:

```tsx
{degraded && (
  <div role="status" className="rounded-[var(--radius-control)] bg-tile-peri px-4 py-2 text-[13px] text-[#1c1c1c]">
    Mất kết nối realtime. Đang dùng chế độ dự phòng (polling).
  </div>
)}
```

Because `AppShell` owns the layout, render the events feed inside the main column (a `SurfaceCard` titled "Sự kiện cổng") rather than the shell rail for MVP, or lift rail content via context. Simplest: place `<GateEventsRail events={events} />` inside a `SurfaceCard` in a third column on wide screens.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/features/gate
git commit -m "feat(frontend): gate realtime socket + polling fallback + events feed"
```

---

## Phase 5 — Sessions

### Task 14: DataTable + Sessions list (server pagination + filters)

**Files:**
- Create: `src/frontend/src/components/data-table.tsx`, `src/frontend/src/features/sessions/sessions-columns.tsx`
- Modify: `src/frontend/src/features/sessions/sessions-page.tsx`
- Test: `src/frontend/src/features/sessions/sessions-page.test.tsx`

**Interfaces:**
- Consumes: `useListSessions(params)`, `SessionOut`, TanStack Table, `StatusChip`, `formatVnd`, `formatDateTime`, `formatDuration`, `formatPlate`.
- Produces: generic `DataTable<T>` (props: `columns, data, loading, empty`), `sessionColumns` (ColumnDef array), `SessionsPage` with plate search (debounced), status filter, server pagination (limit/offset), pill pagination.

- [ ] **Step 1: Write the failing test**

`sessions-page.test.tsx` (mock hook):

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionsPage } from "./sessions-page";

vi.mock("@/api/generated/sessions/sessions", () => ({
  useListSessions: () => ({
    data: { total: 1, items: [{ id: 5, status: "completed", plate_text: "51F-123", vehicle_group: "car", entry_time: "2026-08-23T08:00:00Z", exit_time: "2026-08-23T09:00:00Z", fee_amount: 15000, match_flag: "exact" }] },
    isLoading: false,
  }),
}));

test("renders a session row with plate and status", () => {
  render(<MemoryRouter><SessionsPage /></MemoryRouter>);
  expect(screen.getByText("51F-123")).toBeInTheDocument();
  expect(screen.getByText("Hoàn tất")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- sessions-page`
Expected: FAIL — stub.

- [ ] **Step 3: Write `data-table.tsx`**

```tsx
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from "@tanstack/react-table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";

export function DataTable<T>({
  columns, data, loading = false, empty = "Không có dữ liệu",
}: { columns: ColumnDef<T, unknown>[]; data: T[]; loading?: boolean; empty?: string }) {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });
  if (loading) return <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}</div>;
  if (data.length === 0) return <EmptyState title={empty} />;
  return (
    <table className="w-full text-sm">
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id} className="border-b border-line text-left text-muted">
            {hg.headers.map((h) => (
              <th key={h.id} className="px-3 py-2 font-medium">
                {flexRender(h.column.columnDef.header, h.getContext())}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id} className="border-b border-line hover:bg-surface">
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id} className="px-3 py-2">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Write `sessions-columns.tsx`**

```tsx
import { Link } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import type { SessionOut } from "@/api/generated/model";
import { StatusChip } from "@/components/status-chip";
import { formatPlate, formatVnd, formatDateTime, formatDuration } from "@/lib/format";

export const sessionColumns: ColumnDef<SessionOut, unknown>[] = [
  { header: "Biển số", accessorKey: "plate_text",
    cell: ({ row }) => <Link to={`/sessions/${row.original.id}`} className="tnum font-medium">{formatPlate(row.original.plate_text)}</Link> },
  { header: "Nhóm xe", accessorKey: "vehicle_group", cell: ({ row }) => row.original.vehicle_group ?? "—" },
  { header: "Giờ vào", cell: ({ row }) => formatDateTime(row.original.entry_time) },
  { header: "Giờ ra", cell: ({ row }) => formatDateTime(row.original.exit_time) },
  { header: "Thời lượng", cell: ({ row }) => formatDuration(row.original.entry_time, row.original.exit_time) },
  { header: "Phí", cell: ({ row }) => <span className="tnum">{formatVnd(row.original.fee_amount)}</span> },
  { header: "Trạng thái", cell: ({ row }) => <StatusChip kind="session" value={row.original.status} /> },
  { header: "Khớp", cell: ({ row }) => row.original.match_flag ?? "—" },
];
```

- [ ] **Step 5: Write `sessions-page.tsx`**

```tsx
import { useMemo, useState } from "react";
import { useListSessions } from "@/api/generated/sessions/sessions";
import type { ListSessionsParams } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { sessionColumns } from "./sessions-columns";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SurfaceCard } from "@/components/surface-card";

const PAGE = 20;
const STATUSES = ["", "in_lot", "completed", "disputed", "pending_manual"];

export function SessionsPage() {
  const [plate, setPlate] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);

  const params: ListSessionsParams = useMemo(
    () => ({ plate: plate || null, status: status || null, limit: PAGE, offset }),
    [plate, status, offset],
  );
  const { data, isLoading } = useListSessions(params);
  const total = data?.total ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Input className="w-64" placeholder="Tra biển số" value={plate}
          onChange={(e) => { setPlate(e.target.value); setOffset(0); }} aria-label="Tra biển số" />
        <select className="h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm"
          value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }} aria-label="Lọc trạng thái">
          {STATUSES.map((s) => <option key={s} value={s}>{s || "Tất cả trạng thái"}</option>)}
        </select>
      </div>
      <SurfaceCard variant="white">
        <DataTable columns={sessionColumns} data={data?.items ?? []} loading={isLoading} empty="Chưa có phiên" />
      </SurfaceCard>
      <div className="flex items-center justify-end gap-2 text-sm">
        <Button variant="outline" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - PAGE))}>Trước</Button>
        <span className="tnum text-muted">{offset + 1}–{Math.min(offset + PAGE, total)} / {total}</span>
        <Button variant="outline" disabled={offset + PAGE >= total} onClick={() => setOffset((o) => o + PAGE)}>Sau</Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Run to verify pass**

Run: `npm run test -- sessions-page`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/components/data-table.tsx src/frontend/src/features/sessions
git commit -m "feat(frontend): sessions list with server pagination + filters"
```

### Task 15: Session detail + evidence images + dispute/resolve

**Files:**
- Create: `src/frontend/src/features/sessions/dispute-panel.tsx`
- Modify: `src/frontend/src/features/sessions/session-detail-page.tsx`
- Test: `src/frontend/src/features/sessions/session-detail-page.test.tsx`

**Interfaces:**
- Consumes: `useSessionDetail(id)`, `SessionDetail`, `useDisputeSession`, `useResolveSession`, `fetchImageObjectUrl`, `useParams`, `StatusChip`, formatters.
- Produces: `SessionDetailPage` showing plate/vehicle/entry-exit/fee/match/warning + entry/exit `ReadingBrief`. Evidence images loaded only on explicit "Xem ảnh bằng chứng" click (privacy note shown). `DisputePanel` for mark-disputed + manual-fee resolve.

- [ ] **Step 1: Write the failing test**

`session-detail-page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { SessionDetailPage } from "./session-detail-page";

vi.mock("@/api/generated/sessions/sessions", () => ({
  useSessionDetail: () => ({
    data: { id: 9, status: "completed", plate_text: "51F-123", vehicle_group: "car",
      entry_time: "2026-08-23T08:00:00Z", exit_time: "2026-08-23T09:00:00Z", fee_amount: 15000, match_flag: "exact",
      entry_reading: { id: 1, review_state: "confident", plate_text: "51F-123", image_asset_id: 11 },
      exit_reading: { id: 2, review_state: "confident", plate_text: "51F-123", image_asset_id: 12 } },
    isLoading: false,
  }),
  useDisputeSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useResolveSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

test("shows detail fields and retention notice", () => {
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes><Route path="/sessions/:id" element={<SessionDetailPage />} /></Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText("51F-123")).toBeInTheDocument();
  expect(screen.getByText(/30 ngày/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- session-detail-page`
Expected: FAIL — stub.

- [ ] **Step 3: Write `dispute-panel.tsx`**

```tsx
import { useState } from "react";
import { toast } from "sonner";
import { useDisputeSession, useResolveSession } from "@/api/generated/sessions/sessions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function DisputePanel({ sessionId, onChanged }: { sessionId: number; onChanged: () => void }) {
  const dispute = useDisputeSession();
  const resolve = useResolveSession();
  const [fee, setFee] = useState("");

  return (
    <div className="space-y-3 border-t border-line pt-4">
      <p className="text-sm font-semibold">Xử lý tranh chấp</p>
      <Button variant="outline" onClick={async () => { await dispute.mutateAsync({ sessionId }); toast.success("Đã chuyển tranh chấp"); onChanged(); }}>
        Đánh dấu tranh chấp
      </Button>
      <div className="flex items-end gap-2">
        <div className="space-y-1.5">
          <Label htmlFor="fee">Phí nhập tay</Label>
          <Input id="fee" className="tnum w-40" inputMode="numeric" value={fee} onChange={(e) => setFee(e.target.value.replace(/\D/g, ""))} />
        </div>
        <Button
          className="bg-st-red text-white"
          disabled={!fee}
          onClick={async () => { await resolve.mutateAsync({ sessionId, data: { fee_amount: Number(fee) } }); toast.success("Đã chốt phí"); onChanged(); }}
        >
          Chốt phí và giải quyết
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write `session-detail-page.tsx`**

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useSessionDetail } from "@/api/generated/sessions/sessions";
import { StatusChip } from "@/components/status-chip";
import { SurfaceCard } from "@/components/surface-card";
import { Button } from "@/components/ui/button";
import { DisputePanel } from "./dispute-panel";
import { fetchImageObjectUrl } from "@/lib/image-blob";
import { formatPlate, formatVnd, formatDateTime, formatDuration } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><dt className="text-[13px] text-muted">{label}</dt><dd className="tnum text-sm font-medium">{children}</dd></div>;
}

function Evidence({ imageId }: { imageId?: number | null }) {
  const [url, setUrl] = useState<string | null>(null);
  if (!imageId) return <span className="text-muted">Không có ảnh</span>;
  if (!url) return <Button variant="outline" size="sm" onClick={async () => setUrl(await fetchImageObjectUrl(imageId))}>Xem ảnh bằng chứng</Button>;
  return <img src={url} alt="Ảnh bằng chứng" className="max-h-48 rounded-[var(--radius-control)]" />;
}

export function SessionDetailPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const { data, isLoading, refetch } = useSessionDetail(sessionId);

  if (isLoading) return <EmptyState title="Đang tải..." />;
  if (!data) return <EmptyState title="Không tìm thấy phiên" />;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold tnum">{formatPlate(data.plate_text)}</h1>
        <StatusChip kind="session" value={data.status} />
      </div>
      <SurfaceCard variant="white">
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Field label="Nhóm xe">{data.vehicle_group ?? "—"}</Field>
          <Field label="Loại xe">{data.vehicle_type ?? "—"}</Field>
          <Field label="Giờ vào">{formatDateTime(data.entry_time)}</Field>
          <Field label="Giờ ra">{formatDateTime(data.exit_time)}</Field>
          <Field label="Thời lượng">{formatDuration(data.entry_time, data.exit_time)}</Field>
          <Field label="Phí">{formatVnd(data.fee_amount)}</Field>
          <Field label="Khớp">{data.match_flag ?? "—"}</Field>
          <Field label="Cảnh báo">{data.warning ?? "—"}</Field>
        </dl>
      </SurfaceCard>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SurfaceCard variant="white" className="space-y-2">
          <p className="text-sm font-semibold">Ảnh vào</p>
          {data.entry_reading && <StatusChip kind="review" value={data.entry_reading.review_state ?? "confident"} />}
          <Evidence imageId={data.entry_reading?.image_asset_id} />
        </SurfaceCard>
        <SurfaceCard variant="white" className="space-y-2">
          <p className="text-sm font-semibold">Ảnh ra</p>
          {data.exit_reading && <StatusChip kind="review" value={data.exit_reading.review_state ?? "confident"} />}
          <Evidence imageId={data.exit_reading?.image_asset_id} />
        </SurfaceCard>
      </div>

      <p className="text-[13px] text-muted">Việc truy cập ảnh bằng chứng được hệ thống ghi lại (audit). Dữ liệu tự xóa sau 30 ngày kể từ khi xe ra.</p>

      <SurfaceCard variant="surface">
        <DisputePanel sessionId={sessionId} onChanged={() => refetch()} />
      </SurfaceCard>
    </div>
  );
}
```

- [ ] **Step 5: Run to verify pass**

Run: `npm run test -- session-detail-page`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/features/sessions
git commit -m "feat(frontend): session detail + evidence images + dispute/resolve"
```

---

## Phase 6 — Stats

### Task 16: Stats KPIs + charts + a11y tables + CSV export

**Files:**
- Create: `src/frontend/src/components/charts/{line-chart,bar-chart,donut-chart}.tsx`, `src/frontend/src/features/stats/stats-export.ts`
- Modify: `src/frontend/src/features/stats/stats-page.tsx`
- Test: `src/frontend/src/features/stats/stats-page.test.tsx`

**Interfaces:**
- Consumes: `useGetStats(params)`, Recharts, `getRole`, `getToken`, `AXIOS_INSTANCE`, `formatVnd`.
- Produces: three chart components (props: `data`, series keys), `downloadStatsCsv(from?, to?)` (authed blob GET `/stats/export`, triggers browser download), `StatsPage` with date range + KPIs + charts + a11y number tables + admin-only CSV button.

Note: `/stats` returns `{in_lot, entries, exits, revenue}` (summary only). Time-series for line/bar charts is not in the summary contract; the CSV export path (`/stats/export`, daily rows) is the only time-series source. For MVP charts, derive the bar/line from the CSV daily rows fetched via `downloadStatsCsv`-style parse, or render charts from the summary as single-period bars. Keep charts defensive: render an empty state when no series data.

- [ ] **Step 1: Write `stats-export.ts`**

```ts
import { AXIOS_INSTANCE } from "@/api/axios-instance";

export async function downloadStatsCsv(from?: string, to?: string): Promise<void> {
  const res = await AXIOS_INSTANCE.get("/stats/export", {
    params: { from: from || undefined, to: to || undefined },
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "stats.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export type DailyRow = { date: string; entries: number; exits: number; revenue: number };

export async function fetchDailyRows(from?: string, to?: string): Promise<DailyRow[]> {
  const res = await AXIOS_INSTANCE.get("/stats/export", {
    params: { from: from || undefined, to: to || undefined },
    responseType: "text",
  });
  const lines = String(res.data).trim().split("\n").slice(1); // drop header
  return lines.filter(Boolean).map((l) => {
    const [date, entries, exits, revenue] = l.split(",");
    return { date, entries: Number(entries), exits: Number(exits), revenue: Number(revenue) };
  });
}
```

- [ ] **Step 2: Write the three chart components**

`charts/line-chart.tsx`:

```tsx
import { ResponsiveContainer, LineChart as RLine, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";
import type { DailyRow } from "@/features/stats/stats-export";
import { EmptyState } from "@/components/empty-state";

export function TrafficLineChart({ data }: { data: DailyRow[] }) {
  if (data.length === 0) return <EmptyState title="Chưa có dữ liệu lưu lượng" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <RLine data={data}>
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis dataKey="date" stroke="var(--muted)" fontSize={12} />
        <YAxis stroke="var(--muted)" fontSize={12} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="entries" name="Vào" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="exits" name="Ra" stroke="var(--chart-3)" strokeWidth={2} dot={false} />
      </RLine>
    </ResponsiveContainer>
  );
}
```

`charts/bar-chart.tsx`:

```tsx
import { ResponsiveContainer, BarChart as RBar, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import type { DailyRow } from "@/features/stats/stats-export";
import { EmptyState } from "@/components/empty-state";

export function RevenueBarChart({ data }: { data: DailyRow[] }) {
  if (data.length === 0) return <EmptyState title="Chưa có dữ liệu doanh thu" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <RBar data={data}>
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis dataKey="date" stroke="var(--muted)" fontSize={12} />
        <YAxis stroke="var(--muted)" fontSize={12} />
        <Tooltip />
        <Bar dataKey="revenue" name="Doanh thu" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
      </RBar>
    </ResponsiveContainer>
  );
}
```

`charts/donut-chart.tsx`:

```tsx
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import { EmptyState } from "@/components/empty-state";

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

export function GroupDonutChart({ data }: { data: { name: string; value: number }[] }) {
  if (data.length === 0) return <EmptyState title="Chưa có cơ cấu nhóm xe" />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 3: Write the failing test**

`stats-page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { StatsPage } from "./stats-page";

vi.mock("@/api/generated/stats/stats", () => ({
  useGetStats: () => ({ data: { in_lot: 12, entries: 40, exits: 28, revenue: 420000 }, isLoading: false }),
}));
vi.mock("@/lib/auth", async (orig) => ({ ...(await orig<typeof import("@/lib/auth")>()), getRole: () => "staff" }));

test("staff sees KPIs but not export button", () => {
  render(<StatsPage />);
  expect(screen.getByText("420.000 ₫")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Xuất CSV/i })).toBeNull();
});
```

(If `formatVnd(420000)` renders a slightly different currency string in the test's ICU build, align the expected string with a one-off print.)

- [ ] **Step 4: Run to verify fail**

Run: `npm run test -- stats-page`
Expected: FAIL — stub.

- [ ] **Step 5: Write `stats-page.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useGetStats } from "@/api/generated/stats/stats";
import { KpiTile } from "@/components/kpi-tile";
import { SurfaceCard } from "@/components/surface-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getRole } from "@/lib/auth";
import { formatVnd } from "@/lib/format";
import { downloadStatsCsv, fetchDailyRows, type DailyRow } from "./stats-export";
import { TrafficLineChart } from "@/components/charts/line-chart";
import { RevenueBarChart } from "@/components/charts/bar-chart";
import { GroupDonutChart } from "@/components/charts/donut-chart";

export function StatsPage() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const { data, isLoading } = useGetStats(from || to ? { from: from || null, to: to || null } : undefined);
  const s = (data ?? {}) as { in_lot?: number; entries?: number; exits?: number; revenue?: number };
  const isAdmin = getRole() === "admin";
  const [rows, setRows] = useState<DailyRow[]>([]);

  useEffect(() => { fetchDailyRows(from, to).then(setRows).catch(() => setRows([])); }, [from, to]);

  return (
    <div className="space-y-[18px]">
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-[13px] text-muted">Từ<Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label className="text-[13px] text-muted">Đến<Input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
        {isAdmin && <Button className="ml-auto" onClick={() => downloadStatsCsv(from, to)}>Xuất CSV</Button>}
      </div>

      <div className="grid grid-cols-2 gap-[18px] lg:grid-cols-4">
        <KpiTile title="Đang trong bãi" value={String(s.in_lot ?? 0)} tile="blue" loading={isLoading} />
        <KpiTile title="Lưu lượng hôm nay" value={String(s.entries ?? 0)} tile="peri" loading={isLoading} />
        <KpiTile title="Doanh thu hôm nay" value={formatVnd(s.revenue ?? 0)} tile="mint" loading={isLoading} />
        <KpiTile title="Ra hôm nay" value={String(s.exits ?? 0)} tile="purple" loading={isLoading} />
      </div>

      <SurfaceCard variant="white">
        <h2 className="mb-3 text-sm font-semibold">Lưu lượng theo ngày</h2>
        <TrafficLineChart data={rows} />
        <table className="sr-only"><caption>Bảng số lưu lượng</caption>
          <thead><tr><th>Ngày</th><th>Vào</th><th>Ra</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.date}><td>{r.date}</td><td>{r.entries}</td><td>{r.exits}</td></tr>)}</tbody>
        </table>
      </SurfaceCard>

      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
        <SurfaceCard variant="white">
          <h2 className="mb-3 text-sm font-semibold">Doanh thu theo ngày</h2>
          <RevenueBarChart data={rows} />
        </SurfaceCard>
        <SurfaceCard variant="white">
          <h2 className="mb-3 text-sm font-semibold">Cơ cấu nhóm xe</h2>
          <GroupDonutChart data={[]} />
        </SurfaceCard>
      </div>
    </div>
  );
}
```

Note: donut has no group-breakdown endpoint in the contract; render its empty state for MVP (documented gap — needs a `/stats` group breakdown to populate).

- [ ] **Step 6: Run to verify pass**

Run: `npm run test -- stats-page`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/components/charts src/frontend/src/features/stats
git commit -m "feat(frontend): stats KPIs, charts, a11y tables, CSV export"
```

---

## Phase 7 — Config (admin only)

### Task 17: Config tabs (price rules, users, lanes, toggles)

**Files:**
- Create: `src/frontend/src/features/config/{price-rules-tab,users-tab,lanes-tab,toggles-tab}.tsx`
- Modify: `src/frontend/src/features/config/config-page.tsx`
- Test: `src/frontend/src/features/config/toggles-tab.test.tsx`

**Interfaces:**
- Consumes: config + users hooks (`useListPriceRules`, `useCreatePriceRule`, `useUpdatePriceRule`, `useListLanes`, `useCreateLane`, `useUpdateLane`, `useGetToggles`, `useUpdateToggles`, `useListUsers`, `useCreateUser`, `useUpdateUser`), `Tabs`, `Switch`, `DataTable`, RHF+Zod, `Dialog` (confirm before destructive), sonner.
- Produces: `ConfigPage` with four tabs. Destructive actions styled `--st-red` and behind a confirm dialog. Retention notice shown.

- [ ] **Step 1: Write the failing test (toggles)**

`toggles-tab.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TogglesTab } from "./toggles-tab";

const mutateAsync = vi.fn().mockResolvedValue({ read_plate: false, plate_color: true, vehicle_class: true });
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true }, isLoading: false }),
  useUpdateToggles: () => ({ mutateAsync, isPending: false }),
}));

test("toggling read_plate calls update", async () => {
  render(<TogglesTab />);
  await userEvent.click(screen.getByLabelText(/Đọc biển số/i));
  expect(mutateAsync).toHaveBeenCalledWith({ data: { read_plate: false } });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npm run test -- toggles-tab`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `toggles-tab.tsx`**

```tsx
import { toast } from "sonner";
import { useGetToggles, useUpdateToggles } from "@/api/generated/config/config";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { SurfaceCard } from "@/components/surface-card";

export function TogglesTab() {
  const { data } = useGetToggles();
  const update = useUpdateToggles();
  const set = async (key: "read_plate" | "plate_color" | "vehicle_class", value: boolean) => {
    await update.mutateAsync({ data: { [key]: value } });
    toast.success("Đã cập nhật cấu hình");
  };
  const t = data ?? { read_plate: true, plate_color: true, vehicle_class: true };
  const Row = ({ id, label, checked, hint }: { id: "read_plate" | "plate_color" | "vehicle_class"; label: string; checked: boolean; hint?: string }) => (
    <div className="flex items-center justify-between py-3">
      <div><Label htmlFor={id}>{label}</Label>{hint && <p className="text-[13px] text-muted">{hint}</p>}</div>
      <Switch id={id} checked={checked} onCheckedChange={(v) => set(id, v)} />
    </div>
  );
  return (
    <SurfaceCard variant="white" className="divide-y divide-line">
      <Row id="read_plate" label="Đọc biển số (read_plate)" checked={t.read_plate} hint="Tắt thì màn cổng ép nhập tay" />
      <Row id="plate_color" label="Nhận màu biển (plate_color)" checked={t.plate_color} />
      <Row id="vehicle_class" label="Phân loại xe (vehicle_class)" checked={t.vehicle_class} />
    </SurfaceCard>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test -- toggles-tab`
Expected: PASS.

- [ ] **Step 5: Write `price-rules-tab.tsx`**

```tsx
import { toast } from "sonner";
import { useListPriceRules, useUpdatePriceRule } from "@/api/generated/config/config";
import type { PriceRuleOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import type { ColumnDef } from "@tanstack/react-table";
import { formatVnd } from "@/lib/format";

export function PriceRulesTab() {
  const { data, isLoading } = useListPriceRules();
  const update = useUpdatePriceRule();
  const cols: ColumnDef<PriceRuleOut, unknown>[] = [
    { header: "Nhóm", accessorKey: "vehicle_group" },
    { header: "Chế độ", accessorKey: "mode" },
    { header: "Đơn giá", cell: ({ row }) => <span className="tnum">{formatVnd(row.original.unit_price)}</span> },
    { header: "Block (phút)", cell: ({ row }) => row.original.block_minutes ?? "—" },
    { header: "Kích hoạt", cell: ({ row }) => (
      <Button variant="outline" size="sm" onClick={async () => { await update.mutateAsync({ ruleId: row.original.id, data: { active: !row.original.active } }); toast.success("Đã cập nhật"); }}>
        {row.original.active ? "Bật" : "Tắt"}
      </Button>
    ) },
  ];
  return <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có bảng giá" />;
}
```

- [ ] **Step 6: Write `lanes-tab.tsx`**

```tsx
import { toast } from "sonner";
import { useListLanes, useUpdateLane } from "@/api/generated/config/config";
import type { LaneOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import type { ColumnDef } from "@tanstack/react-table";

export function LanesTab() {
  const { data, isLoading } = useListLanes();
  const update = useUpdateLane();
  const cols: ColumnDef<LaneOut, unknown>[] = [
    { header: "Tên", accessorKey: "name" },
    { header: "RTSP", cell: ({ row }) => row.original.rtsp_url ?? "—" },
    { header: "Kích hoạt", cell: ({ row }) => (
      <Button variant="outline" size="sm" onClick={async () => { await update.mutateAsync({ laneId: row.original.id, data: { active: !row.original.active } }); toast.success("Đã cập nhật"); }}>
        {row.original.active ? "Bật" : "Tắt"}
      </Button>
    ) },
  ];
  return <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có lane" />;
}
```

- [ ] **Step 7: Write `users-tab.tsx`**

```tsx
import { toast } from "sonner";
import { useListUsers, useUpdateUser } from "@/api/generated/users/users";
import type { UserOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import type { ColumnDef } from "@tanstack/react-table";

export function UsersTab() {
  const { data, isLoading } = useListUsers();
  const update = useUpdateUser();
  const cols: ColumnDef<UserOut, unknown>[] = [
    { header: "Tên đăng nhập", accessorKey: "username" },
    { header: "Vai", accessorKey: "role" },
    { header: "Kích hoạt", cell: ({ row }) => (
      <Button variant="outline" size="sm" onClick={async () => { await update.mutateAsync({ userId: row.original.id, data: { active: !row.original.active } }); toast.success("Đã cập nhật"); }}>
        {row.original.active ? "Bật" : "Tắt"}
      </Button>
    ) },
  ];
  return <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có tài khoản" />;
}
```

- [ ] **Step 8: Write `config-page.tsx`**

```tsx
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
        <TabsContent value="price"><SurfaceCard variant="white"><PriceRulesTab /></SurfaceCard></TabsContent>
        <TabsContent value="users"><SurfaceCard variant="white"><UsersTab /></SurfaceCard></TabsContent>
        <TabsContent value="lanes"><SurfaceCard variant="white"><LanesTab /></SurfaceCard></TabsContent>
        <TabsContent value="toggles"><TogglesTab /></TabsContent>
      </Tabs>
      <p className="text-[13px] text-muted">Dữ liệu phiên tự xóa sau 30 ngày kể từ khi xe ra (tuân thủ Luật Bảo vệ dữ liệu cá nhân).</p>
    </div>
  );
}
```

- [ ] **Step 9: Commit**

```bash
git add src/frontend/src/features/config
git commit -m "feat(frontend): config tabs (price, users, lanes, toggles)"
```

---

## Phase 8 — Accessibility pass + containerization

### Task 18: a11y/contrast review + Dockerfile + nginx

**Files:**
- Create: `src/frontend/Dockerfile`, `src/frontend/nginx.conf`, `src/frontend/.dockerignore`
- Modify (as needed): components flagged during a11y review
- Modify: `compose.yaml` only if the build arg for `VITE_API_BASE` must be passed

**Interfaces:**
- Produces: static build served by nginx with SPA fallback. `compose --profile frontend up` serves at `:5173`.

- [ ] **Step 1: a11y checklist pass**

Verify by inspection + keyboard walkthrough on `npm run dev`:
- Every icon-only button has `aria-label` (Topbar toggle/logout, plate show/hide, sidebar collapse). Fix any missing.
- Focus ring visible on buttons, inputs, links, tabs, switches in both themes. Add `focus-visible:ring-2 focus-visible:ring-primary` where shadcn default is insufficient.
- Status always has icon+label (StatusChip/StatusDot already do). Confirm no color-only signals remain.
- Toasts: sonner is `aria-live` polite by default — confirm not `assertive`.
- Gate buttons `h-11` (44px). Confirm.
- Add `@media (prefers-reduced-motion: reduce) { *, ::before, ::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }` to `tokens.css` base layer.

- [ ] **Step 2: Contrast check (dark independently)**

Manually verify with browser devtools contrast on: `--muted` text on `--bg` and on `--surface`, status chip text on its tint, KPI ink on pastel tiles — both themes. Where a token fails 4.5:1, darken/lighten the token value in `tokens.css` (dark mode checked separately, not inferred from light).

- [ ] **Step 3: `nginx.conf`**

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;
  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

- [ ] **Step 4: `Dockerfile` (multi-stage; VITE_API_BASE as build arg)**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

- [ ] **Step 5: `.dockerignore`**

```
node_modules
dist
.git
```

- [ ] **Step 6: Build the image via compose**

Run: `podman compose --profile frontend build frontend`
Expected: image builds; `dist` produced. (`compose.yaml` already defines the `frontend` service mapping `5173:80`, profile `frontend`, `build: ./src/frontend`.)

- [ ] **Step 7: Full verification**

Run: `cd src/frontend && npm run test && npm run build`
Expected: all tests pass; production build succeeds.

- [ ] **Step 8: Commit**

```bash
git add src/frontend/Dockerfile src/frontend/nginx.conf src/frontend/.dockerignore src/frontend/src
git commit -m "feat(frontend): a11y pass + nginx container"
```

---

## Verification (end-to-end)

1. **Backend up:** `podman compose up -d db backend` (seeds admin per existing scripts). Confirm `GET http://localhost:8000/health` OK.
2. **Regenerate client** (after Task 1): `cd src/backend && python -m scripts.export_openapi > ../frontend/openapi.json && cd ../frontend && npm run gen:api`.
3. **Frontend dev:** `cd src/frontend && npm run dev`, open `http://localhost:5173` (or Vite's port in dev). Login with the seeded admin.
4. **Gate realtime:** run the edge simulator (`src/backend/scripts/simulate_edge.py`) to POST a capture; confirm the gate screen shows the capture (image, meta chips), the decision panel matches `review_state`, and the events feed updates. Kill the WS to confirm the degraded banner + polling fallback.
5. **Sessions:** confirm an entry, then an exit; verify the row appears in `/sessions`, detail loads, evidence image loads only on click.
6. **Stats:** verify KPIs match backend; as admin, "Xuất CSV" downloads `stats.csv`.
7. **Config:** as admin, toggle `read_plate` off; confirm the gate forces manual entry. As staff, confirm `/config` redirects to `/gate`.
8. **Tests:** `npm run test` (frontend) all green; `cd src/backend && pytest -q` still green (Task 1 didn't regress).
9. **Container:** `podman compose --profile frontend up --build frontend`; browse `http://localhost:5173`.

## Self-review notes (known contract gaps, in-scope decisions)

- **Realtime meta** now flows end-to-end after Task 1 (WS + `/captures/latest` enriched). Confirmed reconstructable from `PlateReading`.
- **Donut (vehicle-group mix)** has no backend breakdown endpoint; rendered as empty state. Populating it needs a `/stats` group breakdown (out of frontend scope).
- **Line/bar time-series** derive from `/stats/export` daily rows (the only time-series source); `/stats` summary drives KPIs.
- **Disputed-on-gate:** the gate routes disputes to the session-detail dispute panel (evidence side-by-side + manual fee) rather than resolving inline, matching the "never auto-price disputed" rule.
- **Evidence images** are click-to-load with an on-screen audit notice, honoring the privacy constraint.
