import { jwtDecode } from "jwt-decode";

type Claims = { sub?: string; role?: string; exp?: number };
export type Role = "root" | "manager" | "staff";
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
  return r === "root" || r === "manager" || r === "staff" ? r : null;
}

// Id tài khoản đang đăng nhập (claim `sub`), dùng để khóa thao tác tự vô hiệu hóa.
export function getUserId(): number | null {
  const sub = claims()?.sub;
  if (sub == null) return null;
  const n = Number(sub);
  return Number.isInteger(n) ? n : null;
}

export function isExpired(): boolean {
  const exp = claims()?.exp;
  if (!exp) return true;
  return Date.now() >= exp * 1000;
}
