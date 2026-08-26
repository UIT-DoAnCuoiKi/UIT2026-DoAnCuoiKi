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

test("collapsed hides wordmark and nav labels", () => {
  saveToken(jwt("root"));
  render(<MemoryRouter><Sidebar collapsed={true} /></MemoryRouter>);
  expect(screen.queryByText("SmartPark")).toBeNull();
  expect(screen.queryByText("Cấu hình")).toBeNull();
});
