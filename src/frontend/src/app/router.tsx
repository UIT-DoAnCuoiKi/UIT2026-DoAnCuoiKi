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
