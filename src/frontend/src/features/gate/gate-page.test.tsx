import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { GatePage } from "./gate-page";

vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({ capture: null, events: [], degraded: false }),
}));

vi.mock("@/api/generated/stats/stats", () => ({
  useGetStats: () => ({ data: { in_lot: 5, entries: 3, exits: 2, revenue: 1000 }, isLoading: false }),
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
