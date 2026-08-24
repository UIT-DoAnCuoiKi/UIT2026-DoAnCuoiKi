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
