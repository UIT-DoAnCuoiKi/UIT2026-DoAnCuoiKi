import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { getToken, getRole, isExpired, clearToken, type Role } from "@/lib/auth";

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const token = getToken();
  if (!token || isExpired()) return <Navigate to="/login" replace />;
  const role = getRole();
  if (!role) {
    clearToken();
    return <Navigate to="/login" replace />;
  }
  if (!roles.includes(role)) return <Navigate to="/gate" replace />;
  return <>{children}</>;
}
