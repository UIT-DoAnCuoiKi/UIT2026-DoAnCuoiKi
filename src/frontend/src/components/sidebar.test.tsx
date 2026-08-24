import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { saveToken } from "@/lib/auth";

function jwt(role: string) {
  const b64 = (o: object) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${b64({})}.${b64({ role, exp: Math.floor(Date.now() / 1000) + 3600 })}.s`;
}

test("staff does not see Cấu hình; admin does", () => {
  saveToken(jwt("staff"));
  const { rerender } = render(
    <MemoryRouter>
      <Sidebar collapsed={false} />
    </MemoryRouter>,
  );
  expect(screen.queryByText("Cấu hình")).toBeNull();
  expect(screen.getByText("Trạm cổng")).toBeInTheDocument();

  saveToken(jwt("admin"));
  rerender(
    <MemoryRouter>
      <Sidebar collapsed={false} />
    </MemoryRouter>,
  );
  expect(screen.getByText("Cấu hình")).toBeInTheDocument();
});
