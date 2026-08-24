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
            <RequireRole roles={["admin"]}>
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
