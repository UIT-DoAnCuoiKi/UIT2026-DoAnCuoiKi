import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RequireRole } from "./role-guard";
import { saveToken, clearToken, getToken } from "@/lib/auth";

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

test("invalid role clears token and redirects to login", () => {
  clearToken();
  saveToken(jwt("admin")); // role cũ không hợp lệ
  render(tree("/config"));
  expect(screen.getByText("LOGIN")).toBeInTheDocument();
  expect(getToken()).toBeNull();
});
