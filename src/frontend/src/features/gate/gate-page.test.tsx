import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { GatePage } from "./gate-page";

vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({ capture: null, events: [], degraded: false }),
}));

test("gate page shows no statistics KPI", () => {
  render(
    <MemoryRouter>
      <GatePage />
    </MemoryRouter>,
  );
  expect(screen.queryByText("Đang trong bãi")).toBeNull();
  expect(screen.queryByText("Doanh thu")).toBeNull();
});
