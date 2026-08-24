import { saveToken, getToken, clearToken, getRole, isExpired } from "./auth";

// header.payload.signature — payload is base64url of {role, exp}
function makeJwt(payload: object): string {
  const b64 = (o: object) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${b64({ alg: "HS256" })}.${b64(payload)}.sig`;
}

beforeEach(() => localStorage.clear());

test("stores and reads token + role", () => {
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

test("clear removes token and role", () => {
  saveToken(makeJwt({ role: "staff", exp: Math.floor(Date.now() / 1000) + 100 }));
  clearToken();
  expect(getToken()).toBeNull();
  expect(getRole()).toBeNull();
});

test("unknown role returns null", () => {
  saveToken(makeJwt({ role: "root", exp: Math.floor(Date.now() / 1000) + 100 }));
  expect(getRole()).toBeNull();
});
